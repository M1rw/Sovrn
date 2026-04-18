# =============================================================================
# SOVRN API - AI Endpoints
# =============================================================================
"""
AI-powered generation endpoints using hybrid AI architecture.
"""

import asyncio
import hashlib
import json
import time
from threading import Lock
from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError
import structlog

from app.core.config import settings
from app.core.database import async_session
from app.lib.ai.providers import HybridAIEngine, AIProvider, AIResponse, get_ai_engine, AIMode
from app.lib.ai.deep_thinking import DeepThinkingEngine, ThinkingPhase
from app.lib.ai.prompt_registry import PromptRegistryLoader, PromptRegistryValidationError
from app.lib.ai.conversation_summary import (
    SummaryTriggerDecision,
    parse_conversation_summary_output,
    should_trigger_conversation_summary,
)
from app.lib.ai.structured_output import StructuredModelOutput, parse_structured_model_output
from app.schemas import PatchContractRequest
from app.services.conversation_repository import (
    ConversationRepository,
    ConversationRepositoryError,
    ConversationThreadNotFoundError,
    ConversationVersionConflictError,
)

logger = structlog.get_logger()

router = APIRouter()

CHAT_TIMEOUT_SECONDS = 12
_prompt_registry_loader = PromptRegistryLoader()
_shadow_metrics_lock = Lock()
_shadow_metrics = {
    "samples": 0,
    "parse_success": 0,
    "parse_failure": 0,
    "repair_used": 0,
    "action_total": 0,
    "action_match": 0,
    "action_mismatch": 0,
}


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatMessage(BaseModel):
    """Chat message."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: List[ChatMessage]
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    thread_id: Optional[UUID] = None
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=128)
    model: Optional[str] = None
    provider: Optional[str] = Field(default="auto", description="auto, puter, phi3")
    mode: Optional[str] = Field(default="balanced", description="fast, balanced, quality, thinking")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=512, ge=1, le=4096)
    stream: bool = False
    json_mode: bool = False


class ChatResponse(BaseModel):
    """Chat completion response."""
    content: str
    provider: str
    model: str
    thinking: Optional[str] = None
    latency_ms: int
    tokens_used: int
    success: bool


class GenerateWebsiteRequest(BaseModel):
    """Website generation request."""
    prompt: str = Field(..., min_length=10, max_length=2000)
    mode: Optional[str] = Field(default="full", description="quick or full")
    provider: Optional[str] = Field(default="auto")
    return_thinking: bool = Field(default=False)


class GenerateWebsiteResponse(BaseModel):
    """Website generation response."""
    html: str
    thinking_chain: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    total_duration_ms: int
    total_tokens: int
    success: bool
    error: Optional[str] = None


class AIStatusResponse(BaseModel):
    """AI engine status."""
    initialized: bool
    providers: Dict[str, Any]
    stats: Dict[str, int]


def _latest_user_message(request: ChatRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content.strip()
    return ""


def _build_chat_fallback(request: ChatRequest, reason: Optional[str] = None) -> ChatResponse:
    user_message = _latest_user_message(request)
    lowered = user_message.lower()

    if any(keyword in lowered for keyword in ("website", "landing", "portfolio", "shop", "dashboard", "app")):
        content = (
            "I’m loading a fallback response right now, but I can still help you move forward. "
            "Tell me the site type, tone, colors, and the sections you want, and I’ll turn it into a clean build prompt."
        )
    else:
        content = (
            "I’m temporarily using a local fallback while the model warms up. "
            "Send me a short brief and I’ll help structure it into something the builder can use."
        )

    if reason:
        logger.warning("ai_chat_fallback", reason=reason)

    return ChatResponse(
        content=content,
        provider="fallback",
        model="sovrn-fallback",
        thinking=None,
        latency_ms=0,
        tokens_used=0,
        success=True,
    )


def _build_chat_prompt(
    request: ChatRequest,
    messages: Optional[List[ChatMessage]] = None,
) -> tuple[Optional[str], str]:
    """Build canonical chat prompt with optional server-side prompt assembly."""
    message_list = messages if messages is not None else request.messages
    prompt_parts: List[str] = []

    if settings.AI_PROMPT_ASSEMBLY_ON:
        system_prompt: Optional[str] = None
        try:
            system_prompt = _prompt_registry_loader.assemble()
        except PromptRegistryValidationError as e:
            logger.error("ai_prompt_registry_validation_error", error=str(e))
        except Exception as e:
            logger.error("ai_prompt_registry_assembly_error", error=str(e))

        # Under feature flag, client-supplied system prompts are ignored.
        for msg in message_list:
            if msg.role == "user":
                prompt_parts.append(msg.content)
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        return system_prompt, "\n\n".join(prompt_parts)

    system_prompt = None
    for msg in message_list:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            prompt_parts.append(msg.content)
        elif msg.role == "assistant":
            prompt_parts.append(f"Assistant: {msg.content}")

    return system_prompt, "\n\n".join(prompt_parts)


def _message_signature(message: ChatMessage) -> tuple[str, str]:
    return (message.role, message.content.strip())


def _merge_retrieved_and_request_messages(
    retrieved_messages: List[ChatMessage],
    request_messages: List[ChatMessage],
) -> List[ChatMessage]:
    """Merge retrieved context and request messages with deterministic overlap handling."""
    if not retrieved_messages:
        return list(request_messages)

    if not request_messages:
        return list(retrieved_messages)

    retrieved_signatures = [_message_signature(m) for m in retrieved_messages]
    request_signatures = [_message_signature(m) for m in request_messages]

    max_overlap = min(len(retrieved_signatures), len(request_signatures))
    overlap = 0
    for size in range(max_overlap, 0, -1):
        if retrieved_signatures[-size:] == request_signatures[:size]:
            overlap = size
            break

    return [*retrieved_messages, *request_messages[overlap:]]


def _recent_turns_to_messages(recent_turns: List[Any]) -> List[ChatMessage]:
    """Convert persisted recent turns to canonical prompt messages."""
    messages: List[ChatMessage] = []

    for turn in recent_turns:
        user_message = (getattr(turn, "user_message", "") or "").strip()
        if user_message:
            messages.append(ChatMessage(role="user", content=user_message))

        assistant_message = ""
        server_response = getattr(turn, "server_response", None)
        if isinstance(server_response, dict):
            content = server_response.get("content")
            if isinstance(content, str):
                assistant_message = content.strip()

        if assistant_message:
            messages.append(ChatMessage(role="assistant", content=assistant_message))

    return messages


def _build_summary_context_message(summary_output: Any) -> ChatMessage:
    """Create a deterministic non-authoritative summary message for compacted context."""
    lines = [
        (
            "Conversation summary (non-authoritative) "
            f"for turns {summary_output.from_turn_index}-{summary_output.to_turn_index}: "
            f"{summary_output.summary.strip()}"
        )
    ]

    key_points = [
        point.strip()
        for point in summary_output.key_points
        if isinstance(point, str) and point.strip()
    ]
    if key_points:
        lines.append("Key points:")
        lines.extend(f"- {point}" for point in key_points[:5])

    return ChatMessage(role="assistant", content="\n".join(lines))


async def _resolve_compacted_messages(request: ChatRequest) -> List[ChatMessage]:
    """Resolve compacted context from summary plus recent turns with deterministic fallback."""
    if not settings.AI_CONTEXT_COMPACTION_ENABLED:
        return list(request.messages)

    if request.thread_id is None:
        return list(request.messages)

    try:
        async with async_session() as db:
            repository = ConversationRepository(db)
            thread = await repository.get_thread(request.thread_id)
            if thread is None:
                logger.info(
                    "ai_context_compaction_fallback",
                    reason="thread_not_found",
                    thread_id=str(request.thread_id),
                )
                return list(request.messages)

            recent_turns = await repository.list_recent_turns(
                thread_id=thread.id,
                limit=settings.AI_CONTEXT_COMPACTION_RECENT_TURNS,
            )
            recent_messages = _recent_turns_to_messages(recent_turns)

            latest_summary = await repository.get_latest_summary(thread.id)
            if latest_summary is None:
                merged_messages = _merge_retrieved_and_request_messages(recent_messages, request.messages)
                logger.info(
                    "ai_context_compaction_fallback",
                    reason="summary_missing",
                    thread_id=str(thread.id),
                    recent_turn_count=len(recent_turns),
                    merged_message_count=len(merged_messages),
                )
                return merged_messages

            parsed_summary = parse_conversation_summary_output(latest_summary.summary_json)
            if not parsed_summary.success or parsed_summary.parsed is None:
                merged_messages = _merge_retrieved_and_request_messages(recent_messages, request.messages)
                logger.warning(
                    "ai_context_compaction_fallback",
                    reason="summary_invalid",
                    thread_id=str(thread.id),
                    recent_turn_count=len(recent_turns),
                    merged_message_count=len(merged_messages),
                )
                return merged_messages

            summary_message = _build_summary_context_message(parsed_summary.parsed)
            merged_messages = _merge_retrieved_and_request_messages(
                [summary_message, *recent_messages],
                request.messages,
            )

            logger.info(
                "ai_context_compaction_applied",
                thread_id=str(thread.id),
                summary_from_turn=parsed_summary.parsed.from_turn_index,
                summary_to_turn=parsed_summary.parsed.to_turn_index,
                recent_turn_count=len(recent_turns),
                merged_message_count=len(merged_messages),
            )
            return merged_messages
    except Exception as exc:
        logger.warning(
            "ai_context_compaction_exception",
            error_type=type(exc).__name__,
        )
        return list(request.messages)


def _resolve_shadow_action(request: ChatRequest, proposal: StructuredModelOutput) -> tuple[str, str]:
    """Resolve action authoritatively in shadow mode from request and proposal."""
    proposed_action = proposal.action
    lowered_user = _latest_user_message(request).lower()

    def _has_valid_revision_patch_contract(payload: dict[str, Any]) -> bool:
        patch_contract = payload.get("patch_contract")
        if not isinstance(patch_contract, dict):
            return False

        try:
            PatchContractRequest.model_validate(patch_contract)
        except ValidationError:
            return False

        return True

    if proposed_action == "ready_to_generate":
        has_site_intent = any(keyword in lowered_user for keyword in ("website", "landing", "portfolio", "shop", "app"))
        generation_payload = proposal.generation_request if isinstance(proposal.generation_request, dict) else {}
        has_brief = isinstance(generation_payload.get("brief"), str) and bool(generation_payload.get("brief", "").strip())
        if has_site_intent and has_brief:
            return "ready_to_generate", "generation_gate_passed"
        return "ask_clarification", "generation_gate_failed"

    if proposed_action == "propose_revision":
        has_revision_intent = any(keyword in lowered_user for keyword in ("revise", "revision", "change", "update", "edit"))
        revision_payload = proposal.revision_request if isinstance(proposal.revision_request, dict) else {}
        has_revision_scope = bool(revision_payload.get("change_summary") or revision_payload.get("targets"))
        has_patch_contract = _has_valid_revision_patch_contract(revision_payload)
        if has_revision_intent and has_revision_scope and has_patch_contract:
            return "propose_revision", "revision_gate_passed"
        return "ask_clarification", "revision_gate_failed"

    if proposed_action in {"respond", "ask_clarification", "error_recoverable"}:
        return proposed_action, "accepted"

    return "respond", "defaulted"


def _resolve_backend_action_metadata(
    request: ChatRequest,
    model_content: str,
    *,
    reason_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve authoritative action metadata for Phase 5 response rollout."""
    resolved_action = "respond"
    resolved_reason = reason_hint or "defaulted"
    proposed_action: Optional[str] = None

    text = (model_content or "").strip()
    if not text:
        resolved_reason = reason_hint or "empty_model_content"
    else:
        try:
            parsed_result = parse_structured_model_output(text, max_repair_attempts=1)
            if parsed_result.success and parsed_result.parsed is not None:
                proposed_action = parsed_result.parsed.action
                resolved_action, resolved_reason = _resolve_shadow_action(request, parsed_result.parsed)
            else:
                resolved_reason = reason_hint or "structured_parse_failed"
        except Exception:
            resolved_reason = reason_hint or "structured_parse_exception"

    metadata: Dict[str, Any] = {
        "resolved_action": resolved_action,
        "resolved_action_reason": resolved_reason,
        "generation_handoff_allowed": resolved_action == "ready_to_generate",
        # Phase 5-1 exposes authoritative metadata only; handoff path remains unchanged.
        "generation_handoff_initiated": False,
    }
    if proposed_action is not None:
        metadata["proposed_action"] = proposed_action

    return metadata


