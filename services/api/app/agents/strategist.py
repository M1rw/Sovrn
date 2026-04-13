from __future__ import annotations

from typing import Any

from .common import BusinessGoal, PageSpec, SiteStrategy, TargetAudience


class StrategistAgent:
    def analyze(
        self,
        brief: str,
        locale: str = "en",
        industry: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> SiteStrategy:
        text = brief.lower()
        industry_text = (industry or "").lower()
        context = additional_context or {}

        if any(keyword in text for keyword in ["coffee", "restaurant", "food", "cafe"]):
            goal = "drive local visits and online orders"
            value_prop = "A warm, inviting brand experience that turns visitors into customers."
            audience = "Local customers who value quality, convenience, and trust."
            pages = [
                PageSpec("Home", "home", "Introduce the brand and top offers"),
                PageSpec("Menu", "menu", "Show products and pricing"),
                PageSpec("About", "about", "Tell the brand story"),
                PageSpec("Contact", "contact", "Capture calls, directions, and reservations"),
            ]
        elif any(keyword in text for keyword in ["portfolio", "designer", "creative"]):
            goal = "showcase work and win inbound leads"
            value_prop = "A polished portfolio that makes quality and taste obvious fast."
            audience = "Potential clients evaluating creative work and fit."
            pages = [
                PageSpec("Home", "home", "Brand introduction and featured work"),
                PageSpec("Projects", "projects", "Showcase selected work"),
                PageSpec("About", "about", "Explain background and approach"),
                PageSpec("Contact", "contact", "Make hiring easy"),
            ]
        else:
            goal = "convert traffic into qualified leads"
            value_prop = "A focused, conversion-oriented website that reduces friction and explains value quickly."
            audience = "Visitors who need fast clarity about the product or service."
            pages = [
                PageSpec("Home", "home", "Primary landing page"),
                PageSpec("Features", "features", "Explain key benefits"),
                PageSpec("About", "about", "Build trust"),
                PageSpec("Contact", "contact", "Capture conversions"),
            ]

        if context.get("business_model"):
            goal = f"{goal} for a {context['business_model']} model"

        if industry_text:
            value_prop = f"{value_prop} Tailored for the {industry_text} domain."

        return SiteStrategy(
            business_goal=BusinessGoal(primary=goal, confidence=0.82),
            value_proposition=value_prop,
            target_audience=TargetAudience(demographics=audience, needs=["clear CTA", "trust", "mobile-first layout"]),
            pages=pages,
            brand_voice=context.get("brand_voice", "clear, confident, helpful"),
            call_to_action=context.get("cta", "Get started"),
        )

    async def create_strategy(self, brief: str) -> SiteStrategy:
        return self.analyze(brief=brief)


strategist_agent = StrategistAgent()
