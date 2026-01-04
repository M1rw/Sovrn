"""
MML Agents

Specialized AI agents for website generation.
Each agent uses AI when available, with smart template fallbacks.
"""

import json
import re
from typing import Dict, Any, Optional, List
from app.mml.llm import get_backend, GenerationConfig
from app.mml.types import (
    BriefAnalysis, DesignSpec, PagePlan, Section, GeneratedCode
)


# ============================================================================
# SMART TEMPLATES - Used when no API is available
# These are intelligent, not just keyword matching
# ============================================================================

BUSINESS_TEMPLATES = {
    "coffee": {
        "type": "artisan coffee roastery",
        "personality": "warm, craft-focused, authentic, sensory",
        "audience": "coffee enthusiasts, quality-conscious consumers, local community",
        "goal": "drive coffee sales and subscriptions",
        "messages": ["Single-origin beans", "Small-batch roasted", "Direct trade relationships", "Crafted with passion"],
        "sections": ["hero", "story", "beans", "process", "visit", "contact"],
        "mood": "warm",
        "style": "craft",
        "features": ["origin stories", "flavor profiles", "brewing guides"]
    },
    "architect": {
        "type": "architecture firm",
        "personality": "bold, precise, visionary, structural",
        "audience": "developers, investors, design-conscious clients",
        "goal": "attract high-value architecture projects",
        "messages": ["Form follows function", "Contextual design", "Award-winning work", "Sustainable approach"],
        "sections": ["hero", "philosophy", "projects", "awards", "team", "contact"],
        "mood": "professional",
        "style": "swiss",
        "features": ["project gallery", "case studies", "publications"]
    },
    "restaurant": {
        "type": "restaurant",
        "personality": "inviting, delicious, warm, memorable",
        "audience": "food lovers, local diners, special occasion seekers",
        "goal": "drive reservations and visits",
        "messages": ["Fresh ingredients", "Unforgettable flavors", "Warm atmosphere"],
        "sections": ["hero", "menu", "story", "gallery", "reservations", "contact"],
        "mood": "warm",
        "style": "craft",
        "features": ["menu display", "reservation system", "gallery"]
    },
    "agency": {
        "type": "creative agency",
        "personality": "bold, innovative, results-driven",
        "audience": "brands seeking creative partners",
        "goal": "attract new client projects",
        "messages": ["We make brands matter", "Strategy meets creativity", "Results that speak"],
        "sections": ["hero", "services", "work", "about", "contact"],
        "mood": "bold",
        "style": "swiss",
        "features": ["case studies", "client logos", "team profiles"]
    },
    "startup": {
        "type": "tech startup",
        "personality": "innovative, fast, disruptive",
        "audience": "early adopters, investors, tech-savvy users",
        "goal": "drive signups and investment",
        "messages": ["The future is now", "Reimagine possible", "Join the revolution"],
        "sections": ["hero", "features", "how-it-works", "pricing", "testimonials", "contact"],
        "mood": "energetic",
        "style": "minimal",
        "features": ["feature showcase", "pricing table", "demo video"]
    },
    "wellness": {
        "type": "wellness center",
        "personality": "calm, nurturing, balanced, healing",
        "audience": "health-conscious individuals seeking balance",
        "goal": "book classes and treatments",
        "messages": ["Find your balance", "Nurture body and mind", "Your wellness journey"],
        "sections": ["hero", "philosophy", "services", "classes", "team", "contact"],
        "mood": "calm",
        "style": "organic",
        "features": ["class schedule", "booking system", "testimonials"]
    },
    "default": {
        "type": "business",
        "personality": "professional, trustworthy, capable",
        "audience": "potential customers and partners",
        "goal": "generate leads and build trust",
        "messages": ["Excellence in everything", "Your trusted partner", "Quality you can count on"],
        "sections": ["hero", "about", "services", "testimonials", "contact"],
        "mood": "professional",
        "style": "minimal",
        "features": []
    }
}

