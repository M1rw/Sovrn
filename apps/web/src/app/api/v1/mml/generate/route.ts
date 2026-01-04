import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, style } = body;

    if (!prompt || typeof prompt !== 'string') {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }

    // Try backend with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

    try {
      const response = await fetch(`${API_BASE}/api/v1/mml/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, style: style || 'modern' }),
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        if (data.html) {
          return NextResponse.json(data);
        }
      }
    } catch (fetchError) {
      clearTimeout(timeoutId);
      console.log('Backend unavailable, using fallback');
    }

    // Fallback: generate HTML locally
    const html = generateFallbackHtml(prompt);
    return NextResponse.json({ html, success: true, fallback: true });

  } catch (error) {
    console.error('MML generation error:', error);
    const html = generateFallbackHtml('Website');
    return NextResponse.json({ html, success: true, fallback: true });
  }
}

function generateFallbackHtml(prompt: string): string {
  const words = prompt.split(' ').filter(w => w.length > 0);
  const title = words.slice(0, 5).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || 'My Website';
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
      --bg: #0a0a0a;
      --fg: #fafafa;
      --muted: #71717a;
      --card: #18181b;
      --border: rgba(255,255,255,0.1);
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      min-height: 100vh;
      line-height: 1.6;
    }
    nav {
      position: sticky;
      top: 0;
      background: rgba(10, 10, 10, 0.8);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
    }
    .logo { font-weight: 600; font-size: 1.125rem; }
    .nav-links { display: flex; gap: 2rem; }
    .nav-links a {
      color: var(--muted);
      text-decoration: none;
      font-size: 0.875rem;
      transition: color 0.2s;
    }
    .nav-links a:hover { color: var(--fg); }
    .hero {
      max-width: 720px;
      margin: 0 auto;
      padding: 6rem 2rem 4rem;
      text-align: center;
    }
    .hero h1 {
      font-size: clamp(2.5rem, 6vw, 4rem);
      font-weight: 700;
      line-height: 1.1;
      margin-bottom: 1.5rem;
      background: linear-gradient(135deg, #fff 0%, #a1a1aa 100%);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .hero p {
      font-size: 1.125rem;
      color: var(--muted);
      margin-bottom: 2.5rem;
      max-width: 540px;
      margin-left: auto;
      margin-right: auto;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--fg);
      color: var(--bg);
      border: none;
      padding: 0.75rem 1.75rem;
      border-radius: 0.75rem;
      font-size: 0.9375rem;
      font-weight: 500;
      cursor: pointer;
      transition: transform 0.2s, opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .features {
      max-width: 1100px;
      margin: 0 auto;
      padding: 4rem 2rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.75rem;
      transition: transform 0.2s, border-color 0.2s;
    }
    .card:hover {
      transform: translateY(-2px);
      border-color: rgba(255,255,255,0.2);
    }
    .card-icon {
      width: 2.75rem;
      height: 2.75rem;
      background: rgba(59, 130, 246, 0.15);
      border-radius: 0.625rem;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1rem;
      font-size: 1.25rem;
    }
    .card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .card p { color: var(--muted); font-size: 0.875rem; }
    footer {
      border-top: 1px solid var(--border);
      padding: 1.5rem 2rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.8125rem;
    }
    @media (max-width: 640px) {
      .nav-links { display: none; }
      .hero { padding: 4rem 1.5rem 3rem; }
      .features { padding: 2rem 1.5rem; }
    }
  </style>
</head>
<body>
  <nav>
    <div class="logo">${title}</div>
    <div class="nav-links">
      <a href="#">Home</a>
      <a href="#">Features</a>
      <a href="#">About</a>
      <a href="#">Contact</a>
    </div>
  </nav>
  
  <section class="hero">
    <h1>${title}</h1>
    <p>Welcome to our platform. We're building something amazing that will transform the way you work and create.</p>
    <button class="btn">Get Started →</button>
  </section>
  
  <section class="features">
    <div class="card">
      <div class="card-icon">⚡</div>
      <h3>Lightning Fast</h3>
      <p>Optimized for performance with modern architecture and efficient code.</p>
    </div>
    <div class="card">
      <div class="card-icon">🛡️</div>
      <h3>Secure by Design</h3>
      <p>Enterprise-grade security with encryption and best practices.</p>
    </div>
    <div class="card">
      <div class="card-icon">✨</div>
      <h3>Beautiful Interface</h3>
      <p>Carefully crafted design with attention to every detail.</p>
    </div>
  </section>
  
  <footer>
    <p>© ${new Date().getFullYear()} ${title}. All rights reserved.</p>
  </footer>
</body>
</html>`;
}

