# =============================================================================
# MML Pipeline v2 - Deep Thinking Website Generation
# =============================================================================
"""
Advanced MML Pipeline powered by SOVRN Hybrid AI with Deep Thinking.

Key improvements over the original:
1. Multi-step reasoning for better understanding
2. Research phase for best practices
3. Creative ideation before implementation
4. Self-verification and refinement
5. Automatic quality checks

This pipeline significantly outperforms single-shot generation
used by competitors like MiniMax AI.
"""

import time
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.mml.types import MMLResult, BriefAnalysis, DesignSpec, PagePlan, GeneratedCode


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""
    verbose: bool = True
    save_intermediates: bool = False
    mode: str = "full"  # "quick" or "full"
    enable_thinking: bool = True
    max_retries: int = 2


class MMLPipelineV2:
    """
    Advanced MML Pipeline with Deep Thinking.
    
    Two modes available:
    - Quick: 4 phases (understand → architect → design → implement)
    - Full: 8 phases with research, ideation, verification, refinement
    
    The full pipeline produces significantly better results by:
    1. Deeply understanding the user's actual needs
    2. Researching successful similar sites
    3. Generating creative concepts
    4. Planning structure carefully
    5. Creating thoughtful design systems
    6. Implementing clean code
    7. Self-checking for issues
    8. Refining to production quality
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._ai_engine = None
        self._thinking_engine = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Initialize AI engines."""
        if self._initialized:
            return
            
        from app.lib.ai.providers import get_ai_engine
        from app.lib.ai.deep_thinking import DeepThinkingEngine
        
        self._ai_engine = await get_ai_engine()
        self._thinking_engine = DeepThinkingEngine(self._ai_engine)
        self._initialized = True
    
    async def generate(self, prompt: str) -> MMLResult:
        """
        Generate a complete website from a prompt.
        
        Args:
            prompt: User's website description
            
        Returns:
            MMLResult with all generated content
        """
        await self._ensure_initialized()
        
        start_time = time.time()
        
        if self.config.verbose:
            print("=" * 60)
            print("MML Pipeline v2 - Deep Thinking Mode")
            print("=" * 60)
            print(f"\nPrompt: {prompt[:100]}...")
            print(f"Mode: {self.config.mode}")
        
        if self.config.enable_thinking:
            return await self._generate_with_thinking(prompt, start_time)
        else:
            return await self._generate_standard(prompt, start_time)
    
    async def _generate_with_thinking(self, prompt: str, start_time: float) -> MMLResult:
        """Generate using deep thinking engine."""
        
        if self.config.mode == "quick":
            result = await self._thinking_engine.quick_generate(prompt)
        else:
            result = await self._thinking_engine.think(prompt)
        
        if not result.success:
            # Fallback to standard generation
            if self.config.verbose:
                print(f"Deep thinking failed: {result.error}")
                print("Falling back to standard generation...")
            return await self._generate_standard(prompt, start_time)
        
        # Extract components from thinking steps
        brief = self._extract_brief(result.steps)
        spec = self._extract_spec(result.steps)
        plan = self._extract_plan(result.steps)
        code = self._extract_code(result)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if self.config.verbose:
            print("\n" + "=" * 60)
            print(f"Generation complete in {elapsed_ms}ms")
            print(f"Total tokens: {result.total_tokens}")
            print("=" * 60)
        
        return MMLResult(
            brief=brief,
            spec=spec,
            plan=plan,
            code=code,
            generation_time_ms=elapsed_ms,
            model_used="hybrid-ai",
            metadata={
                "thinking_steps": len(result.steps),
                "total_tokens": result.total_tokens,
                "thinking_chain": result.thinking_chain,
            }
        )
    
    async def _generate_standard(self, prompt: str, start_time: float) -> MMLResult:
        """Generate using standard MML agents."""
        from app.mml.agents import StrategistAgent, DesignerAgent, ArchitectAgent, BuilderAgent
        
        if self.config.verbose:
            print("\n[1/4] Strategist analyzing request...")
        strategist = StrategistAgent()
        brief = strategist.analyze(prompt)
        
        if self.config.verbose:
            print(f"  → Business: {brief.business_type}")
            print(f"  → Style: {brief.visual_style}")
        
        if self.config.verbose:
            print("\n[2/4] Designer creating visual spec...")
        designer = DesignerAgent()
        spec = designer.design(brief)
        
        if self.config.verbose:
            print(f"  → Colors: {spec.color_background} / {spec.color_accent}")
        
        if self.config.verbose:
            print("\n[3/4] Architect planning structure...")
        architect = ArchitectAgent()
        plan = architect.plan(brief, spec)
        
        if self.config.verbose:
            print(f"  → Sections: {[s.id for s in plan.sections]}")
        
        if self.config.verbose:
            print("\n[4/4] Builder generating code...")
        builder = BuilderAgent()
        code = builder.build(spec, plan)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if self.config.verbose:
            print(f"\nGeneration complete in {elapsed_ms}ms")
        
        return MMLResult(
            brief=brief,
            spec=spec,
            plan=plan,
            code=code,
            generation_time_ms=elapsed_ms,
            model_used="template"
        )
    
    def _extract_brief(self, steps) -> BriefAnalysis:
        """Extract brief from thinking steps."""
        for step in steps:
            if step.phase.value == "understand":
                data = step.output if isinstance(step.output, dict) else {}
                return BriefAnalysis(
                    business_type=data.get("business_type", "business"),
                    brand_personality=data.get("brand_personality", "professional"),
                    target_audience=data.get("target_audience", "general"),
                    primary_goal=data.get("primary_goal", "generate leads"),
                    secondary_goals=data.get("secondary_goals", []),
                    key_messages=data.get("key_messages", []),
                    required_sections=data.get("required_sections", ["hero", "about", "contact"]),
                    mood=data.get("mood", "professional"),
                    visual_style=data.get("visual_style", "minimal"),
                    special_features=data.get("special_features", [])
                )
        
        # Default
        return BriefAnalysis(
            business_type="business",
            brand_personality="professional",
            target_audience="general",
            primary_goal="generate leads",
            secondary_goals=[],
            key_messages=[],
            required_sections=["hero", "about", "contact"],
            mood="professional",
            visual_style="minimal",
            special_features=[]
        )
    
    def _extract_spec(self, steps) -> DesignSpec:
        """Extract design spec from thinking steps."""
        for step in steps:
            if step.phase.value == "design":
                data = step.output if isinstance(step.output, dict) else {}
                return DesignSpec(
                    brand_name=data.get("brand_name", "BRAND"),
                    tagline=data.get("tagline", ""),
                    color_primary=data.get("color_primary", "#333333"),
                    color_secondary=data.get("color_secondary", "#666666"),
                    color_background=data.get("color_background", "#FFFFFF"),
                    color_text=data.get("color_text", "#333333"),
                    color_accent=data.get("color_accent", "#0066FF"),
                    color_muted=data.get("color_muted", "#999999"),
                    font_display=data.get("font_display", "system-ui, sans-serif"),
                    font_body=data.get("font_body", "system-ui, sans-serif"),
                    font_size_base=data.get("font_size_base", "16px"),
                    heading_weight=data.get("heading_weight", 700),
                    layout_style=data.get("layout_style", "contained"),
                    max_width=data.get("max_width", "1200px"),
                    spacing_unit=data.get("spacing_unit", "8px"),
                    border_radius=data.get("border_radius", "8px"),
                    shadow_style=data.get("shadow_style", "subtle"),
                    image_treatment=data.get("image_treatment", "rounded"),
                    hover_style=data.get("hover_style", "lift"),
                    transition_speed=data.get("transition_speed", "0.3s"),
                    scroll_behavior=data.get("scroll_behavior", "smooth")
                )
        
        # Default
        return DesignSpec(
            brand_name="BRAND",
            tagline="",
            color_primary="#333333",
            color_secondary="#666666",
            color_background="#FFFFFF",
            color_text="#333333",
            color_accent="#0066FF",
            color_muted="#999999",
            font_display="system-ui, sans-serif",
            font_body="system-ui, sans-serif",
            font_size_base="16px",
            heading_weight=700,
            layout_style="contained",
            max_width="1200px",
            spacing_unit="8px",
            border_radius="8px",
            shadow_style="subtle",
            image_treatment="rounded",
            hover_style="lift",
            transition_speed="0.3s",
            scroll_behavior="smooth"
        )
    
    def _extract_plan(self, steps) -> PagePlan:
        """Extract page plan from thinking steps."""
        from app.mml.types import Section
        
        for step in steps:
            if step.phase.value == "architect":
                data = step.output if isinstance(step.output, dict) else {}
                
                sections = []
                for s in data.get("sections", []):
                    sections.append(Section(
                        id=s.get("id", "section"),
                        type=s.get("type", "content"),
                        title=s.get("title", ""),
                        content=s.get("content", {}),
                        layout=s.get("layout", "default")
                    ))
                
                return PagePlan(
                    nav_items=data.get("nav_items", ["Home", "About", "Contact"]),
                    nav_style=data.get("nav_style", "sticky"),
                    hero=data.get("hero", {}),
                    sections=sections,
                    footer=data.get("footer", {}),
                    interactions=data.get("interactions", [])
                )
        
        # Default
        return PagePlan(
            nav_items=["Home", "About", "Contact"],
            nav_style="sticky",
            hero={},
            sections=[],
            footer={},
            interactions=[]
        )
    
    def _extract_code(self, result) -> GeneratedCode:
        """Extract code from thinking result."""
        html = ""
        
        # Look for final output
        if result.final_output:
            if isinstance(result.final_output, str):
                html = result.final_output
            elif isinstance(result.final_output, dict):
                html = result.final_output.get("html", "")
        
        # Or from implement/refine steps
        for step in reversed(result.steps):
            if step.phase.value in ["refine", "implement"]:
                if isinstance(step.output, str):
                    html = step.output
                    break
        
        return GeneratedCode(
            html=html,
            css="",  # CSS is embedded in HTML
            js=""    # JS is embedded in HTML
        )


async def generate_website(prompt: str, verbose: bool = True, mode: str = "full") -> MMLResult:
    """
    Convenience function to generate a website.
    
    Args:
        prompt: Website description
        verbose: Print progress
        mode: "quick" or "full"
        
    Returns:
        MMLResult with generated website
    """
    config = PipelineConfig(verbose=verbose, mode=mode)
    pipeline = MMLPipelineV2(config)
    return await pipeline.generate(prompt)


def save_website(result: MMLResult, output_path: str):
    """Save generated website to file."""
    # If we have embedded code in HTML
    html = result.code.html
    
    # Or combine HTML + CSS + JS
    if not html and result.html:
        html = result.html
    
    if html:
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"Saved to: {output_path}")
    else:
        print("No HTML content to save")