STYLE_SPECS = {
    "craft": {
        "color_primary": "#3D2B1F",
        "color_secondary": "#2D5A3D",
        "color_background": "#F5EDE4",
        "color_text": "#3D2B1F",
        "color_accent": "#2D5A3D",
        "color_muted": "#8B7355",
        "font_display": "Georgia, serif",
        "font_body": "system-ui, sans-serif",
        "font_size_base": "18px",
        "heading_weight": 600,
        "layout_style": "contained",
        "max_width": "1200px",
        "spacing_unit": "8px",
        "border_radius": "12px",
        "shadow_style": "subtle",
        "image_treatment": "rounded",
        "hover_style": "lift",
        "transition_speed": "0.3s",
        "scroll_behavior": "smooth"
    },
    "swiss": {
        "color_primary": "#000000",
        "color_secondary": "#FF3300",
        "color_background": "#FFFFFF",
        "color_text": "#111111",
        "color_accent": "#FF3300",
        "color_muted": "#888888",
        "font_display": "Inter, system-ui, sans-serif",
        "font_body": "Inter, system-ui, sans-serif",
        "font_size_base": "16px",
        "heading_weight": 900,
        "layout_style": "full-width",
        "max_width": "2400px",
        "spacing_unit": "8px",
        "border_radius": "0px",
        "shadow_style": "none",
        "image_treatment": "sharp",
        "hover_style": "color",
        "transition_speed": "0.2s",
        "scroll_behavior": "instant"
    },
    "minimal": {
        "color_primary": "#333333",
        "color_secondary": "#666666",
        "color_background": "#FAFAFA",
        "color_text": "#333333",
        "color_accent": "#000000",
        "color_muted": "#999999",
        "font_display": "Inter, system-ui, sans-serif",
        "font_body": "Inter, system-ui, sans-serif",
        "font_size_base": "16px",
        "heading_weight": 500,
        "layout_style": "contained",
        "max_width": "1200px",
        "spacing_unit": "8px",
        "border_radius": "4px",
        "shadow_style": "subtle",
        "image_treatment": "minimal",
        "hover_style": "underline",
        "transition_speed": "0.3s",
        "scroll_behavior": "smooth"
    },
    "dark": {
        "color_primary": "#FFFFFF",
        "color_secondary": "#FF0055",
        "color_background": "#0A0A0A",
        "color_text": "#FFFFFF",
        "color_accent": "#FF0055",
        "color_muted": "#666666",
        "font_display": "Inter, system-ui, sans-serif",
        "font_body": "Inter, system-ui, sans-serif",
        "font_size_base": "16px",
        "heading_weight": 800,
        "layout_style": "full-width",
        "max_width": "1800px",
        "spacing_unit": "8px",
        "border_radius": "0px",
        "shadow_style": "glow",
        "image_treatment": "contrast",
        "hover_style": "glow",
        "transition_speed": "0.15s",
        "scroll_behavior": "smooth"
    },
    "organic": {
        "color_primary": "#2C3E2D",
        "color_secondary": "#5B8A5B",
        "color_background": "#FDFBF7",
        "color_text": "#2C3E2D",
        "color_accent": "#5B8A5B",
        "color_muted": "#7A8B7A",
        "font_display": "Georgia, serif",
        "font_body": "system-ui, sans-serif",
        "font_size_base": "18px",
        "heading_weight": 500,
        "layout_style": "contained",
        "max_width": "1100px",
        "spacing_unit": "8px",
        "border_radius": "16px",
        "shadow_style": "soft",
        "image_treatment": "organic",
        "hover_style": "fade",
        "transition_speed": "0.4s",
        "scroll_behavior": "smooth"
    }
}

def detect_business_type(prompt: str) -> str:
    """Detect business type from prompt."""
    prompt_lower = prompt.lower()
    
    if any(w in prompt_lower for w in ["coffee", "roaster", "roastery", "cafe", "espresso"]):
        return "coffee"
    if any(w in prompt_lower for w in ["architect", "architecture", "building design"]):
        return "architect"
    if any(w in prompt_lower for w in ["restaurant", "dining", "bistro", "eatery", "food"]):
        return "restaurant"
    if any(w in prompt_lower for w in ["agency", "creative", "marketing", "branding"]):
        return "agency"
    if any(w in prompt_lower for w in ["startup", "saas", "app", "platform", "tech"]):
        return "startup"
    if any(w in prompt_lower for w in ["wellness", "spa", "yoga", "meditation", "health"]):
        return "wellness"
    
    return "default"


# ============================================================================
# AGENTS
# ============================================================================

class StrategistAgent:
    """Understands user intent and creates a strategic brief."""
    
    SYSTEM_PROMPT = """You are a senior brand strategist. Analyze the request and create a strategic brief.
Output valid JSON only."""

    def analyze(self, prompt: str) -> BriefAnalysis:
        """Analyze user prompt and create strategic brief."""
        
        backend = get_backend()
        
        # Try AI generation first
        if backend.is_ai_enabled:
            user_prompt = f"""Analyze this website request:
"{prompt}"

Return JSON:
{{
    "business_type": "specific type",
    "brand_personality": "personality traits",
    "target_audience": "who the site is for",
    "primary_goal": "main conversion goal",
    "secondary_goals": ["other goals"],
    "key_messages": ["core messages"],
    "required_sections": ["sections needed"],
    "mood": "single word mood",
    "visual_style": "craft/swiss/minimal/dark/organic",
    "special_features": ["special features mentioned"]
}}"""

            response = backend.generate(
                prompt=user_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                config=GenerationConfig(temperature=0.6, max_tokens=1024),
                json_mode=True
            )
            
            if response:
                try:
                    data = json.loads(response)
                    return self._create_brief(data)
                except json.JSONDecodeError:
                    pass
        
        # Smart template fallback
        return self._template_analyze(prompt)
    
    def _template_analyze(self, prompt: str) -> BriefAnalysis:
        """Analyze using smart templates."""
        biz_type = detect_business_type(prompt)
        template = BUSINESS_TEMPLATES[biz_type]
        
        # Check for style overrides in prompt
        prompt_lower = prompt.lower()
        style = template["style"]
        if "dark" in prompt_lower or "neon" in prompt_lower:
            style = "dark"
        elif "minimal" in prompt_lower or "clean" in prompt_lower:
            style = "minimal"
        elif "craft" in prompt_lower or "artisan" in prompt_lower or "warm" in prompt_lower:
            style = "craft"
        elif "bold" in prompt_lower or "swiss" in prompt_lower:
            style = "swiss"
        
        return BriefAnalysis(
            business_type=template["type"],
            brand_personality=template["personality"],
            target_audience=template["audience"],
            primary_goal=template["goal"],
            secondary_goals=["Build brand awareness", "Establish credibility"],
            key_messages=template["messages"],
            required_sections=template["sections"],
            mood=template["mood"],
            visual_style=style,
            special_features=template["features"]
        )
    
    def _create_brief(self, data: Dict) -> BriefAnalysis:
        """Create BriefAnalysis from parsed data."""
        return BriefAnalysis(
            business_type=data.get("business_type", "business"),
            brand_personality=data.get("brand_personality", "professional"),
            target_audience=data.get("target_audience", "general visitors"),
            primary_goal=data.get("primary_goal", "generate leads"),
            secondary_goals=data.get("secondary_goals", []),
            key_messages=data.get("key_messages", []),
            required_sections=data.get("required_sections", ["hero", "about", "contact"]),
            mood=data.get("mood", "professional"),
            visual_style=data.get("visual_style", "minimal"),
            special_features=data.get("special_features", [])
        )


