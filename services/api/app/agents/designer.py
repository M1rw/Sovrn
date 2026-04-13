from __future__ import annotations

from typing import Any

from .common import (
    ColorTokens,
    CulturalAdaptation,
    DesignSystem,
    DesignTokens,
    PageSpec,
    Section,
    SiteStrategy,
    TypographyTokens,
)


class DesignerAgent:
    def _theme_from_strategy(self, strategy: SiteStrategy) -> tuple[str, ColorTokens, TypographyTokens]:
        text = f"{strategy.business_goal.primary} {strategy.value_proposition} {strategy.brand_voice}".lower()
        if any(keyword in text for keyword in ["coffee", "warm", "restaurant", "food"]):
            return (
                "warm-modern",
                ColorTokens(primary="#8b4513", secondary="#d2691e", background="#0f0f10", text="#f8f4ef"),
                TypographyTokens(font_family_heading="Inter", font_family_body="Inter"),
            )
        if any(keyword in text for keyword in ["portfolio", "creative", "design"]):
            return (
                "editorial-minimal",
                ColorTokens(primary="#111827", secondary="#6b7280", background="#fafafa", text="#111827"),
                TypographyTokens(font_family_heading="Manrope", font_family_body="Inter"),
            )
        return (
            "modern-product",
            ColorTokens(primary="#6366f1", secondary="#a855f7", background="#0a0a0a", text="#ffffff"),
            TypographyTokens(font_family_heading="Inter", font_family_body="Inter"),
        )

    async def design(
        self,
        strategy: SiteStrategy,
        locale: str = "en",
        country_code: str = "US",
        brand_guidelines: dict[str, Any] | None = None,
    ) -> DesignSystem:
        theme, colors, typography = self._theme_from_strategy(strategy)
        guidelines = brand_guidelines or {}
        direction = "rtl" if locale.startswith(("ar", "he", "fa", "ur")) or country_code in {"AE", "SA"} and locale.startswith("ar") else "ltr"

        sections = []
        for page in strategy.pages:
            sections.append(
                Section(
                    type=page.slug,
                    title=page.title,
                    purpose=page.purpose,
                    content={"call_to_action": strategy.call_to_action},
                )
            )

        components = ["hero", "feature-grid", "testimonials", "footer"]
        if any(page.slug == "menu" for page in strategy.pages):
            components.append("menu-grid")
        if any(page.slug == "contact" for page in strategy.pages):
            components.append("contact-form")

        return DesignSystem(
            layout=guidelines.get("layout", "responsive-grid"),
            style_theme=theme,
            sections=sections,
            components=components,
            pages=strategy.pages,
            tokens=DesignTokens(colors=colors, typography=typography),
            cultural_adaptation=CulturalAdaptation(direction=direction, locale=locale),
        )

    async def design_page(
        self,
        page_spec: PageSpec,
        brand_voice: str = "clear, confident, helpful",
        value_prop: str = "",
    ) -> DesignSystem:
        strategy = SiteStrategy(
            business_goal=None,  # type: ignore[arg-type]
            value_proposition=value_prop or brand_voice,
            target_audience=None,  # type: ignore[arg-type]
            pages=[page_spec],
            brand_voice=brand_voice,
        )
        design = await self.design(strategy=strategy)
        design.sections = [
            Section(
                type=page_spec.slug,
                title=page_spec.title,
                purpose=page_spec.purpose,
                content={"brand_voice": brand_voice, "value_prop": value_prop},
            )
        ]
        return design


designer_agent = DesignerAgent()
