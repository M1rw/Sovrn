# =============================================================================
# SOVRN MML Engine - Custom Website Generation Model
# =============================================================================
"""
MML (Markup Language Model) - A specialized AI engine for generating
production-ready websites using Phi-3 as the base model.

Features:
- Optimized prompts for HTML/CSS/JS generation
- Multi-pass generation for quality
- Component-based architecture
- Style consistency enforcement
"""

import asyncio
import time
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class WebsiteStyle(Enum):
    """Predefined website styles."""
    MODERN = "modern"
    MINIMAL = "minimal"
    BOLD = "bold"
    ELEGANT = "elegant"
    PLAYFUL = "playful"
    CORPORATE = "corporate"
    DARK = "dark"
    LIGHT = "light"


class ComponentType(Enum):
    """Website component types."""
    HERO = "hero"
    NAVBAR = "navbar"
    FEATURES = "features"
    PRICING = "pricing"
    TESTIMONIALS = "testimonials"
    CONTACT = "contact"
    FOOTER = "footer"
    GALLERY = "gallery"
    CTA = "cta"
    ABOUT = "about"


@dataclass
class MMLConfig:
    """MML Engine configuration."""
    model_path: str = "/workspaces/Sovrn/models/phi-3-mini-4k-instruct-q4.gguf"
    max_tokens: int = 8192
    temperature: float = 0.7
    top_p: float = 0.9
    threads: int = 4
    context_length: int = 8192