def _attach_phase5_response_metadata(
    request: ChatRequest,
    base_response: ChatResponse,
    *,
    model_content: str,
    reason_hint: Optional[str] = None,
    conversation_metadata: Optional[Dict[str, Any]] = None,
):
    """Attach optional response metadata behind feature flags."""
    include_resolved_action = settings.AI_RESOLVED_ACTION_RESPONSE_ENABLED
    include_conversation_metadata = bool(conversation_metadata)

    if not include_resolved_action and not include_conversation_metadata:
        return base_response

    payload = base_response.model_dump(mode="json")
    if include_resolved_action:
        payload.update(
            _resolve_backend_action_metadata(
                request,
                model_content,
                reason_hint=reason_hint,
            )
        )
    if include_conversation_metadata:
        payload.update(conversation_metadata or {})

    return JSONResponse(content=payload)


def _record_structured_shadow_metrics(
    parse_success: bool,
    repair_used: bool,
    proposed_action: Optional[str] = None,
    resolved_action: Optional[str] = None,
) -> None:
    """Record shadow parsing/action metrics and emit quality-gate telemetry."""
    if not settings.AI_STRUCTURED_SHADOW_METRICS_ENABLED:
        return

    with _shadow_metrics_lock:
        _shadow_metrics["samples"] += 1
        if parse_success:
            _shadow_metrics["parse_success"] += 1
        else:
            _shadow_metrics["parse_failure"] += 1

        if repair_used:
            _shadow_metrics["repair_used"] += 1

        action_outcome = "not_applicable"
        if proposed_action and resolved_action:
            _shadow_metrics["action_total"] += 1
            if proposed_action == resolved_action:
                _shadow_metrics["action_match"] += 1
                action_outcome = "match"
            else:
                _shadow_metrics["action_mismatch"] += 1
                action_outcome = "mismatch"

        samples = _shadow_metrics["samples"]
        parse_success_rate = _shadow_metrics["parse_success"] / samples
        parse_failure_rate = _shadow_metrics["parse_failure"] / samples
        repair_rate = _shadow_metrics["repair_used"] / samples

        action_total = _shadow_metrics["action_total"]
        action_mismatch_rate = (
            _shadow_metrics["action_mismatch"] / action_total if action_total > 0 else 0.0
        )

        gate_ready = samples >= settings.AI_SHADOW_METRICS_MIN_SAMPLE_SIZE
        gate_parse_success = parse_success_rate >= settings.AI_SHADOW_MIN_PARSE_SUCCESS_RATE
        gate_repair = repair_rate <= settings.AI_SHADOW_MAX_REPAIR_RATE
        gate_parse_failure = parse_failure_rate <= settings.AI_SHADOW_MAX_PARSE_FAILURE_RATE
        gate_action_mismatch = action_mismatch_rate <= settings.AI_SHADOW_MAX_ACTION_MISMATCH_RATE
        gate_pass = gate_ready and all(
            [gate_parse_success, gate_repair, gate_parse_failure, gate_action_mismatch]
        )

        logger.info(
            "ai_structured_shadow_telemetry",
            parse_success=parse_success,
            repair_used=repair_used,
            action_outcome=action_outcome,
            samples=samples,
            parse_success_rate=round(parse_success_rate, 6),
            parse_failure_rate=round(parse_failure_rate, 6),
            repair_rate=round(repair_rate, 6),
            action_mismatch_rate=round(action_mismatch_rate, 6),
            gate_ready=gate_ready,
            gate_pass=gate_pass,
            gate_parse_success=gate_parse_success,
            gate_repair=gate_repair,
            gate_parse_failure=gate_parse_failure,
            gate_action_mismatch=gate_action_mismatch,
        )


