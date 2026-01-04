#!/usr/bin/env python3
"""
Test SOVRN AI Agents
Tests Strategist, Designer, and Engineer agents
"""

import asyncio
import sys
import json

# Add app to path
sys.path.insert(0, '/app')

from app.agents.strategist import strategist_agent
from app.agents.designer import designer_agent  
from app.agents.engineer import engineer_agent


async def test_strategist():
    """Test Strategist Agent"""
    print("\n" + "="*60)
    print("🎯 TESTING STRATEGIST AGENT")
    print("="*60)
    
    brief = """
    Build a website for a small coffee roastery.
    They want to sell coffee beans online and tell their story.
    Target customers are coffee enthusiasts who care about quality.
    """
    
    print(f"\n📝 Business Brief:\n{brief.strip()}")
    print("\n⏳ Generating strategy...")
    
    try:
        strategy = await strategist_agent.create_strategy(brief)
        
        print("\n✅ Strategy Generated!")
        print(f"🎯 Primary Goal: {strategy.business_goal.primary}")
        print(f"💎 Value Prop: {strategy.value_proposition[:100]}...")
        print(f"📄 Pages: {len(strategy.pages)} pages")
        print(f"   - {', '.join([p.slug for p in strategy.pages[:5]])}")
        
        return strategy
        
    except Exception as e:
        print(f"\n❌ Strategist Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_designer(strategy):
    """Test Designer Agent"""
    print("\n" + "="*60)
    print("🎨 TESTING DESIGNER AGENT")
    print("="*60)
    
    if not strategy:
        print("⚠️  Skipping - no strategy available")
        return None
    
    # Use first page for testing
    page_spec = strategy.pages[0]
    print(f"\n📄 Designing: {page_spec.title}")
    print(f"   Slug: {page_spec.slug}")
    print(f"   Purpose: {page_spec.purpose[:80]}...")
    
    print("\n⏳ Generating design...")
    
    try:
        design = await designer_agent.design_page(
            page_spec=page_spec,
            brand_voice=strategy.brand_voice,
            value_prop=strategy.value_proposition
        )
        
        print("\n✅ Design Generated!")
        print(f"🎨 Layout: {design.layout}")
        print(f"🎨 Style: {design.style_theme}")
        print(f"📦 Sections: {len(design.sections)}")
        for i, section in enumerate(design.sections[:3], 1):
            print(f"   {i}. {section.type} - {section.purpose[:50]}...")
        
        return design
        
    except Exception as e:
        print(f"\n❌ Designer Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_engineer(design, page_spec):
    """Test Engineer Agent"""
    print("\n" + "="*60)
    print("⚙️  TESTING ENGINEER AGENT")
    print("="*60)
    
    if not design or not page_spec:
        print("⚠️  Skipping - no design available")
        return None
    
    print(f"\n📄 Generating code for: {page_spec.title}")
    print("\n⏳ Writing production code...")
    
    try:
        code = await engineer_agent.generate_page(
            page_spec=page_spec,
            design=design,
            components_library="react"
        )
        
        print("\n✅ Code Generated!")
        print(f"📦 Files: {len(code.files)}")
        for file in code.files[:3]:
            print(f"   - {file.path} ({len(file.content)} chars)")
        
        print(f"\n📚 Dependencies: {len(code.dependencies)}")
        print(f"   {', '.join(list(code.dependencies.keys())[:5])}...")
        
        print(f"\n🧪 Tests: {'Yes' if code.tests else 'No'}")
        
        # Show a snippet of the main file
        if code.files:
            main_file = code.files[0]
            print(f"\n📄 Preview of {main_file.path}:")
            print("   " + "-"*56)
            lines = main_file.content.split('\n')[:10]
            for line in lines:
                print(f"   {line[:76]}")
            if len(main_file.content.split('\n')) > 10:
                print(f"   ... ({len(main_file.content.split('\n'))} total lines)")
        
        return code
        
    except Exception as e:
        print(f"\n❌ Engineer Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all agent tests"""
    print("\n" + "="*60)
    print("🚀 SOVRN AI AGENTS TEST SUITE")
    print("="*60)
    
    # Test 1: Strategist
    strategy = await test_strategist()
    if not strategy:
        print("\n❌ Cannot continue without strategy")
        return False
    
    # Test 2: Designer
    design = await test_designer(strategy)
    if not design:
        print("\n⚠️  Cannot test Engineer without design")
        return False
    
    # Test 3: Engineer
    code = await test_engineer(design, strategy.pages[0])
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Strategist: {'PASS' if strategy else 'FAIL'}")
    print(f"✅ Designer:   {'PASS' if design else 'FAIL'}")
    print(f"✅ Engineer:   {'PASS' if code else 'FAIL'}")
    print("="*60)
    
    success = all([strategy, design, code])
    if success:
        print("\n🎉 All agents working correctly!")
    else:
        print("\n⚠️  Some agents failed - check logs above")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