@dataclass
class GenerationResult:
    """Result of website generation."""
    html: str
    success: bool
    generation_time_ms: int
    tokens_used: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MMLEngine:
    """
    SOVRN MML Engine - Specialized for website generation.
    Uses Phi-3 with optimized prompts for HTML/CSS/JS output.
    """
    
    def __init__(self, config: Optional[MMLConfig] = None):
        self.config = config or MMLConfig()
        self.llm = None
        self.is_loaded = False
        self._load_lock = asyncio.Lock()
        
    async def load(self) -> bool:
        """Load the Phi-3 model."""
        async with self._load_lock:
            if self.is_loaded:
                return True
                
            try:
                from llama_cpp import Llama
                
                logger.info("mml_loading_model", path=self.config.model_path)
                
                self.llm = Llama(
                    model_path=self.config.model_path,
                    n_ctx=self.config.context_length,
                    n_threads=self.config.threads,
                    n_gpu_layers=0,  # CPU only
                    verbose=False,
                    chat_format="chatml"
                )
                
                self.is_loaded = True
                logger.info("mml_model_loaded")
                return True
                
            except Exception as e:
                logger.error("mml_load_failed", error=str(e))
                return False
    
    def _build_system_prompt(self, style: WebsiteStyle = WebsiteStyle.MODERN) -> str:
        """Build the system prompt for website generation."""
        
        style_guides = {
            WebsiteStyle.MODERN: "Clean lines, gradient backgrounds, rounded corners, subtle shadows, modern sans-serif fonts",
            WebsiteStyle.MINIMAL: "Lots of whitespace, simple colors, thin borders, minimal decorations, elegant typography",
            WebsiteStyle.BOLD: "Strong contrasts, large typography, vibrant colors, impactful visuals",
            WebsiteStyle.ELEGANT: "Refined aesthetics, serif fonts, muted colors, sophisticated layouts",
            WebsiteStyle.PLAYFUL: "Bright colors, rounded shapes, fun animations, friendly fonts",
            WebsiteStyle.CORPORATE: "Professional, structured, trustworthy blues and grays, formal typography",
            WebsiteStyle.DARK: "Dark backgrounds, light text, neon accents, modern feel",
            WebsiteStyle.LIGHT: "White/light backgrounds, dark text, clean and airy feel",
        }
        
        return f"""You are an expert web developer. Generate a COMPLETE, working HTML website.

STYLE: {style_guides.get(style, style_guides[WebsiteStyle.MODERN])}

You MUST output a complete HTML file with:
1. <!DOCTYPE html> at the start
2. Full <head> with meta tags, title, and embedded CSS in <style>
3. Full <body> with all sections: header/nav, hero, content sections, footer
4. Embedded JavaScript in <script> before </body> for interactivity

CSS Requirements:
- Use CSS variables for colors
- Include hover effects and transitions
- Make it responsive with media queries
- Use flexbox/grid for layouts

JavaScript Requirements:
- Smooth scroll navigation
- Mobile menu toggle
- Any relevant animations

Output ONLY the HTML code. No explanations."""

    def _build_generation_prompt(self, user_request: str, style: WebsiteStyle) -> str:
        """Build the full prompt for generation."""
        return f"""Build a complete website for: {user_request}

Include these sections:
- Navigation bar with logo and links
- Hero section with headline and CTA button
- Features/services section with cards
- About section
- Contact section or form
- Footer with links

Start with <!DOCTYPE html> and include complete CSS and JavaScript."""

    def _extract_html(self, response: str) -> str:
        """Extract HTML from the response, handling various formats."""
        # Remove markdown code blocks if present
        response = re.sub(r'```html\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Try to find HTML content
        html_match = re.search(r'(<!DOCTYPE html.*</html>)', response, re.DOTALL | re.IGNORECASE)
        if html_match:
            return html_match.group(1)
        
        # If no full HTML found, check if it starts with doctype
        if response.strip().lower().startswith('<!doctype'):
            return response.strip()
        
        # If response looks like HTML content, wrap it
        if '<' in response and '>' in response:
            return response.strip()
            
        return response.strip()

    async def generate(
        self,
        prompt: str,
        style: WebsiteStyle = WebsiteStyle.MODERN,
        max_tokens: Optional[int] = None
    ) -> GenerationResult:
        """Generate a website from a prompt."""
        
        if not self.is_loaded:
            await self.load()
            
        if not self.is_loaded or not self.llm:
            return GenerationResult(
                html="",
                success=False,
                generation_time_ms=0,
                error="Model not loaded"
            )
        
        start_time = time.time()
        
        try:
            system_prompt = self._build_system_prompt(style)
            user_prompt = self._build_generation_prompt(prompt, style)
            
            # Generate with Phi-3
            response = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                stop=["---", "Note:", "I hope", "Let me know", "Feel free"]
            )
            
            content = response["choices"][0]["message"]["content"]
            html = self._extract_html(content)
            
            generation_time = int((time.time() - start_time) * 1000)
            tokens_used = response.get("usage", {}).get("total_tokens", 0)
            
            # Validate HTML
            is_valid = html.strip().lower().startswith('<!doctype') or html.strip().startswith('<html')
            
            if not is_valid:
                # Try to wrap partial HTML
                html = self._wrap_partial_html(html, prompt)
            
            return GenerationResult(
                html=html,
                success=True,
                generation_time_ms=generation_time,
                tokens_used=tokens_used,
                metadata={
                    "style": style.value,
                    "prompt_length": len(prompt)
                }
            )
            
        except Exception as e:
            logger.error("mml_generation_failed", error=str(e))
            return GenerationResult(
                html="",
                success=False,
                generation_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _wrap_partial_html(self, content: str, title: str = "SOVRN Website") -> str:
        """Wrap partial HTML content in a full document or generate a fallback."""
        # If content is very short, generate a proper fallback website
        if len(content.strip()) < 500:
            return self._generate_fallback_website(title)
            
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #0a0a0a;
            --surface: #141414;
            --text: #ffffff;
            --text-muted: rgba(255,255,255,0.6);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: system-ui, -apple-system, sans-serif; 
            line-height: 1.6;
            background: var(--bg);
            color: var(--text);
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    def _generate_fallback_website(self, description: str) -> str:
        """Generate a proper fallback website when generation fails."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{description}</title>
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #0a0a0a;
            --surface: #141414;
            --surface-hover: #1a1a1a;
            --border: rgba(255,255,255,0.08);
            --text: #ffffff;
            --text-muted: rgba(255,255,255,0.6);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif; 
            line-height: 1.6;
            background: var(--bg);
            color: var(--text);
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
        
        /* Navigation */
        nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(10,10,10,0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            z-index: 100;
        }}
        nav .container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 72px;
        }}
        .logo {{
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .nav-links {{ display: flex; gap: 32px; list-style: none; }}
        .nav-links a {{
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.95rem;
            transition: color 0.2s;
        }}
        .nav-links a:hover {{ color: var(--text); }}
        
        /* Hero */
        .hero {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            padding: 120px 0 80px;
            background: radial-gradient(ellipse at top, rgba(99,102,241,0.15), transparent 50%);
        }}
        .hero-content {{ max-width: 800px; }}
        .hero h1 {{
            font-size: clamp(2.5rem, 6vw, 4rem);
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 24px;
        }}
        .hero p {{
            font-size: 1.25rem;
            color: var(--text-muted);
            margin-bottom: 40px;
            max-width: 600px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 16px 32px;
            background: var(--primary);
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .btn:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
        }}
        
        /* Sections */
        section {{ padding: 100px 0; }}
        .section-title {{
            font-size: 2.5rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 60px;
        }}
        
        /* Features */
        .features-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }}
        .feature-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            transition: all 0.2s;
        }}
        .feature-card:hover {{
            background: var(--surface-hover);
            transform: translateY(-4px);
        }}
        .feature-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary), #a855f7);
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .feature-card h3 {{
            font-size: 1.25rem;
            margin-bottom: 12px;
        }}
        .feature-card p {{
            color: var(--text-muted);
        }}
        
        /* Footer */
        footer {{
            border-top: 1px solid var(--border);
            padding: 48px 0;
            text-align: center;
            color: var(--text-muted);
        }}
        
        @media (max-width: 768px) {{
            .nav-links {{ display: none; }}
            .hero h1 {{ font-size: 2rem; }}
        }}
    </style>
</head>
<body>
    <nav>
        <div class="container">
            <div class="logo">SOVRN</div>
            <ul class="nav-links">
                <li><a href="#features">Features</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </div>
    </nav>
    
    <section class="hero">
        <div class="container">
            <div class="hero-content">
                <h1>{description}</h1>
                <p>A beautifully crafted website generated by SOVRN AI. Modern design meets exceptional user experience.</p>
                <a href="#features" class="btn">Explore Features →</a>
            </div>
        </div>
    </section>
    
    <section id="features">
        <div class="container">
            <h2 class="section-title">Features</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon"></div>
                    <h3>Modern Design</h3>
                    <p>Clean, contemporary aesthetics that make a lasting impression on your visitors.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"></div>
                    <h3>Fully Responsive</h3>
                    <p>Looks perfect on every device, from mobile phones to large desktop screens.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"></div>
                    <h3>Fast & Optimized</h3>
                    <p>Lightning-fast load times with optimized code and no external dependencies.</p>
                </div>
            </div>
        </div>
    </section>
    
    <footer>
        <div class="container">
            <p>&copy; 2024 Generated by SOVRN AI</p>
        </div>
    </footer>
    
    <script>
        // Smooth scroll
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function(e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) target.scrollIntoView({{ behavior: 'smooth' }});
            }});
        }});
    </script>
</body>
</html>'''

    async def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> GenerationResult:
        """General chat completion."""
        
        if not self.is_loaded:
            await self.load()
            
        if not self.is_loaded or not self.llm:
            return GenerationResult(
                html="",
                success=False,
                generation_time_ms=0,
                error="Model not loaded"
            )
        
        start_time = time.time()
        
        try:
            messages = [
                {"role": "system", "content": "You are SOVRN, a helpful AI assistant. Be concise and accurate."}
            ]
            
            if history:
                messages.extend(history)
                
            messages.append({"role": "user", "content": message})
            
            response = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            
            content = response["choices"][0]["message"]["content"]
            generation_time = int((time.time() - start_time) * 1000)
            
            return GenerationResult(
                html=content,  # Using html field for response
                success=True,
                generation_time_ms=generation_time,
                tokens_used=response.get("usage", {}).get("total_tokens", 0)
            )
            
        except Exception as e:
            return GenerationResult(
                html="",
                success=False,
                generation_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )


# Global engine instance
_mml_engine: Optional[MMLEngine] = None


async def get_mml_engine() -> MMLEngine:
    """Get or create the global MML engine."""
    global _mml_engine
    
    if _mml_engine is None:
        _mml_engine = MMLEngine()
        await _mml_engine.load()
    
    return _mml_engine
