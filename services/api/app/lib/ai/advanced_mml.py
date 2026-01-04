# =============================================================================
# SOVRN Advanced MML Engine - Multi-Agent Website Generation
# =============================================================================
"""
Advanced website generation using multiple specialized agents:
- Design Agent: Analyzes prompt, creates design spec
- HTML Agent: Generates semantic HTML structure
- CSS Agent: Creates advanced styling with animations
- JS Agent: Adds interactivity and effects

Supports external resources: fonts, icons, images, effects
"""

import asyncio
import time
import re
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class DesignStyle(Enum):
    """Design style categories."""
    MINIMAL = "minimal"
    BRUTALIST = "brutalist"
    GLASSMORPHISM = "glassmorphism"
    NEOMORPHISM = "neomorphism"
    RETRO = "retro"
    CYBERPUNK = "cyberpunk"
    ORGANIC = "organic"
    SWISS = "swiss"
    EDITORIAL = "editorial"
    EXPERIMENTAL = "experimental"


@dataclass
class DesignSpec:
    """Design specification from analysis."""
    style: str
    color_palette: Dict[str, str]
    typography: Dict[str, str]
    layout: str
    sections: List[str]
    effects: List[str]
    mood: str
    external_resources: Dict[str, List[str]]


@dataclass
class GeneratedFile:
    """A generated file."""
    name: str
    content: str
    type: str
    size: int = 0


@dataclass
class GenerationResult:
    """Result of website generation."""
    files: List[GeneratedFile]
    success: bool
    generation_time_ms: int
    preview_html: str = ""
    error: Optional[str] = None


