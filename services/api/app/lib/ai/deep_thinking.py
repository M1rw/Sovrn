# =============================================================================
# Deep Thinking Engine - Advanced Reasoning for Website Generation
# =============================================================================
"""
Deep thinking orchestration for superior website building.
Implements multi-step reasoning chains to outperform MiniMax AI.

Key Advantages:
- Structured reasoning process
- Multi-agent thinking collaboration
- Self-verification loops
- Context-aware generation
- Iterative refinement
"""

import asyncio
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
import time

logger = structlog.get_logger()


class ThinkingPhase(str, Enum):
    """Phases of the thinking process."""
    UNDERSTAND = "understand"      # Parse and understand the request
    RESEARCH = "research"          # Gather context and examples
    IDEATE = "ideate"              # Generate creative ideas
    ARCHITECT = "architect"        # Plan the structure
    DESIGN = "design"              # Visual and UX decisions
    IMPLEMENT = "implement"        # Generate code
    VERIFY = "verify"              # Self-check and validate
    REFINE = "refine"              # Improve and polish


@dataclass
class ThinkingStep:
    """A single step in the thinking chain."""
    phase: ThinkingPhase
    input: str
    reasoning: str
    output: Any
    confidence: float = 0.0  # 0-1 confidence score
    duration_ms: int = 0
    tokens_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "input": self.input[:200] + "..." if len(self.input) > 200 else self.input,
            "reasoning": self.reasoning,
            "output": self.output if isinstance(self.output, (str, dict, list)) else str(self.output),
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
        }


@dataclass
class ThinkingResult:
    """Result of the complete thinking process."""
    steps: List[ThinkingStep] = field(default_factory=list)
    final_output: Any = None
    total_duration_ms: int = 0
    total_tokens: int = 0
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "final_output": self.final_output,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "success": self.success,
            "error": self.error,
        }
    
    @property
    def thinking_chain(self) -> str:
        """Get human-readable thinking chain."""
        parts = []
        for i, step in enumerate(self.steps, 1):
            parts.append(f"## Step {i}: {step.phase.value.upper()}")
            parts.append(f"**Reasoning:** {step.reasoning}")
            parts.append("")
        return "\n".join(parts)


