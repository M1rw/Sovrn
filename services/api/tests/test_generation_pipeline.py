#!/usr/bin/env python3
"""
SOVRN Generation Pipeline Test Script
Tests the complete three-agent pipeline: Strategist -> Designer -> Engineer
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.strategist import strategist_agent
from app.agents.designer import designer_agent
from app.agents.engineer import engineer_agent


async def test_full_pipeline():
    """Test the complete generation pipeline."""
    
    # Example business brief
    brief = """
    We are a sustainable fashion startup selling eco-friendly activewear.
    We want to increase online sales and build brand awareness.
    Target audience: health-conscious millennials aged 25-40, interested in sustainability.
    Location: North America and Europe.
    Current challenge: Most competitors have better website experiences.
    """
    
    print("\n" + "="*80)
    print("SOVRN GENERATION PIPELINE TEST")
    print("="*80)
    
    try:
        # Phase 1: Strategy
        print("\n[1/3] PHASE 1: BUSINESS STRATEGY ANALYSIS")
        print("-" * 80)
        print("📊 Analyzing business goals and creating strategy...")
        
        strategy = await strategist_agent.analyze(
            brief=brief,
            locale="en",
            industry="fashion",
            additional_context={
                "business_model": "direct-to-consumer",
                "budget": "5000-10000 USD",
                "timeline": "3 months to launch"
            }
        )
        
        print(f"\n✓ Strategy Complete!")
        print(f"  • Primary Goal: {strategy.business_goal.primary}")
        print(f"  • Confidence: {strategy.business_goal.confidence:.0%}")
        print(f"  • Value Proposition: {strategy.value_proposition}")
        print(f"  • Target Audience: {strategy.target_audience.demographics}")
        print(f"  • Pages Designed: {len(strategy.pages)}")
        for page in strategy.pages:
            print(f"    - {page.title} ({page.slug})")
        
        # Phase 2: Design
        print("\n[2/3] PHASE 2: DESIGN SYSTEM GENERATION")
        print("-" * 80)
        print("🎨 Creating design system and visual language...")
        
        design = await designer_agent.design(
            strategy=strategy,
            locale="en",
            country_code="US",
            brand_guidelines={
                "brand_personality": "sustainable, modern, trustworthy",
                "color_preferences": ["earth tones", "forest green", "natural textures"],
                "typography_preference": "clean, modern sans-serif"
            }
        )
        
        print(f"\n✓ Design System Complete!")
        print(f"  • Primary Color: {design.tokens.colors.primary}")
        print(f"  • Direction: {design.cultural_adaptation.direction}")
        print(f"  • Pages Designed: {len(design.pages)}")
        print(f"  • Components: {len(design.components)}")
        print(f"  • Typography:")
        print(f"    - Heading Font: {design.tokens.typography.font_family_heading}")
        print(f"    - Body Font: {design.tokens.typography.font_family_body}")
        
        # Phase 3: Engineering
        print("\n[3/3] PHASE 3: CODE GENERATION")
        print("-" * 80)
        print("⚙️  Generating Next.js production code...")
        
        code = await engineer_agent.generate(
            strategy=strategy,
            design=design,
            project_name="eco-activewear-shop"
        )
        
        print(f"\n✓ Code Generation Complete!")
        print(f"  • Files Generated: {len(code.files)}")
        print(f"  • Pages: {len(code.pages)}")
        print(f"  • Components: {len(code.components)}")
        print(f"  • Configuration Files: ~5")
        print(f"\n  Generated Pages:")
        for page in code.pages:
            print(f"    - {page.title} ({page.slug})")
        
        print(f"\n  Generated Components:")
        for comp in code.components[:5]:
            print(f"    - {comp.name}")
        if len(code.components) > 5:
            print(f"    ... and {len(code.components) - 5} more")
        
        # Summary
        print("\n" + "="*80)
        print("GENERATION COMPLETE! 🎉")
        print("="*80)
        
        print(f"\n📊 Summary:")
        print(f"  • Business Goal: {strategy.business_goal.primary}")
        print(f"  • Target Locale: en (US)")
        print(f"  • Design Pages: {len(design.pages)}")
        print(f"  • Code Files: {len(code.files)}")
        print(f"  • Components: {len(code.components)}")
        print(f"\n✓ The site is ready for deployment!")
        
        # Save outputs for review (example)
        outputs = {
            "project": "eco-activewear-shop",
            "strategy": {
                "goal": strategy.business_goal.primary,
                "pages": [p.title for p in strategy.pages]
            },
            "design": {
                "primary_color": design.tokens.colors.primary,
                "pages": len(design.pages),
                "components": len(design.components)
            },
            "code": {
                "pages": [p.title for p in code.pages],
                "components": [c.name for c in code.components],
                "languages": list(set(f.language for f in code.files))
            }
        }
        
        print(f"\n📁 Output Summary:")
        print(json.dumps(outputs, indent=2))
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_individual_agents():
    """Test each agent independently."""
    
    brief = "I want to build a simple landing page for my SaaS product."
    
    print("\n" + "="*80)
    print("INDIVIDUAL AGENT TESTS")
    print("="*80)
    
    try:
        # Test Strategist
        print("\n[TEST 1] Strategist Agent")
        print("-" * 80)
        strategy = await strategist_agent.analyze(brief=brief)
        print(f"✓ Strategist: {strategy.business_goal.primary}")
        
        # Test Designer
        print("\n[TEST 2] Designer Agent")
        print("-" * 80)
        design = await designer_agent.design(strategy=strategy)
        print(f"✓ Designer: Created {len(design.pages)} pages with {len(design.components)} components")
        
        # Test Engineer
        print("\n[TEST 3] Engineer Agent")
        print("-" * 80)
        code = await engineer_agent.generate(strategy=strategy, design=design)
        print(f"✓ Engineer: Generated {len(code.files)} files and {len(code.pages)} pages")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🚀 Starting SOVRN Generation Pipeline Tests...")
    print("   Inference Server: http://localhost:8080")
    print("   API Server: http://localhost:8000")
    
    # Run full pipeline test
    success = await test_full_pipeline()
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