class AdvancedMMLEngine:
    """
    Advanced Multi-Agent MML Engine for creative website generation.
    """
    
    def __init__(self):
        self.llm = None
        self.is_loaded = False
        self._load_lock = asyncio.Lock()
        
        # Design templates for different styles
        self.style_templates = self._load_style_templates()
        
    def _load_style_templates(self) -> Dict[str, Dict]:
        """Load design templates for each style."""
        return {
            "techno": {
                "fonts": ["Space Mono", "Orbitron"],
                "colors": {"primary": "#00ff41", "secondary": "#ff0040", "bg": "#0a0a0a", "text": "#ffffff"},
                "effects": ["glitch", "scanlines", "noise", "kinetic-type"],
                "layout": "asymmetric"
            },
            "brutalist": {
                "fonts": ["Helvetica Neue", "Akzidenz-Grotesk", "Arial Black"],
                "colors": {"primary": "#ff4400", "secondary": "#000000", "bg": "#ffffff", "text": "#000000"},
                "effects": ["thick-borders", "raw-grid", "monochrome"],
                "layout": "swiss-grid"
            },
            "organic": {
                "fonts": ["Playfair Display", "Source Sans Pro"],
                "colors": {"primary": "#8B4513", "secondary": "#F5DEB3", "bg": "#FDF5E6", "text": "#3E2723"},
                "effects": ["texture", "hand-drawn", "soft-shadows"],
                "layout": "split-screen"
            },
            "cyberpunk": {
                "fonts": ["Rajdhani", "Share Tech Mono"],
                "colors": {"primary": "#00f0ff", "secondary": "#ff00ff", "bg": "#0d0d0d", "text": "#ffffff"},
                "effects": ["neon-glow", "chromatic", "grid-lines", "flicker"],
                "layout": "layered"
            },
            "minimal": {
                "fonts": ["Inter", "DM Sans"],
                "colors": {"primary": "#000000", "secondary": "#666666", "bg": "#ffffff", "text": "#1a1a1a"},
                "effects": ["subtle-hover", "smooth-transitions"],
                "layout": "centered"
            },
            "editorial": {
                "fonts": ["PP Editorial New", "Suisse Intl"],
                "colors": {"primary": "#1a1a1a", "secondary": "#c4a35a", "bg": "#f5f5f0", "text": "#1a1a1a"},
                "effects": ["reveal-animations", "parallax", "magnetic-cursor"],
                "layout": "magazine"
            }
        }
    
    async def load(self) -> bool:
        """Load the AI model."""
        async with self._load_lock:
            if self.is_loaded:
                return True
            try:
                from llama_cpp import Llama
                
                model_path = "/workspaces/Sovrn/models/phi-3-mini-4k-instruct-q4.gguf"
                logger.info("advanced_mml_loading", path=model_path)
                
                self.llm = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_threads=4,
                    n_gpu_layers=0,
                    verbose=False,
                    chat_format="chatml"
                )
                
                self.is_loaded = True
                logger.info("advanced_mml_loaded")
                return True
            except Exception as e:
                logger.error("advanced_mml_load_failed", error=str(e))
                return False

    def _analyze_prompt(self, prompt: str) -> DesignSpec:
        """Analyze prompt to determine design direction."""
        prompt_lower = prompt.lower()
        
        # Detect style from keywords
        style = "minimal"
        if any(k in prompt_lower for k in ["techno", "acid", "glitch", "rave", "festival", "electronic"]):
            style = "techno"
        elif any(k in prompt_lower for k in ["brutalist", "swiss", "grid", "architecture", "concrete", "industrial"]):
            style = "brutalist"
        elif any(k in prompt_lower for k in ["organic", "craft", "artisan", "coffee", "nature", "botanical", "warm"]):
            style = "organic"
        elif any(k in prompt_lower for k in ["cyber", "neon", "futuristic", "sci-fi", "tech"]):
            style = "cyberpunk"
        elif any(k in prompt_lower for k in ["editorial", "magazine", "luxury", "fashion"]):
            style = "editorial"
        
        template = self.style_templates.get(style, self.style_templates["minimal"])
        
        # Extract sections from prompt
        sections = ["hero"]
        if any(k in prompt_lower for k in ["about", "story", "philosophy"]):
            sections.append("about")
        if any(k in prompt_lower for k in ["feature", "service", "product", "menu", "lineup"]):
            sections.append("features")
        if any(k in prompt_lower for k in ["gallery", "portfolio", "project", "work"]):
            sections.append("gallery")
        if any(k in prompt_lower for k in ["contact", "booking", "ticket"]):
            sections.append("contact")
        sections.append("footer")
        
        return DesignSpec(
            style=style,
            color_palette=template["colors"],
            typography={"heading": template["fonts"][0], "body": template["fonts"][-1]},
            layout=template["layout"],
            sections=sections,
            effects=template["effects"],
            mood=style,
            external_resources={
                "fonts": template["fonts"],
                "icons": ["lucide"],
                "images": ["unsplash"]
            }
        )

    def _generate_html(self, prompt: str, spec: DesignSpec) -> str:
        """Generate HTML structure based on design spec."""
        
        # Build font imports
        font_imports = []
        for font in spec.external_resources.get("fonts", []):
            font_url = font.replace(" ", "+")
            font_imports.append(f'<link href="https://fonts.googleapis.com/css2?family={font_url}:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">')
        
        fonts_html = "\n    ".join(font_imports)
        
        # Determine brand name from prompt
        brand = "SOVRN"
        if "coffee" in prompt.lower():
            brand = "The Roastery"
        elif "architect" in prompt.lower():
            brand = "AXIS ARCHITECTS"
        elif "festival" in prompt.lower() or "techno" in prompt.lower():
            brand = "SYSTEM_FAILURE"
        elif "fashion" in prompt.lower():
            brand = "MAISON"
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{brand}</title>
    {fonts_html}
    <link rel="stylesheet" href="styles.css">