class DeepThinkingEngine:
    """
    Deep Thinking Engine for website generation.
    
    Implements a multi-phase reasoning process:
    1. UNDERSTAND - Parse user intent and requirements
    2. RESEARCH - Analyze similar sites and best practices
    3. IDEATE - Generate creative concepts
    4. ARCHITECT - Plan page structure and flow
    5. DESIGN - Define visual language
    6. IMPLEMENT - Generate actual code
    7. VERIFY - Self-check for quality
    8. REFINE - Polish and improve
    
    This structured approach produces better results than
    single-shot generation used by competitors.
    """
    
    # Phase-specific system prompts
    PHASE_PROMPTS = {
        ThinkingPhase.UNDERSTAND: """You are an expert requirements analyst.
Your task is to deeply understand what the user wants.

Extract:
1. Business type and industry
2. Target audience and their needs
3. Primary goals (sales, leads, awareness)
4. Brand personality and tone
5. Specific features mentioned
6. Implicit requirements not stated
7. Success criteria

Think like a senior consultant doing discovery.
Output valid JSON with your analysis.""",

        ThinkingPhase.RESEARCH: """You are a web design researcher with access to 10,000+ website examples.
Analyze what makes successful sites in this category.

Consider:
1. Industry best practices
2. Competitor patterns
3. Conversion optimization tactics
4. Trust-building elements
5. Mobile-first considerations
6. Accessibility requirements
7. SEO fundamentals

Output actionable insights as JSON.""",

        ThinkingPhase.IDEATE: """You are a creative director at a top design agency.
Generate innovative concepts for this website.

Explore:
1. Unique visual directions
2. Memorable interactions
3. Brand differentiation
4. Emotional connections
5. Surprise and delight moments
6. Content strategy angles
7. Value propositions

Be creative but practical. Output 3 distinct concepts as JSON.""",

        ThinkingPhase.ARCHITECT: """You are a senior UX architect.
Plan the optimal page structure and user flow.

Define:
1. Page sections and hierarchy
2. Content blocks and their purpose
3. User journey through the page
4. Call-to-action placement
5. Information architecture
6. Mobile layout adaptations
7. Performance considerations

Output a detailed page plan as JSON.""",

        ThinkingPhase.DESIGN: """You are a visual design systems expert.
Create a complete design specification.

Specify:
1. Color palette with exact hex codes
2. Typography system (fonts, sizes, weights)
3. Spacing and grid system
4. Component styles (buttons, cards, etc.)
5. Animation and transition details
6. Image treatment guidelines
7. Dark/light mode considerations

Output precise design tokens as JSON.""",

        ThinkingPhase.IMPLEMENT: """You are an expert frontend developer.
Generate production-ready HTML, CSS, and JavaScript.

Requirements:
1. Semantic HTML5 structure
2. Modern CSS with custom properties
3. Responsive design (mobile-first)
4. Smooth animations
5. Accessible (WCAG 2.1 AA)
6. Performance optimized
7. Cross-browser compatible

Output a complete, working webpage.""",

        ThinkingPhase.VERIFY: """You are a senior QA engineer and code reviewer.
Check the generated code for issues.

Verify:
1. HTML validity and semantics
2. CSS best practices
3. Responsive breakpoints work
4. Accessibility compliance
5. Performance bottlenecks
6. Browser compatibility
7. Content accuracy

List issues found and severity (critical/major/minor).
Output verification report as JSON.""",

        ThinkingPhase.REFINE: """You are a perfectionist web developer.
Polish and improve the code based on feedback.

Focus on:
1. Fix all critical issues
2. Improve code quality
3. Enhance animations
4. Optimize performance
5. Add finishing touches
6. Ensure pixel-perfection
7. Final polish

Output the refined, production-ready code.""",
    }
    
    def __init__(self, ai_engine):
        """
        Initialize with AI engine.
        
        Args:
            ai_engine: HybridAIEngine instance
        """
        self.ai = ai_engine
        self._thinking_cache: Dict[str, ThinkingResult] = {}
        
    async def think(
        self,
        prompt: str,
        phases: Optional[List[ThinkingPhase]] = None,
        context: Optional[Dict[str, Any]] = None,
        verbose: bool = True,
    ) -> ThinkingResult:
        """
        Execute deep thinking process for website generation.
        
        Args:
            prompt: User's website request
            phases: Custom phase sequence (default: full pipeline)
            context: Additional context to include
            verbose: Log progress
            
        Returns:
            ThinkingResult with all steps and final output
        """
        start_time = time.time()
        
        # Default phases for website generation
        if phases is None:
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
        
        result = ThinkingResult()
        accumulated_context = {
            "original_prompt": prompt,
            **(context or {})
        }
        
        if verbose:
            logger.info("deep_thinking_started", phases=[p.value for p in phases])
        
        try:
            for phase in phases:
                step = await self._execute_phase(
                    phase=phase,
                    prompt=prompt,
                    context=accumulated_context,
                    verbose=verbose,
                )
                
                result.steps.append(step)
                result.total_tokens += step.tokens_used
                
                # Add output to context for next phase
                accumulated_context[phase.value] = step.output
                
                # Check for low confidence
                if step.confidence < 0.5:
                    logger.warning(
                        "low_confidence_step",
                        phase=phase.value,
                        confidence=step.confidence
                    )
            
            # Final output is from the last phase
            if result.steps:
                result.final_output = result.steps[-1].output
            
            result.total_duration_ms = int((time.time() - start_time) * 1000)
            result.success = True
            
            if verbose:
                logger.info(
                    "deep_thinking_complete",
                    duration_ms=result.total_duration_ms,
                    total_tokens=result.total_tokens,
                    steps=len(result.steps)
                )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.total_duration_ms = int((time.time() - start_time) * 1000)
            logger.error("deep_thinking_failed", error=str(e))
        
        return result
    
    async def _execute_phase(
        self,
        phase: ThinkingPhase,
        prompt: str,
        context: Dict[str, Any],
        verbose: bool,
    ) -> ThinkingStep:
        """Execute a single thinking phase."""
        start_time = time.time()
        
        if verbose:
            logger.info("executing_phase", phase=phase.value)
        
        # Build context string
        context_str = self._build_context_string(phase, context)
        
        # Build phase prompt
        phase_prompt = self._build_phase_prompt(phase, prompt, context)
        
        # Determine if this phase needs JSON output
        json_mode = phase not in [ThinkingPhase.IMPLEMENT, ThinkingPhase.REFINE]
        
        # Use thinking mode for complex phases
        from .providers import AIMode
        mode = AIMode.THINKING if phase in [
            ThinkingPhase.UNDERSTAND,
            ThinkingPhase.IDEATE,
            ThinkingPhase.ARCHITECT
        ] else AIMode.QUALITY
        
        # Generate
        response = await self.ai.generate(
            prompt=phase_prompt,
            system_prompt=self.PHASE_PROMPTS[phase],
            context=context_str,
            mode=mode,
            json_mode=json_mode,
            max_tokens=8192 if phase in [ThinkingPhase.IMPLEMENT, ThinkingPhase.REFINE] else 4096,
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Parse output
        output = self._parse_output(response.content, json_mode)
        
        # Extract reasoning
        reasoning = response.thinking or self._extract_reasoning(response.content)
        
        # Calculate confidence
        confidence = self._calculate_confidence(response, output, phase)
        
        return ThinkingStep(
            phase=phase,
            input=phase_prompt[:500],
            reasoning=reasoning[:1000] if reasoning else "Direct generation",
            output=output,
            confidence=confidence,
            duration_ms=duration_ms,
            tokens_used=response.tokens_used,
        )
    
    def _build_context_string(self, phase: ThinkingPhase, context: Dict[str, Any]) -> str:
        """Build context string for the phase."""
        parts = []
        
        # Include relevant previous outputs
        relevant_phases = {
            ThinkingPhase.UNDERSTAND: [],
            ThinkingPhase.RESEARCH: ["understand"],
            ThinkingPhase.IDEATE: ["understand", "research"],
            ThinkingPhase.ARCHITECT: ["understand", "ideate"],
            ThinkingPhase.DESIGN: ["understand", "ideate", "architect"],
            ThinkingPhase.IMPLEMENT: ["architect", "design"],
            ThinkingPhase.VERIFY: ["implement"],
            ThinkingPhase.REFINE: ["implement", "verify"],
        }
        
        for prev_phase in relevant_phases.get(phase, []):
            if prev_phase in context:
                parts.append(f"### {prev_phase.upper()} OUTPUT:")
                output = context[prev_phase]
                if isinstance(output, dict):
                    parts.append(json.dumps(output, indent=2))
                else:
                    parts.append(str(output)[:2000])
                parts.append("")
        
        return "\n".join(parts) if parts else None
    
    def _build_phase_prompt(
        self,
        phase: ThinkingPhase,
        original_prompt: str,
        context: Dict[str, Any]
    ) -> str:
        """Build the prompt for a specific phase."""
        
        if phase == ThinkingPhase.UNDERSTAND:
            return f"""Analyze this website request deeply:

"{original_prompt}"

Extract all explicit and implicit requirements.
Think about what the user REALLY needs, not just what they said."""

        elif phase == ThinkingPhase.RESEARCH:
            return f"""Based on the understanding of this request:
{json.dumps(context.get('understand', {}), indent=2)}

Research best practices and patterns for this type of website.
What makes similar sites successful? What should we learn from them?"""

        elif phase == ThinkingPhase.IDEATE:
            return f"""Given this understanding and research:

Understanding: {json.dumps(context.get('understand', {}), indent=2)}
Research: {json.dumps(context.get('research', {}), indent=2)}

Generate 3 creative concepts for this website.
Each concept should have a unique angle and memorable elements."""

        elif phase == ThinkingPhase.ARCHITECT:
            best_concept = context.get('ideate', {})
            if isinstance(best_concept, list):
                best_concept = best_concept[0] if best_concept else {}
            
            return f"""Create a detailed page architecture for this website.

Selected Concept: {json.dumps(best_concept, indent=2)}
Business Understanding: {json.dumps(context.get('understand', {}), indent=2)}

Plan every section, its purpose, and content structure."""

        elif phase == ThinkingPhase.DESIGN:
            return f"""Create a complete design system for this website.

Architecture: {json.dumps(context.get('architect', {}), indent=2)}
Understanding: {json.dumps(context.get('understand', {}), indent=2)}

Define exact colors, typography, spacing, and component styles."""

        elif phase == ThinkingPhase.IMPLEMENT:
            return f"""Generate a complete, production-ready single-page website.

Design System: {json.dumps(context.get('design', {}), indent=2)}
Architecture: {json.dumps(context.get('architect', {}), indent=2)}

Create HTML, CSS, and JavaScript in a single file.
The code should be immediately deployable."""

        elif phase == ThinkingPhase.VERIFY:
            return f"""Review this generated website code for issues:

```html
{context.get('implement', '')}
```

Check for:
1. HTML validity
2. CSS issues
3. Accessibility problems
4. Mobile responsiveness
5. Performance concerns
6. Browser compatibility

List all issues found with severity levels."""

        elif phase == ThinkingPhase.REFINE:
            return f"""Improve this website based on the verification feedback:

ORIGINAL CODE:
```html
{context.get('implement', '')}
```

ISSUES FOUND:
{json.dumps(context.get('verify', {}), indent=2)}

Fix all issues and polish the code to production quality."""

        return original_prompt
    
    def _parse_output(self, content: str, json_mode: bool) -> Any:
        """Parse the output from AI response."""
        if not json_mode:
            return content
        
        try:
            # Try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object
        brace_match = re.search(r'\{[\s\S]*\}', content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Return as string if can't parse
        return content
    
    def _extract_reasoning(self, content: str) -> Optional[str]:
        """Extract reasoning from response."""
        # Look for thinking patterns
        patterns = [
            r"(?:Thinking|Reasoning|Analysis):\s*(.*?)(?=\n\n|\{|\[)",
            r"<thinking>(.*?)</thinking>",
            r"## Reasoning\n(.*?)(?=\n##|\n\{)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _calculate_confidence(
        self,
        response: Any,
        output: Any,
        phase: ThinkingPhase
    ) -> float:
        """Calculate confidence score for the step."""
        confidence = 0.5  # Base confidence
        
        # Check if response succeeded
        if not response.success:
            return 0.1
        
        # Check output quality
        if isinstance(output, dict):
            # More keys = more complete
            confidence += min(len(output) * 0.05, 0.3)
        elif isinstance(output, str):
            # Longer = more detailed (to a point)
            if len(output) > 100:
                confidence += 0.1
            if len(output) > 500:
                confidence += 0.1
        
        # Check for code phases
        if phase in [ThinkingPhase.IMPLEMENT, ThinkingPhase.REFINE]:
            if isinstance(output, str):
                if "<html" in output.lower() or "<!doctype" in output.lower():
                    confidence += 0.2
                if "<style" in output.lower() or "css" in output.lower():
                    confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def quick_generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ThinkingResult:
        """
        Quick generation with abbreviated thinking.
        Skips research and verification for speed.
        
        Args:
            prompt: User's website request
            context: Additional context
            
        Returns:
            ThinkingResult with generated website
        """
        return await self.think(
            prompt=prompt,
            phases=[
                ThinkingPhase.UNDERSTAND,
                ThinkingPhase.ARCHITECT,
                ThinkingPhase.DESIGN,
                ThinkingPhase.IMPLEMENT,
            ],
            context=context,
            verbose=True,
        )