def _run_structured_shadow_parse(request: ChatRequest, content: str) -> None:
    """Run shadow-mode structured parse/repair with optional shadow action resolution."""
    if not settings.AI_STRUCTURED_SHADOW_ENABLED:
        return

    if not content.strip():
        return

    try:
        result = parse_structured_model_output(content, max_repair_attempts=1)
        if result.success and result.parsed is not None:
            if settings.AI_ACTION_RESOLUTION_SHADOW_ENABLED:
                proposed_action = result.parsed.action
                resolved_action, reason = _resolve_shadow_action(request, result.parsed)
                if proposed_action != resolved_action:
                    logger.warning(
                        "ai_structured_shadow_action_mismatch",
                        proposed_action=proposed_action,
                        resolved_action=resolved_action,
                        reason=reason,
                        repaired=result.repaired,
                        repair_attempts=result.repair_attempts,
                        generation_handoff_initiated=False,
                    )
                else:
                    logger.info(
                        "ai_structured_shadow_action_resolved",
                        proposed_action=proposed_action,
                        resolved_action=resolved_action,
                        reason=reason,
                        repaired=result.repaired,
                        repair_attempts=result.repair_attempts,
                        generation_handoff_initiated=False,
                    )

                _record_structured_shadow_metrics(
                    parse_success=True,
                    repair_used=result.repaired,
                    proposed_action=proposed_action,
                    resolved_action=resolved_action,
                )
            else:
                logger.info(
                    "ai_structured_shadow_parse_ok",
                    repaired=result.repaired,
                    repair_attempts=result.repair_attempts,
                    action=result.parsed.action,
                )
                _record_structured_shadow_metrics(
                    parse_success=True,
                    repair_used=result.repaired,
                )
        else:
            logger.warning(
                "ai_structured_shadow_parse_failed",
                repaired=result.repaired,
                repair_attempts=result.repair_attempts,
                error_type="structured_parse_failed",
            )
            _record_structured_shadow_metrics(
                parse_success=False,
                repair_used=result.repaired,
            )
    except Exception as e:
        # Shadow parsing must never alter existing chat behavior.
        logger.error(
            "ai_structured_shadow_parse_exception",
            error_type=type(e).__name__,
        )
        _record_structured_shadow_metrics(
            parse_success=False,
            repair_used=False,
        )