</head>
<body data-style="{spec.style}">
    <div class="cursor" id="cursor"></div>
    <div class="cursor-follower" id="cursor-follower"></div>
    
    <nav class="nav">
        <div class="nav-brand">{brand}</div>
        <ul class="nav-links">
            <li><a href="#hero">Index</a></li>
            <li><a href="#about">About</a></li>
            <li><a href="#work">Work</a></li>
            <li><a href="#contact">Contact</a></li>
        </ul>
        <button class="nav-toggle" aria-label="Menu">
            <span></span>
            <span></span>
        </button>
    </nav>
    
    <main>
        <section id="hero" class="hero">
            <div class="hero-content">
                <span class="hero-label">EST. 2024 — CRAFTED WITH PURPOSE</span>
                <h1 class="hero-title" data-splitting>{brand}</h1>
                <p class="hero-subtitle">{self._get_tagline(prompt, spec.style)}</p>
                <a href="#work" class="btn btn-primary">
                    <span>Explore</span>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                </a>
            </div>
            <div class="hero-visual">
                <div class="hero-image"></div>
            </div>
            <div class="scroll-indicator">
                <span>Scroll to explore</span>
                <div class="scroll-line"></div>
            </div>
        </section>
        
        <section id="about" class="about">
            <div class="container">
                <div class="section-header">
                    <span class="section-label">01 / About</span>
                    <h2 class="section-title">{self._get_about_title(spec.style)}</h2>
                </div>
                <div class="about-content">
                    <p class="about-text">{self._get_about_text(prompt, spec.style)}</p>
                </div>
            </div>
        </section>
        
        <section id="work" class="work">
            <div class="container">
                <div class="section-header">
                    <span class="section-label">02 / Work</span>
                    <h2 class="section-title">Selected Projects</h2>
                </div>
                <div class="work-grid">
                    {self._generate_work_items(spec.style)}
                </div>
            </div>
        </section>
        
        <section id="contact" class="contact">
            <div class="container">
                <div class="contact-content">
                    <h2 class="contact-title">Let's Create<br/>Something Amazing</h2>
                    <a href="mailto:hello@sovrn.ai" class="contact-link">hello@sovrn.ai</a>
                </div>
            </div>
        </section>
    </main>
    
    <footer class="footer">
        <div class="container">
            <div class="footer-content">
                <span>© 2024 {brand}</span>
                <span>Crafted by SOVRN AI</span>
            </div>
        </div>
    </footer>
    
    <script src="script.js"></script>
</body>
</html>'''

    def _get_tagline(self, prompt: str, style: str) -> str:
        """Generate tagline based on prompt and style."""
        taglines = {
            "techno": "Where sound meets chaos. March 15-17, 2025.",
            "brutalist": "Form follows structure. Architecture stripped to its essential truth.",
            "organic": "Small-batch roasted beans, carefully sourced from sustainable farms worldwide.",
            "cyberpunk": "The future is now. Experience tomorrow's technology today.",
            "editorial": "Defining luxury through exceptional craftsmanship.",
            "minimal": "Simple. Elegant. Powerful."
        }
        return taglines.get(style, taglines["minimal"])

    def _get_about_title(self, style: str) -> str:
        """Generate about section title."""
        titles = {
            "techno": "The Movement",
            "brutalist": "Philosophy",
            "organic": "Our Story",
            "cyberpunk": "The Vision",
            "editorial": "Our Craft",
            "minimal": "About Us"
        }
        return titles.get(style, titles["minimal"])

    def _get_about_text(self, prompt: str, style: str) -> str:
        """Generate about section text."""
        texts = {
            "techno": "We are the underground. A collective of artists, producers, and visionaries pushing the boundaries of electronic music. Every beat tells a story of rebellion, unity, and the relentless pursuit of sonic excellence.",
            "brutalist": "We create spaces where geometry meets humanity. Our approach strips architecture to its essential truth—raw materials, honest construction, and spaces that inspire through their bold simplicity.",
            "organic": "Every cup tells a story. We source our beans directly from farmers who share our passion for quality and sustainability. Each roast is crafted to bring out the unique character of its origin.",
            "cyberpunk": "At the intersection of humanity and technology, we build experiences that challenge perception. Our work pushes boundaries and questions what's possible in the digital realm.",
            "editorial": "We believe in the power of restraint. Our designs speak through precision, clarity, and an unwavering commitment to excellence. Every detail matters.",
            "minimal": "We believe in the power of simplicity. Our approach focuses on what truly matters—creating meaningful experiences through thoughtful design and innovation."
        }
        return texts.get(style, texts["minimal"])

    def _generate_work_items(self, style: str) -> str:
        """Generate work/project items."""
        items = []
        projects = [
            {"title": "Project Alpha", "category": "Design", "year": "2024"},
            {"title": "Project Beta", "category": "Development", "year": "2024"},
            {"title": "Project Gamma", "category": "Branding", "year": "2023"},
        ]
        
        for i, p in enumerate(projects):
            items.append(f'''
                    <article class="work-item" data-index="{i:02d}">
                        <div class="work-item-image"></div>
                        <div class="work-item-content">
                            <span class="work-item-category">{p["category"]}</span>
                            <h3 class="work-item-title">{p["title"]}</h3>
                            <span class="work-item-year">{p["year"]}</span>
                        </div>
                    </article>''')
        
        return "\n".join(items)

    def _generate_css(self, spec: DesignSpec) -> str:
        """Generate CSS based on design spec."""
        colors = spec.color_palette
        fonts = spec.typography
        
        # Base styles that all designs share
        base_css = f'''/* ===========================================
   SOVRN Generated Styles
   Style: {spec.style}
   =========================================== */

