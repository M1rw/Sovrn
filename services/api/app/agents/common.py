from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BusinessGoal:
    primary: str
    confidence: float = 0.75


@dataclass
class TargetAudience:
    demographics: str
    needs: list[str] = field(default_factory=list)


@dataclass
class PageSpec:
    title: str
    slug: str
    purpose: str = ""


@dataclass
class Section:
    type: str
    title: str
    purpose: str = ""
    content: dict[str, Any] = field(default_factory=dict)


@dataclass
class TypographyTokens:
    font_family_heading: str
    font_family_body: str


@dataclass
class ColorTokens:
    primary: str
    secondary: str
    background: str
    text: str


@dataclass
class DesignTokens:
    colors: ColorTokens
    typography: TypographyTokens


@dataclass
class CulturalAdaptation:
    direction: str = "ltr"
    locale: str = "en"


@dataclass
class DesignSystem:
    layout: str
    style_theme: str
    sections: list[Section] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    pages: list[PageSpec] = field(default_factory=list)
    tokens: DesignTokens = field(
        default_factory=lambda: DesignTokens(
            colors=ColorTokens(
                primary="#6366f1",
                secondary="#a855f7",
                background="#0a0a0a",
                text="#ffffff",
            ),
            typography=TypographyTokens(
                font_family_heading="Inter",
                font_family_body="Inter",
            ),
        )
    )
    cultural_adaptation: CulturalAdaptation = field(default_factory=CulturalAdaptation)


@dataclass
class SiteStrategy:
    business_goal: BusinessGoal
    value_proposition: str
    target_audience: TargetAudience
    pages: list[PageSpec] = field(default_factory=list)
    brand_voice: str = "clear, confident, helpful"
    call_to_action: str = "Get started"


@dataclass
class FileArtifact:
    path: str
    content: str
    language: str = "tsx"


@dataclass
class GeneratedSite:
    files: list[FileArtifact] = field(default_factory=list)
    pages: list[PageSpec] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    tests: dict[str, str] = field(default_factory=dict)