def _derive_idempotency_key(request: ChatRequest) -> str:
    """Derive a deterministic fallback idempotency key from request payload."""
    payload = {
        "thread_id": str(request.thread_id) if request.thread_id else None,
        "provider": request.provider,
        "mode": request.mode,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "messages": [{"role": message.role, "content": message.content} for message in request.messages],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:64]


def _build_non_authoritative_summary_payload(
    decision: SummaryTriggerDecision,
    user_message: str,
    assistant_message: str,
) -> dict[str, Any]:
    """Build minimal non-authoritative summary payload for contract validation."""
    from_turn = int(decision.from_turn_index or 0)
    to_turn = int(decision.to_turn_index or 0)
    clean_user = (user_message or "").strip().replace("\n", " ")
    clean_assistant = (assistant_message or "").strip().replace("\n", " ")

    key_points: List[str] = []
    if clean_user:
        key_points.append(f"User: {clean_user[:280]}")
    if clean_assistant:
        key_points.append(f"Assistant: {clean_assistant[:280]}")

    return {
        "version": "1.0",
        "non_authoritative": True,
        "from_turn_index": from_turn,
        "to_turn_index": to_turn,
        "summary": (
            f"Non-authoritative summary for turns {from_turn}-{to_turn}. "
            "Content is stored for later compaction steps and does not alter authoritative state."
        ),
        "key_points": key_points,
        "open_questions": [],
        "meta": {
            "source": "deterministic_trigger_stub",
        },
    }