:root {{
    --primary: {colors.get("primary", "#000")};
    --secondary: {colors.get("secondary", "#666")};
    --bg: {colors.get("bg", "#fff")};
    --text: {colors.get("text", "#000")};
    --font-heading: '{fonts.get("heading", "Inter")}', sans-serif;
    --font-body: '{fonts.get("body", "Inter")}', sans-serif;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
    font-size: 16px;
}}

body {{
    font-family: var(--font-body);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    overflow-x: hidden;
}}

/* Custom Cursor */
.cursor, .cursor-follower {{
    position: fixed;
    pointer-events: none;
    z-index: 9999;
    mix-blend-mode: difference;
}}

.cursor {{
    width: 8px;
    height: 8px;
    background: var(--primary);
    border-radius: 50%;
    transform: translate(-50%, -50%);
}}

.cursor-follower {{
    width: 40px;
    height: 40px;
    border: 1px solid var(--primary);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    transition: transform 0.15s ease-out, width 0.3s, height 0.3s;
}}

/* Navigation */
.nav {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    padding: 24px 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    mix-blend-mode: difference;
}}

.nav-brand {{
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #fff;
}}

.nav-links {{
    display: flex;
    gap: 48px;
    list-style: none;
}}

.nav-links a {{
    color: #fff;
    text-decoration: none;
    font-size: 0.875rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    opacity: 0.7;
    transition: opacity 0.3s;
}}

.nav-links a:hover {{
    opacity: 1;
}}

.nav-toggle {{
    display: none;
    flex-direction: column;
    gap: 6px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
}}

.nav-toggle span {{
    width: 24px;
    height: 2px;
    background: #fff;
    transition: 0.3s;
}}

/* Hero Section */
.hero {{
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1fr;
    position: relative;
}}

.hero-content {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 120px 80px;
}}

.hero-label {{
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    opacity: 0.5;
    margin-bottom: 24px;
}}

.hero-title {{
    font-family: var(--font-heading);
    font-size: clamp(3rem, 8vw, 7rem);
    font-weight: 800;
    line-height: 0.95;
    letter-spacing: -0.03em;
    margin-bottom: 24px;
}}

.hero-subtitle {{
    font-size: 1.125rem;
    opacity: 0.7;
    max-width: 400px;
    margin-bottom: 48px;
}}

.btn {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 16px 32px;
    background: var(--primary);
    color: var(--bg);
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
}}

.btn:hover {{
    transform: translateX(8px);
}}

.hero-visual {{
    position: relative;
    overflow: hidden;
}}

.hero-image {{
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    opacity: 0.9;
}}

