from __future__ import annotations

from .common import DesignSystem, FileArtifact, GeneratedSite, PageSpec, Section, SiteStrategy


class EngineerAgent:
    def _build_index_html(self, strategy: SiteStrategy, design: DesignSystem, project_name: str) -> str:
        title = project_name or strategy.pages[0].title if strategy.pages else "Sovrn Site"
        primary = design.tokens.colors.primary
        background = design.tokens.colors.background
        text = design.tokens.colors.text
        sections_html = "\n".join(
            f"<section id='{section.type}'><h2>{section.title}</h2><p>{section.purpose}</p></section>"
            for section in design.sections
        )

        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{ --primary: {primary}; --bg: {background}; --text: {text}; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: {design.tokens.typography.font_family_body}, system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    header, section, footer {{ padding: 2rem; max-width: 1120px; margin: 0 auto; }}
    h1, h2 {{ font-family: {design.tokens.typography.font_family_heading}, system-ui, sans-serif; }}
    .btn {{ display: inline-block; background: var(--primary); color: white; padding: .9rem 1.25rem; border-radius: .75rem; text-decoration: none; }}
    section {{ border-top: 1px solid rgba(255,255,255,.08); }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>{strategy.value_proposition}</p>
    <a class=\"btn\" href=\"#contact\">{strategy.call_to_action}</a>
  </header>
  {sections_html}
  <footer id=\"contact\">Built with Sovrn</footer>
</body>
</html>"""

    def generate(self, strategy: SiteStrategy, design: DesignSystem, project_name: str = "") -> GeneratedSite:
        pages = strategy.pages or design.pages
        components = list(dict.fromkeys(design.components + [page.slug for page in pages]))
        index_html = self._build_index_html(strategy, design, project_name)

        files = [
            FileArtifact(path="app/page.tsx", content=index_html, language="tsx"),
            FileArtifact(path="app/globals.css", content="body { margin: 0; }", language="css"),
            FileArtifact(path="components/Hero.tsx", content="export function Hero() { return null; }", language="tsx"),
            FileArtifact(path="components/Section.tsx", content="export function Section() { return null; }", language="tsx"),
        ]

        return GeneratedSite(
            files=files,
            pages=pages,
            components=components,
            dependencies={"next": "^14.0.0", "react": "^18.0.0", "typescript": "^5.0.0"},
            tests={"smoke": "renders a page with header, sections, and footer"},
        )

    async def generate_page(
        self,
        page_spec: PageSpec,
        design: DesignSystem,
        components_library: str = "react",
    ) -> GeneratedSite:
        strategy = SiteStrategy(
            business_goal=None,  # type: ignore[arg-type]
            value_proposition=page_spec.purpose or page_spec.title,
            target_audience=None,  # type: ignore[arg-type]
            pages=[page_spec],
        )
        return self.generate(strategy=strategy, design=design, project_name=page_spec.title)


engineer_agent = EngineerAgent()
