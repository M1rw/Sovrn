'use client';

import { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Code, 
  Eye, 
  Download, 
  Copy, 
  Check, 
  ExternalLink,
  Loader2,
  Zap,
  Save,
  FolderOpen,
  Trash2
} from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Project {
  id: string;
  name: string;
  html: string;
  prompt: string;
  created_at: string;
}

type ViewMode = 'chat' | 'preview' | 'code';
type WebsiteStyle = 'modern' | 'minimal' | 'bold' | 'elegant' | 'playful' | 'corporate' | 'dark' | 'light';

// =============================================================================
// Quick Prompts
// =============================================================================

const QUICK_PROMPTS = [
  { icon: '🏪', label: 'Landing Page', prompt: 'Create a modern landing page for a SaaS product called "FlowSync" - project management tool' },
  { icon: '☕', label: 'Coffee Shop', prompt: 'Design a cozy coffee shop website with menu, about section, and contact form' },
  { icon: '💼', label: 'Portfolio', prompt: 'Build a creative portfolio website for a UI/UX designer with project gallery' },
  { icon: '🛒', label: 'E-commerce', prompt: 'Create an e-commerce product page for premium headphones with features and reviews' },
  { icon: '🍕', label: 'Restaurant', prompt: 'Design a restaurant website with menu, reservation form, and location map' },
  { icon: '🏋️', label: 'Fitness', prompt: 'Build a fitness gym landing page with membership plans and class schedule' },
  { icon: '📱', label: 'App Launch', prompt: 'Create a mobile app launch page with features, screenshots, and download buttons' },
  { icon: '🎵', label: 'Music', prompt: 'Design a music artist portfolio with albums, tour dates, and media player' },
];

const STYLE_OPTIONS: { value: WebsiteStyle; label: string; icon: string }[] = [
  { value: 'modern', label: 'Modern', icon: '✨' },
  { value: 'minimal', label: 'Minimal', icon: '◻️' },
  { value: 'bold', label: 'Bold', icon: '💪' },
  { value: 'elegant', label: 'Elegant', icon: '👑' },
  { value: 'playful', label: 'Playful', icon: '🎨' },
  { value: 'corporate', label: 'Corporate', icon: '🏢' },
  { value: 'dark', label: 'Dark', icon: '🌙' },
  { value: 'light', label: 'Light', icon: '☀️' },
];

// =============================================================================
// Main Component
// =============================================================================