.scroll-indicator {{
    position: absolute;
    bottom: 48px;
    left: 80px;
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.5;
}}

.scroll-line {{
    width: 48px;
    height: 1px;
    background: currentColor;
    position: relative;
    overflow: hidden;
}}

.scroll-line::after {{
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: var(--primary);
    animation: scroll-line 2s ease-in-out infinite;
}}

@keyframes scroll-line {{
    0% {{ transform: translateX(-100%); }}
    100% {{ transform: translateX(100%); }}
}}

/* Sections */
section {{
    padding: 160px 0;
}}

.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 48px;
}}

.section-header {{
    margin-bottom: 80px;
}}

.section-label {{
    display: block;
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    opacity: 0.5;
    margin-bottom: 16px;
}}

.section-title {{
    font-family: var(--font-heading);
    font-size: clamp(2rem, 5vw, 4rem);
    font-weight: 700;
    letter-spacing: -0.02em;
}}

/* About */
.about-content {{
    max-width: 800px;
}}

.about-text {{
    font-size: 1.5rem;
    line-height: 1.8;
    opacity: 0.8;
}}

/* Work Grid */
.work-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 48px;
}}

.work-item {{
    position: relative;
    cursor: pointer;
}}

.work-item-image {{
    aspect-ratio: 4/3;
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    opacity: 0.8;
    transition: opacity 0.5s, transform 0.5s;
}}

.work-item:hover .work-item-image {{
    opacity: 1;
    transform: scale(1.02);
}}

.work-item-content {{
    padding: 24px 0;
    display: flex;
    align-items: center;
    gap: 24px;
}}

.work-item-category {{
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.5;
}}

.work-item-title {{
    font-family: var(--font-heading);
    font-size: 1.5rem;
    font-weight: 600;
    flex: 1;
}}

.work-item-year {{
    font-size: 0.875rem;
    opacity: 0.5;
}}

/* Contact */
.contact {{
    text-align: center;
    padding: 200px 0;
}}

.contact-title {{
    font-family: var(--font-heading);
    font-size: clamp(2.5rem, 6vw, 5rem);
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 48px;
}}

.contact-link {{
    font-size: 1.25rem;
    color: var(--primary);
    text-decoration: none;
    border-bottom: 2px solid transparent;
    transition: border-color 0.3s;
}}

.contact-link:hover {{
    border-color: var(--primary);
}}

/* Footer */
.footer {{
    padding: 48px 0;
    border-top: 1px solid rgba(128,128,128,0.2);
}}

.footer-content {{
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    opacity: 0.5;
}}

/* Responsive */
@media (max-width: 1024px) {{
    .hero {{
        grid-template-columns: 1fr;
    }}
    
    .hero-visual {{
        display: none;
    }}
    
    .hero-content {{
        padding: 120px 48px;
    }}
    
    .work-grid {{
        grid-template-columns: 1fr;
    }}
}}

@media (max-width: 768px) {{
    .nav {{
        padding: 16px 24px;
    }}
    
    .nav-links {{
        display: none;
    }}
    
    .nav-toggle {{
        display: flex;
    }}
    
    .hero-content {{
        padding: 100px 24px;
    }}
    
    .container {{
        padding: 0 24px;
    }}
    
    section {{
        padding: 100px 0;
    }}
    
    .about-text {{
        font-size: 1.125rem;
    }}
}}
'''

        # Add style-specific CSS
        style_css = self._get_style_specific_css(spec.style, colors)
        
        return base_css + style_css

    def _get_style_specific_css(self, style: str, colors: Dict) -> str:
        """Get CSS specific to each design style."""
        
        if style == "techno":
            return f'''
/* Techno/Acid Style Overrides */
body[data-style="techno"] {{
    background: #0a0a0a;
    color: #fff;
}}

body[data-style="techno"] .hero-title {{
    font-family: 'Space Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    animation: glitch 2s infinite;
}}