async def _maybe_persist_non_authoritative_summary(
    repository: ConversationRepository,
    thread_id: UUID,
    turn_index: int,
    user_message: str,
    assistant_message: str,
) -> None:
    """Persist non-authoritative summary only when deterministic trigger fires."""
    if not settings.AI_SUMMARIZATION_ENABLED:
        return

    latest_summary = await repository.get_latest_summary(thread_id)
    latest_to_turn = int(latest_summary.to_turn_index) if latest_summary is not None else None

    decision = should_trigger_conversation_summary(
        current_turn_index=turn_index,
        latest_summary_to_turn_index=latest_to_turn,
        trigger_every_turns=settings.AI_SUMMARY_TRIGGER_EVERY_TURNS,
    )
    if not decision.should_trigger:
        logger.info(
            "ai_summary_trigger_skipped",
            thread_id=str(thread_id),
            turn_index=turn_index,
            reason=decision.reason,
        )
        return

    candidate = _build_non_authoritative_summary_payload(
        decision=decision,
        user_message=user_message,
        assistant_message=assistant_message,
    )
    parsed = parse_conversation_summary_output(candidate)
    if not parsed.success or parsed.parsed is None:
        logger.warning(
            "ai_summary_contract_rejected",
            thread_id=str(thread_id),
            turn_index=turn_index,
            error=parsed.error,
        )
        return

    summary_output = parsed.parsed
    await repository.write_summary(
        thread_id=thread_id,
        from_turn_index=summary_output.from_turn_index,
        to_turn_index=summary_output.to_turn_index,
        summary_json=summary_output.model_dump(mode="json"),
        summarizer_version="deterministic-trigger.v1",
    )

    logger.info(
        "ai_summary_persisted",
        thread_id=str(thread_id),
        from_turn_index=summary_output.from_turn_index,
        to_turn_index=summary_output.to_turn_index,
        non_authoritative=summary_output.non_authoritative,
    )


