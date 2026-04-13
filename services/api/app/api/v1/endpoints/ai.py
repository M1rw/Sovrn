# =============================================================================
# SOVRN API - AI Endpoints
# =============================================================================
"""
AI-powered generation endpoints using hybrid AI architecture.
"""

import asyncio
import json
import time
from threading import Lock
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings
from app.lib.ai.providers import HybridAIEngine, AIProvider, AIResponse, get_ai_engine, AIMode
from app.lib.ai.deep_thinking import DeepThinkingEngine, ThinkingPhase
from app.lib.ai.prompt_registry import PromptRegistryLoader, PromptRegistryValidationError
from app.lib.ai.structured_output import StructuredModelOutput, parse_structured_model_output

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


def _build_chat_prompt(request: ChatRequest) -> tuple[Optional[str], str]:
    """Build canonical chat prompt with optional server-side prompt assembly."""
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
        for msg in request.messages:
            if msg.role == "user":
                prompt_parts.append(msg.content)
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        return system_prompt, "\n\n".join(prompt_parts)

    system_prompt = None
    for msg in request.messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            prompt_parts.append(msg.content)
        elif msg.role == "assistant":
            prompt_parts.append(f"Assistant: {msg.content}")

    return system_prompt, "\n\n".join(prompt_parts)


def _resolve_shadow_action(request: ChatRequest, proposal: StructuredModelOutput) -> tuple[str, str]:
    """Resolve action authoritatively in shadow mode from request and proposal."""
    proposed_action = proposal.action
    lowered_user = _latest_user_message(request).lower()

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
        if has_revision_intent and has_revision_scope:
            return "propose_revision", "revision_gate_passed"
        return "ask_clarification", "revision_gate_failed"

    if proposed_action in {"respond", "ask_clarification", "error_recoverable"}:
        return proposed_action, "accepted"

    return "respond", "defaulted"


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
        
        # Build prompt from messages.
        system_prompt, prompt = _build_chat_prompt(request)
        
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

        latency_ms = int((time.monotonic() - start_time) * 1000)

        if not response.success or not response.content.strip():
            fallback = _build_chat_fallback(request, response.error or "empty_ai_response")
            fallback.latency_ms = latency_ms
            return fallback
        
        return ChatResponse(
            content=response.content,
            provider=response.provider.value,
            model=response.model,
            thinking=response.thinking,
            latency_ms=latency_ms or response.latency_ms,
            tokens_used=response.tokens_used,
            success=response.success,
        )

    except asyncio.TimeoutError:
        return _build_chat_fallback(request, "timeout")
        
    except Exception as e:
        logger.error("chat_completion_error", error=str(e))
        return _build_chat_fallback(request, str(e))


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