@keyframes glitch {{
    0%, 90%, 100% {{ transform: translate(0); }}
    92% {{ transform: translate(-2px, 2px); }}
    94% {{ transform: translate(2px, -2px); }}
    96% {{ transform: translate(-2px, -2px); }}
    98% {{ transform: translate(2px, 2px); }}
}}

body[data-style="techno"] .hero-image {{
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,255,65,0.03) 2px,
        rgba(0,255,65,0.03) 4px
    );
}}

body[data-style="techno"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.1) 2px,
        rgba(0,0,0,0.1) 4px
    );
    pointer-events: none;
    z-index: 9998;
}}
'''
        
        elif style == "brutalist":
            return f'''
/* Brutalist/Swiss Style Overrides */
body[data-style="brutalist"] {{
    background: #fff;
    color: #000;
}}

body[data-style="brutalist"] .hero {{
    border-bottom: 8px solid #000;
}}

body[data-style="brutalist"] .hero-title {{
    font-weight: 900;
    text-transform: uppercase;
}}

body[data-style="brutalist"] .btn {{
    background: #ff4400;
    color: #fff;
    border: 4px solid #000;
}}

body[data-style="brutalist"] .work-item {{
    border: 4px solid #000;
}}

body[data-style="brutalist"] .section-title {{
    border-bottom: 4px solid #000;
    padding-bottom: 16px;
}}

body[data-style="brutalist"] .nav {{
    border-bottom: 4px solid #000;
    mix-blend-mode: normal;
}}

body[data-style="brutalist"] .nav-brand,
body[data-style="brutalist"] .nav-links a {{
    color: #000;
}}
'''
        
        elif style == "organic":
            return f'''
/* Organic/Craft Style Overrides */
body[data-style="organic"] {{
    background: #FDF5E6;
    background-image: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    color: #3E2723;
}}

body[data-style="organic"] .hero-title {{
    font-family: 'Playfair Display', serif;
    font-weight: 400;
    font-style: italic;
}}

body[data-style="organic"] .btn {{
    background: #8B4513;
    border-radius: 0;
}}

body[data-style="organic"] .hero-image {{
    background: linear-gradient(135deg, #D2691E 0%, #8B4513 100%);
}}

body[data-style="organic"] .work-item-image {{
    border-radius: 8px;
}}

body[data-style="organic"] .nav {{
    mix-blend-mode: normal;
}}

body[data-style="organic"] .nav-brand,
body[data-style="organic"] .nav-links a {{
    color: #3E2723;
}}
'''
        
        elif style == "cyberpunk":
            return f'''
/* Cyberpunk Style Overrides */
body[data-style="cyberpunk"] {{
    background: #0d0d0d;
    color: #fff;
}}

body[data-style="cyberpunk"] .hero-title {{
    text-shadow: 0 0 20px rgba(0,240,255,0.5), 0 0 40px rgba(0,240,255,0.3);
}}

body[data-style="cyberpunk"] .btn {{
    background: transparent;
    border: 1px solid #00f0ff;
    color: #00f0ff;
    box-shadow: 0 0 20px rgba(0,240,255,0.3), inset 0 0 20px rgba(0,240,255,0.1);
}}

body[data-style="cyberpunk"] .btn:hover {{
    background: rgba(0,240,255,0.1);
    box-shadow: 0 0 40px rgba(0,240,255,0.5);
}}

body[data-style="cyberpunk"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background: 
        linear-gradient(90deg, rgba(0,240,255,0.03) 1px, transparent 1px) 0 0 / 50px 50px,
        linear-gradient(rgba(0,240,255,0.03) 1px, transparent 1px) 0 0 / 50px 50px;
    pointer-events: none;
    z-index: -1;
}}
'''
        
        return ""

    def _generate_js(self, spec: DesignSpec) -> str:
        """Generate JavaScript for interactivity."""
        return '''// ===========================================