class DesignerAgent:
    """Creates the visual design specification."""
    
    SYSTEM_PROMPT = """You are a world-class UI designer. Create precise design specs.
Output valid JSON only with exact hex codes and values."""

    def design(self, brief: BriefAnalysis) -> DesignSpec:
        """Create design specification from brief."""
        
        backend = get_backend()
        
        # Try AI generation
        if backend.is_ai_enabled:
            user_prompt = f"""Create design spec for:
Business: {brief.business_type}
Personality: {brief.brand_personality}
Mood: {brief.mood}
Style: {brief.visual_style}

Return JSON with exact values:
{{
    "brand_name": "BRAND NAME",
    "tagline": "Tagline",
    "color_primary": "#hexcode",
    "color_secondary": "#hexcode",
    "color_background": "#hexcode",
    "color_text": "#hexcode",
    "color_accent": "#hexcode",
    "color_muted": "#hexcode",
    "font_display": "Font name",
    "font_body": "Font name",
    "font_size_base": "16px",
    "heading_weight": 700,
    "layout_style": "contained or full-width",
    "max_width": "1400px",
    "spacing_unit": "8px",
    "border_radius": "0px or 8px",
    "shadow_style": "none or subtle",
    "image_treatment": "how images look",
    "hover_style": "hover effect type",
    "transition_speed": "0.3s",
    "scroll_behavior": "smooth"
}}"""

            response = backend.generate(
                prompt=user_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                config=GenerationConfig(temperature=0.4, max_tokens=1024),
                json_mode=True
            )
            
            if response:
                try:
                    data = json.loads(response)
                    return self._create_spec(data, brief)
                except json.JSONDecodeError:
                    pass
        
        # Smart template fallback
        return self._template_design(brief)
    
    def _template_design(self, brief: BriefAnalysis) -> DesignSpec:
        """Design using smart templates."""
        style = brief.visual_style
        if style not in STYLE_SPECS:
            style = "minimal"
        
        spec = STYLE_SPECS[style]
        
        # Generate brand name based on business type
        brand_names = {
            "artisan coffee roastery": ("EMBER", "ROASTERS"),
            "architecture firm": ("AXIS", "ARCHITECTS"),
            "restaurant": ("THE", "TABLE"),
            "creative agency": ("FORMA", "STUDIO"),
            "tech startup": ("NOVA", ""),
            "wellness center": ("SERENITY", ""),
        }
        
        name_parts = brand_names.get(brief.business_type, ("STUDIO", ""))
        brand_name = f"{name_parts[0]}\n{name_parts[1]}" if name_parts[1] else name_parts[0]
        
        taglines = {
            "craft": "Crafted with passion",
            "swiss": "Form follows function",
            "minimal": "Less is more",
            "dark": "Enter the void",
            "organic": "Find your balance"
        }
        
        return DesignSpec(
            brand_name=brand_name,
            tagline=taglines.get(style, "Excellence in everything"),
            color_primary=spec["color_primary"],
            color_secondary=spec["color_secondary"],
            color_background=spec["color_background"],
            color_text=spec["color_text"],
            color_accent=spec["color_accent"],
            color_muted=spec["color_muted"],
            font_display=spec["font_display"],
            font_body=spec["font_body"],
            font_size_base=spec["font_size_base"],
            heading_weight=spec["heading_weight"],
            layout_style=spec["layout_style"],
            max_width=spec["max_width"],
            spacing_unit=spec["spacing_unit"],
            border_radius=spec["border_radius"],
            shadow_style=spec["shadow_style"],
            image_treatment=spec["image_treatment"],
            hover_style=spec["hover_style"],
            transition_speed=spec["transition_speed"],
            scroll_behavior=spec["scroll_behavior"]
        )
    
    def _create_spec(self, data: Dict, brief: BriefAnalysis) -> DesignSpec:
        """Create DesignSpec from parsed data with fallbacks."""
        style = brief.visual_style
        defaults = STYLE_SPECS.get(style, STYLE_SPECS["minimal"])
        
        return DesignSpec(
            brand_name=data.get("brand_name", "BRAND"),
            tagline=data.get("tagline", ""),
            color_primary=data.get("color_primary", defaults["color_primary"]),
            color_secondary=data.get("color_secondary", defaults["color_secondary"]),
            color_background=data.get("color_background", defaults["color_background"]),
            color_text=data.get("color_text", defaults["color_text"]),
            color_accent=data.get("color_accent", defaults["color_accent"]),
            color_muted=data.get("color_muted", defaults["color_muted"]),
            font_display=data.get("font_display", defaults["font_display"]),
            font_body=data.get("font_body", defaults["font_body"]),
            font_size_base=data.get("font_size_base", defaults["font_size_base"]),
            heading_weight=data.get("heading_weight", defaults["heading_weight"]),
            layout_style=data.get("layout_style", defaults["layout_style"]),
            max_width=data.get("max_width", defaults["max_width"]),
            spacing_unit=data.get("spacing_unit", defaults["spacing_unit"]),
            border_radius=data.get("border_radius", defaults["border_radius"]),
            shadow_style=data.get("shadow_style", defaults["shadow_style"]),
            image_treatment=data.get("image_treatment", defaults["image_treatment"]),
            hover_style=data.get("hover_style", defaults["hover_style"]),
            transition_speed=data.get("transition_speed", defaults["transition_speed"]),
            scroll_behavior=data.get("scroll_behavior", defaults["scroll_behavior"])
        )