async def _persist_conversation_shadow_state(
    request: ChatRequest,
    response: AIResponse,
) -> Optional[Dict[str, Any]]:
    """Persist canonical conversation thread/turn/snapshot state behind feature flag."""
    if not settings.AI_STATE_PERSIST_ENABLED:
        return None

    if request.user_id is None:
        logger.info("ai_conversation_persist_skipped", reason="missing_user_id")
        return None

    idempotency_key = request.idempotency_key or _derive_idempotency_key(request)
    user_message = _latest_user_message(request)

    try:
        async with async_session() as db:
            repository = ConversationRepository(db)

            thread = None
            if request.thread_id is not None:
                thread = await repository.get_thread(request.thread_id)
                if thread is None:
                    raise ConversationThreadNotFoundError(f"Conversation thread not found: {request.thread_id}")
            else:
                thread = await repository.create_thread(
                    user_id=request.user_id,
                    project_id=request.project_id,
                )

            existing_turn = await repository.get_turn_by_idempotency_key(
                thread_id=thread.id,
                idempotency_key=idempotency_key,
            )
            if existing_turn is not None:
                await db.rollback()
                logger.info(
                    "ai_conversation_persist_idempotent_hit",
                    thread_id=str(thread.id),
                    turn_id=str(existing_turn.id),
                )
                return {
                    "thread_id": str(thread.id),
                    "turn_index": int(existing_turn.turn_index),
                    "state_version": int(thread.state_version),
                    "idempotency_key": idempotency_key,
                }

            turn_index = int(thread.last_turn_index) + 1
            turn = await repository.append_turn(
                thread_id=thread.id,
                turn_index=turn_index,
                user_message=user_message,
                idempotency_key=idempotency_key,
                server_response={
                    "content": response.content,
                    "provider": response.provider.value,
                    "model": response.model,
                    "success": response.success,
                },
                model_raw_output={"content": response.content},
                parse_status="shadow_attempted" if settings.AI_STRUCTURED_SHADOW_ENABLED else "not_attempted",
                provider=response.provider.value,
                model=response.model,
                latency_ms=response.latency_ms,
                tokens_used=response.tokens_used,
            )

            authoritative_state = dict(thread.authoritative_state or {})
            authoritative_state["last_user_message"] = user_message
            authoritative_state["last_model"] = response.model
            authoritative_state["last_provider"] = response.provider.value
            authoritative_state["last_response_success"] = bool(response.success)

            snapshot = await repository.write_state_snapshot(
                thread_id=thread.id,
                expected_version=int(thread.state_version),
                authoritative_state=authoritative_state,
                locked_constraints=list(thread.locked_constraints or []),
                turn_id=turn.id,
                last_turn_index=turn_index,
            )

            await _maybe_persist_non_authoritative_summary(
                repository=repository,
                thread_id=thread.id,
                turn_index=turn_index,
                user_message=user_message,
                assistant_message=response.content or "",
            )

            await db.commit()
            logger.info(
                "ai_conversation_persisted",
                thread_id=str(thread.id),
                turn_id=str(turn.id),
                state_version=int(snapshot.state_version),
            )
            return {
                "thread_id": str(thread.id),
                "turn_index": turn_index,
                "state_version": int(snapshot.state_version),
                "idempotency_key": idempotency_key,
            }
    except ConversationVersionConflictError as e:
        logger.warning(
            "ai_conversation_persist_version_conflict",
            thread_id=str(e.thread_id),
            expected_version=e.expected_version,
            current_version=e.current_version,
        )
        return None
    except ConversationRepositoryError as e:
        logger.warning("ai_conversation_persist_repository_error", error_type=type(e).__name__)
        return None
    except Exception as e:
        # Persistence must fail open and never break chat completion behavior.
        logger.error("ai_conversation_persist_exception", error_type=type(e).__name__)
        return None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Get AI engine status and available providers."""
    try:
        engine = await get_ai_engine()
        status = engine.get_status()
        return AIStatusResponse(**status)
    except Exception as e:
        logger.error("ai_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Chat completion with hybrid AI.
    
    Uses Puter.js (cloud) as primary with Phi-3 (local) as fallback.
    """
    try:
        start_time = time.monotonic()

        engine = await asyncio.wait_for(get_ai_engine(), timeout=CHAT_TIMEOUT_SECONDS)
        
        # Parse provider
        provider = {
            "auto": AIProvider.AUTO,
            "puter": AIProvider.PUTER,
            "phi3": AIProvider.PHI3_LOCAL,
        }.get(request.provider, AIProvider.AUTO)
        
        # Parse mode
        mode = {
            "fast": AIMode.FAST,
            "balanced": AIMode.BALANCED,
            "quality": AIMode.QUALITY,
            "thinking": AIMode.THINKING,
        }.get(request.mode, AIMode.BALANCED)
        
        # Build prompt from compacted context when enabled.
        effective_messages = await _resolve_compacted_messages(request)
        system_prompt, prompt = _build_chat_prompt(request, messages=effective_messages)
        
        # Generate
        response = await asyncio.wait_for(
            engine.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                mode=mode,
                provider=provider,
                json_mode=request.json_mode,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            ),
            timeout=CHAT_TIMEOUT_SECONDS,
        )

        _run_structured_shadow_parse(request, response.content or "")
        conversation_metadata = await _persist_conversation_shadow_state(request, response)

        latency_ms = int((time.monotonic() - start_time) * 1000)

        if not response.success or not response.content.strip():
            fallback = _build_chat_fallback(request, response.error or "empty_ai_response")
            fallback.latency_ms = latency_ms
            return _attach_phase5_response_metadata(
                request,
                fallback,
                model_content=response.content or "",
                reason_hint=response.error or "empty_ai_response",
                conversation_metadata=conversation_metadata,
            )
        
        chat_response = ChatResponse(
            content=response.content,
            provider=response.provider.value,
            model=response.model,
            thinking=response.thinking,
            latency_ms=latency_ms or response.latency_ms,
            tokens_used=response.tokens_used,
            success=response.success,
        )
        return _attach_phase5_response_metadata(
            request,
            chat_response,
            model_content=response.content or "",
            conversation_metadata=conversation_metadata,
        )

    except asyncio.TimeoutError:
        fallback = _build_chat_fallback(request, "timeout")
        return _attach_phase5_response_metadata(
            request,
            fallback,
            model_content="",
            reason_hint="timeout",
        )
        
    except Exception as e:
        logger.error("chat_completion_error", error=str(e))
        fallback = _build_chat_fallback(request, str(e))
        return _attach_phase5_response_metadata(
            request,
            fallback,
            model_content="",
            reason_hint="chat_completion_exception",
        )