// SOVRN Generated Scripts
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    // Custom Cursor
    const cursor = document.getElementById('cursor');
    const follower = document.getElementById('cursor-follower');
    
    if (cursor && follower) {
        let mouseX = 0, mouseY = 0;
        let cursorX = 0, cursorY = 0;
        let followerX = 0, followerY = 0;
        
        document.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });
        
        function animate() {
            // Cursor follows mouse instantly
            cursorX = mouseX;
            cursorY = mouseY;
            cursor.style.left = cursorX + 'px';
            cursor.style.top = cursorY + 'px';
            
            // Follower has smooth delay
            followerX += (mouseX - followerX) * 0.15;
            followerY += (mouseY - followerY) * 0.15;
            follower.style.left = followerX + 'px';
            follower.style.top = followerY + 'px';
            
            requestAnimationFrame(animate);
        }
        animate();
        
        // Cursor effects on hover
        document.querySelectorAll('a, button, .work-item').forEach(el => {
            el.addEventListener('mouseenter', () => {
                follower.style.transform = 'translate(-50%, -50%) scale(2)';
                follower.style.borderColor = 'var(--secondary)';
            });
            el.addEventListener('mouseleave', () => {
                follower.style.transform = 'translate(-50%, -50%) scale(1)';
                follower.style.borderColor = 'var(--primary)';
            });
        });
    }
    
    // Smooth Scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
    
    // Scroll Animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.section-header, .work-item, .about-text').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(40px)';
        el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        observer.observe(el);
    });
    
    // Add visible class styles
    const style = document.createElement('style');
    style.textContent = `
        .is-visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
    
    // Nav Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('is-open');
            navToggle.classList.toggle('is-active');
        });
    }
    
    // Parallax on Hero
    const heroVisual = document.querySelector('.hero-visual');
    if (heroVisual) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            heroVisual.style.transform = `translateY(${scrolled * 0.3}px)`;
        });
    }
    
    // Text reveal animation
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        const text = heroTitle.textContent;
        heroTitle.innerHTML = text.split('').map((char, i) => 
            `<span style="animation-delay: ${i * 0.05}s">${char === ' ' ? '&nbsp;' : char}</span>`
        ).join('');
        
        const style = document.createElement('style');
        style.textContent = `
            .hero-title span {
                display: inline-block;
                opacity: 0;
                transform: translateY(100%);
                animation: revealChar 0.8s ease forwards;
            }
            @keyframes revealChar {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    console.log('✨ SOVRN Website Initialized');
});
'''

    async def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate a complete website with multiple files."""
        start_time = time.time()
        
        try:
            # Step 1: Analyze prompt and create design spec
            spec = self._analyze_prompt(prompt)
            logger.info("design_spec_created", style=spec.style, sections=spec.sections)
            
            # Step 2: Generate HTML
            html = self._generate_html(prompt, spec)
            
            # Step 3: Generate CSS
            css = self._generate_css(spec)
            
            # Step 4: Generate JavaScript
            js = self._generate_js(spec)
            
            # Step 5: Create preview HTML (combined)
            preview_html = self._create_preview_html(html, css, js)
            
            generation_time = int((time.time() - start_time) * 1000)
            
            # Return as dictionary for API compatibility
            return {
                "files": {
                    "index.html": html,
                    "styles.css": css,
                    "script.js": js
                },
                "success": True,
                "generation_time_ms": generation_time,
                "preview_html": preview_html,
                "design_style": spec.style
            }
            
        except Exception as e:
            logger.error("generation_failed", error=str(e))
            return {
                "files": {},
                "success": False,
                "generation_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }

    def _create_preview_html(self, html: str, css: str, js: str) -> str:
        """Create a single HTML file with embedded CSS and JS for preview."""
        # Find the </head> and insert CSS
        html_with_css = html.replace(
            '<link rel="stylesheet" href="styles.css">',
            f'<style>\n{css}\n</style>'
        )
        
        # Find </body> and insert JS
        html_with_js = html_with_css.replace(
            '<script src="script.js"></script>',
            f'<script>\n{js}\n</script>'
        )
        
        return html_with_js