class ArchitectAgent:
    """Plans the page structure and content."""
    
    SYSTEM_PROMPT = """You are a senior UX architect. Create detailed page plans with REAL content.
Output valid JSON only."""

    def plan(self, brief: BriefAnalysis, spec: DesignSpec) -> PagePlan:
        """Create page plan from brief and spec."""
        
        backend = get_backend()
        
        # Try AI generation
        if backend.is_ai_enabled:
            user_prompt = f"""Create page structure for:
Business: {brief.business_type}
Brand: {spec.brand_name}
Sections needed: {brief.required_sections}
Key messages: {brief.key_messages}

Return JSON:
{{
    "nav_items": ["Home", "About", ...],
    "nav_style": "sticky",
    "hero": {{
        "eyebrow": "Small text",
        "headline": "Main headline",
        "subheadline": "Description",
        "cta_primary": "CTA text",
        "cta_secondary": "Secondary CTA"
    }},
    "sections": [
        {{
            "id": "section-id",
            "type": "story|features|products|gallery|process|cta|contact",
            "title": "Section Title",
            "layout": "default|split|grid|cards",
            "content": {{...section specific content...}}
        }}
    ],
    "footer": {{
        "tagline": "Footer text",
        "copyright": "© 2024 Brand"
    }},
    "interactions": ["interaction descriptions"]
}}

Write REAL content, not placeholders."""

            response = backend.generate(
                prompt=user_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                config=GenerationConfig(temperature=0.7, max_tokens=2048),
                json_mode=True
            )
            
            if response:
                try:
                    data = json.loads(response)
                    return self._create_plan(data)
                except json.JSONDecodeError:
                    pass
        
        # Smart template fallback
        return self._template_plan(brief, spec)
    
    def _template_plan(self, brief: BriefAnalysis, spec: DesignSpec) -> PagePlan:
        """Create plan using templates."""
        
        # Build sections based on required_sections
        sections = []
        section_templates = self._get_section_templates(brief)
        
        for i, section_id in enumerate(brief.required_sections):
            if section_id == "hero":
                continue  # Hero is separate
            
            template = section_templates.get(section_id, {
                "type": "content",
                "title": section_id.replace("-", " ").title(),
                "content": {"description": f"Content for {section_id}"}
            })
            
            sections.append(Section(
                id=section_id,
                type=template.get("type", "content"),
                title=template.get("title", section_id.title()),
                content=template.get("content", {}),
                layout=template.get("layout", "default")
            ))
        
        # Build hero
        hero = self._get_hero_template(brief, spec)
        
        # Nav items from sections
        nav_items = ["Home"] + [s.title for s in sections[:4]]
        
        return PagePlan(
            nav_items=nav_items,
            nav_style="sticky",
            hero=hero,
            sections=sections,
            footer={
                "tagline": spec.tagline,
                "copyright": f"© 2024 {spec.brand_name.split()[0]}"
            },
            interactions=["Smooth scroll", "Hover effects", "Scroll animations"]
        )
    
    def _get_hero_template(self, brief: BriefAnalysis, spec: DesignSpec) -> Dict:
        """Get hero content for business type."""
        
        heroes = {
            "artisan coffee roastery": {
                "eyebrow": "ARTISAN COFFEE ROASTERS",
                "headline": "Crafted With Passion",
                "subheadline": "From the highlands to your cup—small-batch roasted coffee with origin and craft at its heart.",
                "cta_primary": "Explore Our Beans",
                "cta_secondary": "Our Story"
            },
            "architecture firm": {
                "eyebrow": "ARCHITECTURE STUDIO",
                "headline": "Form Follows Structure",
                "subheadline": "We design buildings that define their context and elevate the human experience.",
                "cta_primary": "View Projects",
                "cta_secondary": "Our Philosophy"
            },
            "restaurant": {
                "eyebrow": "FINE DINING",
                "headline": "A Feast For The Senses",
                "subheadline": "Fresh ingredients, unforgettable flavors, and moments worth savoring.",
                "cta_primary": "View Menu",
                "cta_secondary": "Reserve a Table"
            },
            "creative agency": {
                "eyebrow": "CREATIVE AGENCY",
                "headline": "We Make Brands Matter",
                "subheadline": "Strategy, design, and technology for brands that want to lead, not follow.",
                "cta_primary": "See Our Work",
                "cta_secondary": "Our Approach"
            },
            "tech startup": {
                "eyebrow": "THE FUTURE IS HERE",
                "headline": "Reimagine What's Possible",
                "subheadline": "We're building the tools that will shape tomorrow.",
                "cta_primary": "Get Started",
                "cta_secondary": "Learn More"
            },
            "wellness center": {
                "eyebrow": "WELLNESS STUDIO",
                "headline": "Find Your Balance",
                "subheadline": "A sanctuary for body, mind, and spirit in the heart of the city.",
                "cta_primary": "Explore Classes",
                "cta_secondary": "Our Philosophy"
            }
        }
        
        return heroes.get(brief.business_type, {
            "eyebrow": brief.business_type.upper(),
            "headline": brief.key_messages[0] if brief.key_messages else "Welcome",
            "subheadline": f"Your trusted partner for {brief.business_type}",
            "cta_primary": "Learn More",
            "cta_secondary": "Contact Us"
        })
    
    def _get_section_templates(self, brief: BriefAnalysis) -> Dict:
        """Get section templates for business type."""
        
        # Coffee-specific sections
        if "coffee" in brief.business_type:
            return {
                "story": {
                    "type": "story",
                    "title": "Our Story",
                    "layout": "split",
                    "content": {
                        "headline": "From Bean to Cup",
                        "description": "Every bean tells a story. From the misty highlands where farmers tend their crops by hand, to the careful roasting that unlocks each origin's unique character.",
                        "points": [
                            {"title": "Sourced with Care", "text": "Direct relationships with farmers across three continents."},
                            {"title": "Roasted Fresh", "text": "Small-batch roasting every week for peak flavor."},
                            {"title": "Crafted by Hand", "text": "Each roast profile refined over hundreds of hours."}
                        ]
                    }
                },
                "beans": {
                    "type": "products",
                    "title": "Our Beans",
                    "layout": "grid",
                    "content": {
                        "items": [
                            {"name": "Ethiopian Yirgacheffe", "notes": "Floral, citrus, jasmine", "roast": "Light"},
                            {"name": "Colombian Supremo", "notes": "Caramel, nutty, balanced", "roast": "Medium"},
                            {"name": "Sumatra Mandheling", "notes": "Earthy, spice, dark chocolate", "roast": "Dark"},
                            {"name": "House Blend", "notes": "Smooth, rich, versatile", "roast": "Medium-Dark"}
                        ]
                    }
                },
                "process": {
                    "type": "process",
                    "title": "The Process",
                    "layout": "steps",
                    "content": {
                        "steps": [
                            {"number": "01", "title": "Sourcing", "description": "We travel to origin, meeting farmers and selecting the finest harvests."},
                            {"number": "02", "title": "Cupping", "description": "Each lot is carefully evaluated for flavor, aroma, and consistency."},
                            {"number": "03", "title": "Roasting", "description": "Small batches ensure precise control and consistent quality."},
                            {"number": "04", "title": "Delivery", "description": "Roasted fresh and shipped within 24 hours."}
                        ]
                    }
                },
                "visit": {
                    "type": "location",
                    "title": "Visit Us",
                    "layout": "split",
                    "content": {
                        "headline": "Experience the craft in person",
                        "address": "42 Roastery Lane\nBrooklyn, NY 11201",
                        "hours": "Mon-Fri 7am-6pm\nSat-Sun 8am-5pm",
                        "features": ["Tasting room", "Brewing classes", "Bean subscriptions"]
                    }
                },
                "contact": {
                    "type": "contact",
                    "title": "Get in Touch",
                    "layout": "split",
                    "content": {
                        "headline": "Questions? We'd love to hear from you.",
                        "email": "hello@emberroasters.com",
                        "phone": "(555) 123-4567"
                    }
                }
            }
        
        # Architecture sections
        if "architect" in brief.business_type:
            return {
                "philosophy": {
                    "type": "philosophy",
                    "title": "Philosophy",
                    "layout": "split",
                    "content": {
                        "statement": "Architecture is the thoughtful making of space.",
                        "principles": [
                            {"title": "Context", "text": "Every site tells a story. We listen."},
                            {"title": "Material", "text": "Honest use of materials defines our work."},
                            {"title": "Light", "text": "Natural light shapes every space."}
                        ]
                    }
                },
                "projects": {
                    "type": "gallery",
                    "title": "Selected Projects",
                    "layout": "grid",
                    "content": {
                        "items": [
                            {"title": "Concrete House", "category": "Residential", "year": "2024"},
                            {"title": "Museum Extension", "category": "Cultural", "year": "2024"},
                            {"title": "Office Tower", "category": "Commercial", "year": "2023"},
                            {"title": "Waterfront Pavilion", "category": "Public", "year": "2023"}
                        ]
                    }
                },
                "awards": {
                    "type": "list",
                    "title": "Recognition",
                    "layout": "default",
                    "content": {
                        "items": [
                            {"title": "AIA Honor Award", "year": "2024"},
                            {"title": "Architectural Review Award", "year": "2023"}
                        ]
                    }
                },
                "contact": {
                    "type": "contact",
                    "title": "Start a Project",
                    "layout": "split",
                    "content": {
                        "headline": "Let's discuss your vision.",
                        "email": "studio@axisarchitects.com"
                    }
                }
            }
        
        # Default sections
        return {
            "about": {
                "type": "about",
                "title": "About",
                "layout": "split",
                "content": {
                    "headline": f"About {brief.business_type}",
                    "description": brief.key_messages[0] if brief.key_messages else "We deliver excellence."
                }
            },
            "services": {
                "type": "services",
                "title": "Services",
                "layout": "grid",
                "content": {
                    "items": [
                        {"title": "Service One", "description": "Description of service."},
                        {"title": "Service Two", "description": "Description of service."},
                        {"title": "Service Three", "description": "Description of service."}
                    ]
                }
            },
            "contact": {
                "type": "contact",
                "title": "Contact",
                "layout": "split",
                "content": {
                    "headline": "Get in touch",
                    "email": "hello@example.com"
                }
            }
        }
    
    def _create_plan(self, data: Dict) -> PagePlan:
        """Create PagePlan from parsed data."""
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


