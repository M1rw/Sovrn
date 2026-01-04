"""
MML Pipeline

Orchestrates the website generation process.
"""

import time
from typing import Optional
from dataclasses import dataclass
from app.mml.types import MMLResult, BriefAnalysis, DesignSpec, PagePlan, GeneratedCode
from app.mml.agents import StrategistAgent, DesignerAgent, ArchitectAgent, BuilderAgent
from app.mml.llm import get_backend


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""
    verbose: bool = True
    save_intermediates: bool = False


class MMLPipeline:
    """
    Main pipeline for website generation.
    
    Flow:
    1. Strategist: Understand the request
    2. Designer: Create visual spec
    3. Architect: Plan page structure
    4. Builder: Generate code
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.strategist = StrategistAgent()
        self.designer = DesignerAgent()
        self.architect = ArchitectAgent()
        self.builder = BuilderAgent()
    
    def generate(self, prompt: str) -> MMLResult:
        """
        Generate a complete website from a prompt.
        
        Args:
            prompt: User's website description
            
        Returns:
            MMLResult with all generated content
        """
        start_time = time.time()
        
        if self.config.verbose:
            print("=" * 60)
            print("MML Pipeline Starting")
            print("=" * 60)
            print(f"\nPrompt: {prompt[:100]}...")
        
        # Step 1: Strategist analyzes the request
        if self.config.verbose:
            print("\n[1/4] Strategist analyzing request...")
        brief = self.strategist.analyze(prompt)
        if self.config.verbose:
            print(f"  → Business: {brief.business_type}")
            print(f"  → Style: {brief.visual_style}")
            print(f"  → Mood: {brief.mood}")
        
        # Step 2: Designer creates visual spec
        if self.config.verbose:
            print("\n[2/4] Designer creating visual spec...")
        spec = self.designer.design(brief)
        if self.config.verbose:
            print(f"  → Brand: {spec.brand_name}")
            print(f"  → Colors: {spec.color_background} / {spec.color_accent}")
            print(f"  → Font: {spec.font_display}")
        
        # Step 3: Architect plans the page
        if self.config.verbose:
            print("\n[3/4] Architect planning page structure...")
        plan = self.architect.plan(brief, spec)
        if self.config.verbose:
            print(f"  → Sections: {[s.id for s in plan.sections]}")
            print(f"  → Hero: {plan.hero.get('headline', 'N/A')[:50]}")
        
        # Step 4: Builder generates code
        if self.config.verbose:
            print("\n[4/4] Builder generating code...")
        code = self.builder.build(spec, plan)
        if self.config.verbose:
            print(f"  → HTML: {len(code.html)} chars")
            print(f"  → CSS: {len(code.css)} chars")
            print(f"  → JS: {len(code.js)} chars")
        
        # Calculate time
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if self.config.verbose:
            print("\n" + "=" * 60)
            print(f"Generation complete in {elapsed_ms}ms")
            print("=" * 60)
        
        return MMLResult(
            brief=brief,
            spec=spec,
            plan=plan,
            code=code,
            generation_time_ms=elapsed_ms,
            model_used="qwen-coder"
        )


def generate_website(prompt: str, verbose: bool = True) -> MMLResult:
    """
    Convenience function to generate a website.
    
    Args:
        prompt: Website description
        verbose: Print progress
        
    Returns:
        MMLResult with generated website
    """
    config = PipelineConfig(verbose=verbose)
    pipeline = MMLPipeline(config)
    return pipeline.generate(prompt)


def save_website(result: MMLResult, output_path: str):
    """Save generated website to file."""
    with open(output_path, 'w') as f:
        f.write(result.html)
    print(f"Saved to: {output_path}")