@router.post("/chat/stream")
async def chat_completion_stream(request: ChatRequest):
    """
    Streaming chat completion.
    
    Returns Server-Sent Events with response chunks.
    """
    async def generate():
        try:
            engine = await get_ai_engine()
            
            # Build prompt
            system_prompt = None
            prompt = ""
            
            for msg in request.messages:
                if msg.role == "system":
                    system_prompt = msg.content
                elif msg.role == "user":
                    prompt = msg.content
            
            # Parse provider
            provider = {
                "auto": AIProvider.AUTO,
                "puter": AIProvider.PUTER,
                "phi3": AIProvider.PHI3_LOCAL,
            }.get(request.provider, AIProvider.AUTO)
            
            async for chunk in engine.stream_generate(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=provider,
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/generate/website", response_model=GenerateWebsiteResponse)
async def generate_website(request: GenerateWebsiteRequest):
    """
    Generate a complete website using deep thinking.
    
    This is the core website builder endpoint that uses multi-step
    reasoning to create high-quality websites.
    """
    try:
        engine = await get_ai_engine()
        thinking_engine = DeepThinkingEngine(engine)
        
        # Choose generation mode
        if request.mode == "quick":
            result = await thinking_engine.quick_generate(request.prompt)
        else:
            result = await thinking_engine.think(request.prompt)
        
        # Extract HTML from final output
        html = ""
        if result.success and result.final_output:
            if isinstance(result.final_output, str):
                html = result.final_output
            elif isinstance(result.final_output, dict):
                html = result.final_output.get("html", str(result.final_output))
        
        return GenerateWebsiteResponse(
            html=html,
            thinking_chain=result.thinking_chain if request.return_thinking else None,
            steps=[s.to_dict() for s in result.steps] if request.return_thinking else None,
            total_duration_ms=result.total_duration_ms,
            total_tokens=result.total_tokens,
            success=result.success,
            error=result.error,
        )
        
    except Exception as e:
        logger.error("generate_website_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/website/stream")
async def generate_website_stream(request: GenerateWebsiteRequest):
    """
    Stream website generation with thinking steps.
    
    Returns Server-Sent Events with progress updates.
    """
    async def generate():
        try:
            engine = await get_ai_engine()
            thinking_engine = DeepThinkingEngine(engine)
            
            # Define phases based on mode
            if request.mode == "quick":
                phases = [
                    ThinkingPhase.UNDERSTAND,
                    ThinkingPhase.ARCHITECT,
                    ThinkingPhase.DESIGN,
                    ThinkingPhase.IMPLEMENT,
                ]
            else:
                phases = [
                    ThinkingPhase.UNDERSTAND,
                    ThinkingPhase.RESEARCH,
                    ThinkingPhase.IDEATE,
                    ThinkingPhase.ARCHITECT,
                    ThinkingPhase.DESIGN,
                    ThinkingPhase.IMPLEMENT,
                    ThinkingPhase.VERIFY,
                    ThinkingPhase.REFINE,
                ]
            
            # Send phase list
            yield f"data: {json.dumps({'type': 'phases', 'phases': [p.value for p in phases]})}\n\n"
            
            # Execute phases and stream progress
            context = {"original_prompt": request.prompt}
            
            for phase in phases:
                # Send phase start
                yield f"data: {json.dumps({'type': 'phase_start', 'phase': phase.value})}\n\n"
                
                # Execute phase
                step = await thinking_engine._execute_phase(
                    phase=phase,
                    prompt=request.prompt,
                    context=context,
                    verbose=False,
                )
                
                # Add to context
                context[phase.value] = step.output
                
                # Send phase complete
                yield f"data: {json.dumps({'type': 'phase_complete', 'phase': phase.value, 'duration_ms': step.duration_ms, 'confidence': step.confidence})}\n\n"
                
                # Send reasoning if available
                if step.reasoning:
                    yield f"data: {json.dumps({'type': 'reasoning', 'phase': phase.value, 'content': step.reasoning[:500]})}\n\n"
            
            # Send final HTML
            final_html = context.get("refine", context.get("implement", ""))
            yield f"data: {json.dumps({'type': 'complete', 'html': final_html})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/models")
async def list_models():
    """List available AI models."""
    return {
        "cloud_models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "puter", "speed": "fast"},
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "puter", "speed": "medium"},
            {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "puter", "speed": "medium"},
            {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "provider": "puter", "speed": "fast"},
            {"id": "llama-3.1-405b", "name": "Llama 3.1 405B", "provider": "puter", "speed": "slow"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "provider": "puter", "speed": "medium", "thinking": True},
        ],
        "local_models": [
            {"id": "phi-3-mini", "name": "Phi-3 Mini (4K)", "provider": "phi3", "speed": "medium", "offline": True},
        ]
    }