class BuilderAgent:
    """Generates the actual HTML, CSS, and JavaScript code."""
    
    def build(self, spec: DesignSpec, plan: PagePlan) -> GeneratedCode:
        """Generate HTML, CSS, and JS from spec and plan."""
        
        backend = get_backend()
        
        # For now, use template generation (fast and reliable)
        # AI generation can be added later for customization
        html = self._generate_html_template(spec, plan)
        css = self._generate_css_template(spec)
        js = self._generate_js_template(spec, plan)
        
        return GeneratedCode(html=html, css=css, js=js)
    
    def _generate_html_template(self, spec: DesignSpec, plan: PagePlan) -> str:
        """Generate HTML using templates."""
        
        # Navigation
        nav_links = "\n".join([
            f'            <a href="#{item.lower().replace(" ", "-")}" class="nav-link">{item}</a>'
            for item in plan.nav_items
        ])
        
        # Hero
        hero = plan.hero
        hero_html = f'''
    <!-- Hero Section -->
    <section id="home" class="hero">
        <div class="hero-content">
            <span class="hero-eyebrow">{hero.get("eyebrow", "")}</span>
            <h1 class="hero-headline">{hero.get("headline", "Welcome")}</h1>
            <p class="hero-subheadline">{hero.get("subheadline", "")}</p>
            <div class="hero-ctas">
                <a href="#contact" class="btn btn-primary">{hero.get("cta_primary", "Learn More")}</a>
                <a href="#about" class="btn btn-secondary">{hero.get("cta_secondary", "About")}</a>
            </div>
        </div>
    </section>
'''
        
        # Sections
        sections_html = ""
        for section in plan.sections:
            sections_html += self._render_section(section)
        
        # Footer
        footer = plan.footer
        footer_html = f'''
    <!-- Footer -->
    <footer class="footer">
        <div class="footer-content">
            <p class="footer-tagline">{footer.get("tagline", "")}</p>
            <p class="footer-copyright">{footer.get("copyright", "© 2024")}</p>
        </div>
    </footer>
'''
        
        # Combine
        brand_lines = spec.brand_name.split('\n')
        brand_display = '<br>'.join(brand_lines)
        
        return f'''
    <!-- Navigation -->
    <nav class="nav">
        <div class="nav-container">
            <a href="#" class="nav-logo">{brand_display}</a>
            <div class="nav-links">
{nav_links}
            </div>
            <button class="nav-toggle" aria-label="Toggle menu">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </div>
    </nav>
{hero_html}
    <!-- Main Content -->
    <main class="main">
{sections_html}
    </main>
{footer_html}
'''
    
    def _render_section(self, section: Section) -> str:
        """Render a section to HTML."""
        content = section.content
        
        if section.type == "story":
            points_html = ""
            for point in content.get("points", []):
                points_html += f'''
                <div class="story-point">
                    <h4>{point.get("title", "")}</h4>
                    <p>{point.get("text", "")}</p>
                </div>'''
            
            return f'''
        <section id="{section.id}" class="section section-story">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="story-content">
                    <div class="story-main">
                        <h3 class="story-headline">{content.get("headline", "")}</h3>
                        <p class="story-description">{content.get("description", "")}</p>
                    </div>
                    <div class="story-points">
{points_html}
                    </div>
                </div>
            </div>
        </section>
'''
        
        elif section.type == "products":
            items_html = ""
            for item in content.get("items", []):
                items_html += f'''
                <div class="product-card">
                    <h4 class="product-name">{item.get("name", "")}</h4>
                    <p class="product-notes">{item.get("notes", "")}</p>
                    <span class="product-roast">{item.get("roast", "")}</span>
                </div>'''
            
            return f'''
        <section id="{section.id}" class="section section-products">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="products-grid">
{items_html}
                </div>
            </div>
        </section>
'''
        
        elif section.type == "process":
            steps_html = ""
            for step in content.get("steps", []):
                steps_html += f'''
                <div class="process-step">
                    <span class="step-number">{step.get("number", "")}</span>
                    <h4 class="step-title">{step.get("title", "")}</h4>
                    <p class="step-description">{step.get("description", "")}</p>
                </div>'''
            
            return f'''
        <section id="{section.id}" class="section section-process">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="process-steps">
{steps_html}
                </div>
            </div>
        </section>
'''
        
        elif section.type == "location":
            features_html = ""
            for feature in content.get("features", []):
                features_html += f'<li>{feature}</li>'
            
            return f'''
        <section id="{section.id}" class="section section-location">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="location-content">
                    <div class="location-info">
                        <h3>{content.get("headline", "")}</h3>
                        <address>{content.get("address", "").replace(chr(10), "<br>")}</address>
                        <p class="hours">{content.get("hours", "").replace(chr(10), "<br>")}</p>
                    </div>
                    <ul class="location-features">
{features_html}
                    </ul>
                </div>
            </div>
        </section>
'''
        
        elif section.type == "gallery":
            items_html = ""
            for item in content.get("items", []):
                items_html += f'''
                <div class="gallery-item">
                    <div class="gallery-image"></div>
                    <h4 class="gallery-title">{item.get("title", "")}</h4>
                    <p class="gallery-meta">{item.get("category", "")} · {item.get("year", "")}</p>
                </div>'''
            
            return f'''
        <section id="{section.id}" class="section section-gallery">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="gallery-grid">
{items_html}
                </div>
            </div>
        </section>
'''
        
        elif section.type == "contact":
            return f'''
        <section id="{section.id}" class="section section-contact">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <div class="contact-content">
                    <div class="contact-info">
                        <h3>{content.get("headline", "Get in touch")}</h3>
                        <p><a href="mailto:{content.get("email", "")}">{content.get("email", "")}</a></p>
                        <p>{content.get("phone", "")}</p>
                    </div>
                    <form class="contact-form">
                        <input type="text" placeholder="Name" required>
                        <input type="email" placeholder="Email" required>
                        <textarea placeholder="Message" rows="4" required></textarea>
                        <button type="submit" class="btn btn-primary">Send Message</button>
                    </form>
                </div>
            </div>
        </section>
'''
        
        # Default section
        return f'''
        <section id="{section.id}" class="section">
            <div class="section-container">
                <h2 class="section-title">{section.title}</h2>
                <p>{content.get("description", "")}</p>
            </div>
        </section>
'''
    
    def _generate_css_template(self, spec: DesignSpec) -> str:
        """Generate CSS using design spec."""
        
        return f'''
/* ==========================================================================
   CSS Variables (Design Tokens)
   ========================================================================== */

:root {{
    /* Colors */
    --color-primary: {spec.color_primary};
    --color-secondary: {spec.color_secondary};
    --color-background: {spec.color_background};
    --color-text: {spec.color_text};
    --color-accent: {spec.color_accent};
    --color-muted: {spec.color_muted};
    
    /* Typography */
    --font-display: {spec.font_display};
    --font-body: {spec.font_body};
    --font-size-base: {spec.font_size_base};
    --heading-weight: {spec.heading_weight};
    
    /* Layout */
    --max-width: {spec.max_width};
    --spacing: {spec.spacing_unit};
    --radius: {spec.border_radius};
    
    /* Transitions */
    --transition: {spec.transition_speed} ease;
}}

/* ==========================================================================
   Reset & Base
   ========================================================================== */

*, *::before, *::after {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

html {{
    scroll-behavior: {spec.scroll_behavior};
}}

body {{
    font-family: var(--font-body);
    font-size: var(--font-size-base);
    line-height: 1.6;
    color: var(--color-text);
    background-color: var(--color-background);
}}

/* ==========================================================================
   Typography
   ========================================================================== */

h1, h2, h3, h4 {{
    font-family: var(--font-display);
    font-weight: var(--heading-weight);
    line-height: 1.2;
}}

h1 {{ font-size: clamp(2.5rem, 6vw, 4.5rem); }}
h2 {{ font-size: clamp(1.75rem, 4vw, 2.5rem); }}
h3 {{ font-size: clamp(1.25rem, 2vw, 1.5rem); }}

a {{
    color: var(--color-accent);
    text-decoration: none;
    transition: var(--transition);
}}

a:hover {{
    opacity: 0.8;
}}

/* ==========================================================================
   Navigation
   ========================================================================== */

.nav {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--color-background);
    border-bottom: 1px solid rgba(0,0,0,0.1);
}}

.nav-container {{
    max-width: var(--max-width);
    margin: 0 auto;
    padding: calc(var(--spacing) * 2) calc(var(--spacing) * 3);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.nav-logo {{
    font-family: var(--font-display);
    font-weight: var(--heading-weight);
    font-size: 1.25rem;
    color: var(--color-text);
    line-height: 1.2;
}}

.nav-links {{
    display: flex;
    gap: calc(var(--spacing) * 4);
}}

.nav-link {{
    color: var(--color-text);
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.nav-link:hover {{
    color: var(--color-accent);
}}

.nav-toggle {{
    display: none;
    flex-direction: column;
    gap: 4px;
    background: none;
    border: none;
    cursor: pointer;
}}

.nav-toggle span {{
    width: 24px;
    height: 2px;
    background: var(--color-text);
    transition: var(--transition);
}}

/* ==========================================================================
   Hero
   ========================================================================== */

.hero {{
    min-height: 90vh;
    display: flex;
    align-items: center;
    padding: calc(var(--spacing) * 8) calc(var(--spacing) * 3);
}}

.hero-content {{
    max-width: var(--max-width);
    margin: 0 auto;
    width: 100%;
}}

.hero-eyebrow {{
    display: block;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-muted);
    margin-bottom: calc(var(--spacing) * 2);
}}

.hero-headline {{
    margin-bottom: calc(var(--spacing) * 3);
}}

.hero-subheadline {{
    font-size: 1.25rem;
    color: var(--color-muted);
    max-width: 600px;
    margin-bottom: calc(var(--spacing) * 4);
}}

.hero-ctas {{
    display: flex;
    gap: calc(var(--spacing) * 2);
    flex-wrap: wrap;
}}

/* ==========================================================================
   Buttons
   ========================================================================== */

.btn {{
    display: inline-block;
    padding: calc(var(--spacing) * 1.5) calc(var(--spacing) * 3);
    border-radius: var(--radius);
    font-size: 0.875rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    transition: var(--transition);
    border: 2px solid transparent;
    cursor: pointer;
}}

.btn-primary {{
    background: var(--color-accent);
    color: var(--color-background);
    border-color: var(--color-accent);
}}

.btn-primary:hover {{
    background: transparent;
    color: var(--color-accent);
}}

.btn-secondary {{
    background: transparent;
    color: var(--color-text);
    border-color: var(--color-text);
}}

.btn-secondary:hover {{
    background: var(--color-text);
    color: var(--color-background);
}}

/* ==========================================================================
   Sections
   ========================================================================== */

.section {{
    padding: calc(var(--spacing) * 10) calc(var(--spacing) * 3);
}}

.section-container {{
    max-width: var(--max-width);
    margin: 0 auto;
}}

.section-title {{
    margin-bottom: calc(var(--spacing) * 6);
}}

/* Story Section */
.story-content {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: calc(var(--spacing) * 6);
}}

.story-headline {{
    margin-bottom: calc(var(--spacing) * 2);
}}

.story-description {{
    color: var(--color-muted);
    font-size: 1.125rem;
}}

.story-points {{
    display: flex;
    flex-direction: column;
    gap: calc(var(--spacing) * 3);
}}

.story-point h4 {{
    margin-bottom: calc(var(--spacing) * 0.5);
    color: var(--color-accent);
}}

/* Products Section */
.products-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: calc(var(--spacing) * 3);
}}

.product-card {{
    padding: calc(var(--spacing) * 3);
    background: rgba(0,0,0,0.03);
    border-radius: var(--radius);
    transition: var(--transition);
}}

.product-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}}

.product-name {{
    margin-bottom: calc(var(--spacing) * 1);
}}

.product-notes {{
    color: var(--color-muted);
    font-size: 0.875rem;
    margin-bottom: calc(var(--spacing) * 2);
}}

.product-roast {{
    display: inline-block;
    padding: calc(var(--spacing) * 0.5) calc(var(--spacing) * 1.5);
    background: var(--color-accent);
    color: var(--color-background);
    font-size: 0.75rem;
    text-transform: uppercase;
    border-radius: var(--radius);
}}

/* Process Section */
.process-steps {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: calc(var(--spacing) * 4);
}}

.process-step {{
    text-align: center;
}}

.step-number {{
    display: block;
    font-family: var(--font-display);
    font-size: 3rem;
    font-weight: var(--heading-weight);
    color: var(--color-accent);
    opacity: 0.3;
    margin-bottom: calc(var(--spacing) * 1);
}}

.step-title {{
    margin-bottom: calc(var(--spacing) * 1);
}}

.step-description {{
    color: var(--color-muted);
    font-size: 0.875rem;
}}

/* Location Section */
.location-content {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: calc(var(--spacing) * 6);
}}

.location-info h3 {{
    margin-bottom: calc(var(--spacing) * 2);
}}

.location-info address {{
    font-style: normal;
    margin-bottom: calc(var(--spacing) * 2);
}}

.hours {{
    color: var(--color-muted);
}}

.location-features {{
    list-style: none;
}}

.location-features li {{
    padding: calc(var(--spacing) * 1.5) 0;
    border-bottom: 1px solid rgba(0,0,0,0.1);
}}

/* Gallery Section */
.gallery-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: calc(var(--spacing) * 3);
}}

.gallery-item {{
    cursor: pointer;
}}

.gallery-image {{
    aspect-ratio: 4/3;
    background: linear-gradient(135deg, var(--color-muted) 0%, var(--color-text) 100%);
    border-radius: var(--radius);
    margin-bottom: calc(var(--spacing) * 2);
    transition: var(--transition);
}}

.gallery-item:hover .gallery-image {{
    transform: scale(1.02);
}}

.gallery-title {{
    margin-bottom: calc(var(--spacing) * 0.5);
}}

.gallery-meta {{
    color: var(--color-muted);
    font-size: 0.875rem;
}}

/* Contact Section */
.contact-content {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: calc(var(--spacing) * 6);
}}

.contact-info h3 {{
    margin-bottom: calc(var(--spacing) * 2);
}}

.contact-form {{
    display: flex;
    flex-direction: column;
    gap: calc(var(--spacing) * 2);
}}

.contact-form input,
.contact-form textarea {{
    padding: calc(var(--spacing) * 1.5);
    border: 1px solid rgba(0,0,0,0.2);
    border-radius: var(--radius);
    font-family: var(--font-body);
    font-size: 1rem;
    background: transparent;
    transition: var(--transition);
}}

.contact-form input:focus,
.contact-form textarea:focus {{
    outline: none;
    border-color: var(--color-accent);
}}

/* ==========================================================================
   Footer
   ========================================================================== */

.footer {{
    padding: calc(var(--spacing) * 6) calc(var(--spacing) * 3);
    border-top: 1px solid rgba(0,0,0,0.1);
}}

.footer-content {{
    max-width: var(--max-width);
    margin: 0 auto;
    text-align: center;
}}

.footer-tagline {{
    font-family: var(--font-display);
    margin-bottom: calc(var(--spacing) * 2);
}}

.footer-copyright {{
    color: var(--color-muted);
    font-size: 0.875rem;
}}

/* ==========================================================================
   Responsive
   ========================================================================== */

@media (max-width: 768px) {{
    .nav-links {{
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--color-background);
        flex-direction: column;
        padding: calc(var(--spacing) * 2);
        border-bottom: 1px solid rgba(0,0,0,0.1);
    }}
    
    .nav-links.active {{
        display: flex;
    }}
    
    .nav-toggle {{
        display: flex;
    }}
    
    .story-content,
    .location-content,
    .contact-content {{
        grid-template-columns: 1fr;
    }}
    
    .hero {{
        min-height: 70vh;
    }}
}}
'''
    
    def _generate_js_template(self, spec: DesignSpec, plan: PagePlan) -> str:
        """Generate JavaScript for interactions."""
        
        return '''
// Mobile Navigation Toggle
const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');

if (navToggle) {
    navToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });
}

// Smooth Scroll for Navigation Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
            navLinks.classList.remove('active');
        }
    });
});

// Scroll Reveal Animation
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

document.querySelectorAll('.section').forEach(section => {
    section.style.opacity = '0';
    section.style.transform = 'translateY(20px)';
    section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(section);
});

// Add revealed class styles
const style = document.createElement('style');
style.textContent = '.revealed { opacity: 1 !important; transform: translateY(0) !important; }';
document.head.appendChild(style);

// Form Submission
const contactForm = document.querySelector('.contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Thank you for your message! We will get back to you soon.');
        contactForm.reset();
    });
}
'''