export default function PlaygroundPage() {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedHtml, setGeneratedHtml] = useState<string>('');
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [copied, setCopied] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<WebsiteStyle>('modern');
  const [aiStatus, setAiStatus] = useState<{ loaded: boolean; engine: string } | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showProjects, setShowProjects] = useState(false);
  const [generationTime, setGenerationTime] = useState<number | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ==========================================================================
  // Effects
  // ==========================================================================

  useEffect(() => {
    checkAIStatus();
    loadProjects();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  // ==========================================================================
  // API Functions
  // ==========================================================================

  const checkAIStatus = async () => {
    try {
      const res = await fetch('/api/v1/ai/status');
      if (res.ok) {
        const data = await res.json();
        setAiStatus({ 
          loaded: data.initialized, 
          engine: data.engine || 'SOVRN MML' 
        });
      }
    } catch {
      setAiStatus({ loaded: false, engine: 'Not connected' });
    }
  };

  const loadProjects = async () => {
    try {
      const res = await fetch('/api/v1/projects');
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch {
      console.error('Failed to load projects');
    }
  };

  const generateWebsite = async (prompt: string) => {
    setIsGenerating(true);
    setGenerationTime(null);
    
    const userMessage: Message = { role: 'user', content: prompt };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const res = await fetch('/api/v1/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt,
          style: selectedStyle
        })
      });
      
      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }
      
      const data = await res.json();
      
      if (data.success && data.html) {
        setGeneratedHtml(data.html);
        setGenerationTime(data.generation_time_ms);
        setViewMode('preview');
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: `✅ Website generated in ${(data.generation_time_ms / 1000).toFixed(1)}s! Check the Preview tab.`
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        throw new Error(data.error || 'Generation failed');
      }
      
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ Error: ${error.message}. Make sure the MML Engine is running.`
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsGenerating(false);
    }
  };

  const saveProject = async () => {
    if (!generatedHtml) return;
    
    const projectName = prompt('Enter project name:', 'My Website');
    if (!projectName) return;
    
    try {
      const res = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName,
          html: generatedHtml,
          prompt: messages[0]?.content || ''
        })
      });
      
      if (res.ok) {
        await loadProjects();
        alert('Project saved!');
      }
    } catch {
      alert('Failed to save project');
    }
  };

  const loadProject = (project: Project) => {
    setGeneratedHtml(project.html);
    setMessages([{ role: 'user', content: project.prompt }]);
    setViewMode('preview');
    setShowProjects(false);
  };

  const deleteProject = async (id: string) => {
    if (!confirm('Delete this project?')) return;
    
    try {
      await fetch(`/api/v1/projects/${id}`, { method: 'DELETE' });
      await loadProjects();
    } catch {
      alert('Failed to delete project');
    }
  };

  // ==========================================================================
  // Handlers
  // ==========================================================================

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;
    
    generateWebsite(input.trim());
    setInput('');
  };

  const handleQuickPrompt = (prompt: string) => {
    generateWebsite(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const copyCode = async () => {
    await navigator.clipboard.writeText(generatedHtml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadHtml = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'website.html';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openInNewTab = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">SOVRN MML</h1>
            <p className="text-xs text-gray-400">AI Website Generator</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {/* AI Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
            aiStatus?.loaded ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${aiStatus?.loaded ? 'bg-green-400' : 'bg-yellow-400'} animate-pulse`} />
            {aiStatus?.engine || 'Checking...'}
          </div>
          
          {/* Projects button */}
          <button
            onClick={() => setShowProjects(!showProjects)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
          >
            <FolderOpen className="w-4 h-4" />
            Projects ({projects.length})
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat Section */}
        <div className={`flex flex-col ${viewMode === 'chat' ? 'flex-1' : 'w-96'} border-r border-gray-800`}>
          {/* Style Selector */}
          <div className="p-4 border-b border-gray-800">
            <label className="text-sm text-gray-400 mb-2 block">Website Style</label>
            <div className="flex flex-wrap gap-2">
              {STYLE_OPTIONS.map(style => (
                <button
                  key={style.value}
                  onClick={() => setSelectedStyle(style.value)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition ${
                    selectedStyle === style.value
                      ? 'bg-violet-500 text-white'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <span>{style.icon}</span>
                  {style.label}
                </button>
              ))}
            </div>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center mb-6">
                  <Sparkles className="w-10 h-10 text-violet-400" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Describe your website</h2>
                <p className="text-gray-400 mb-8 max-w-md">
                  Tell me what kind of website you want to create and I'll generate it using the SOVRN MML Engine.
                </p>
                
                {/* Quick prompts */}
                <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
                  {QUICK_PROMPTS.map((item, i) => (
                    <button
                      key={i}
                      onClick={() => handleQuickPrompt(item.prompt)}
                      disabled={isGenerating}
                      className="flex items-center gap-2 p-3 rounded-xl bg-gray-800/50 hover:bg-gray-800 border border-gray-700 transition text-left text-sm disabled:opacity-50"
                    >
                      <span className="text-xl">{item.icon}</span>
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-violet-500 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            
            {isGenerating && (
              <div className="flex justify-start">
                <div className="bg-gray-800 px-4 py-3 rounded-2xl flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
                  <span>Generating website...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-gray-800">
            <div className="flex gap-2">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your website..."
                rows={1}
                className="flex-1 px-4 py-3 bg-gray-800 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 max-h-32"
                disabled={isGenerating}
              />
              <button
                type="submit"
                disabled={!input.trim() || isGenerating}
                className="px-4 py-3 bg-violet-500 hover:bg-violet-600 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {isGenerating ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Preview Section */}
        {viewMode !== 'chat' && (
          <div className="flex-1 flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900/50">
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('preview')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                    viewMode === 'preview' ? 'bg-violet-500' : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <Eye className="w-4 h-4" />
                  Preview
                </button>
                <button
                  onClick={() => setViewMode('code')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                    viewMode === 'code' ? 'bg-violet-500' : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <Code className="w-4 h-4" />
                  Code
                </button>
              </div>
              
              <div className="flex items-center gap-2">
                {generationTime && (
                  <span className="text-sm text-gray-400 mr-2">
                    Generated in {(generationTime / 1000).toFixed(1)}s
                  </span>
                )}
                <button
                  onClick={saveProject}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  title="Save Project"
                >
                  <Save className="w-4 h-4" />
                </button>
                <button
                  onClick={copyCode}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  title="Copy Code"
                >
                  {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  onClick={downloadHtml}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  title="Download"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={openInNewTab}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  title="Open in New Tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {viewMode === 'preview' ? (
                <iframe
                  srcDoc={generatedHtml}
                  className="w-full h-full bg-white"
                  sandbox="allow-scripts"
                  title="Preview"
                />
              ) : (
                <div className="h-full overflow-auto bg-gray-900 p-4">
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                    {generatedHtml}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Projects Sidebar */}
        {showProjects && (
          <div className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col">
            <div className="p-4 border-b border-gray-800">
              <h3 className="font-semibold">Saved Projects</h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {projects.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-8">No saved projects yet</p>
              ) : (
                projects.map(project => (
                  <div
                    key={project.id}
                    className="p-3 rounded-lg bg-gray-800 hover:bg-gray-750 group"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <button
                        onClick={() => loadProject(project)}
                        className="font-medium text-sm hover:text-violet-400 transition"
                      >
                        {project.name}
                      </button>
                      <button
                        onClick={() => deleteProject(project.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 truncate">{project.prompt}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
