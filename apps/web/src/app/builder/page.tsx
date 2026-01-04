'use client';

import { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Code2, 
  Eye, 
  Download, 
  Copy, 
  Check, 
  Loader2,
  ThumbsUp,
  ThumbsDown,
  RotateCw,
  MoreHorizontal,
  Sparkles,
  Moon,
  Sun,
  Maximize2,
  RotateCcw,
  PanelRightClose,
  PanelRight,
  Plus,
  Search,
  Globe,
  FileCode,
  Palette,
  Zap,
  MessageSquare,
  Settings,
  Menu,
  X
} from 'lucide-react';

type ViewMode = 'preview' | 'code';

interface GeneratedFile {
  name: string;
  content: string;
  type: string;
  size: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  isNew?: boolean;
  thinkingDuration?: number;
  isTask?: boolean;
  taskStatus?: 'running' | 'completed';
  generatedFiles?: { name: string; size: string; type: string }[];
}

interface TaskStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed';
  duration?: number;
  detail?: string;
}

interface ChatHistory {
  id: string;
  title: string;
  preview: string;
  timestamp: Date;
  hasWebsite?: boolean;
}

// Animations
const styles = `
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.typing-cursor {
  animation: cursor-blink 0.8s infinite;
}
@keyframes thinking-wave {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(-8px); opacity: 1; }
}
.thinking-dot {
  animation: thinking-wave 1.4s ease-in-out infinite;
}
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 0.5s ease-out forwards;
}
@keyframes slide-in-right {
  from { opacity: 0; transform: translateX(60px); filter: blur(10px); }
  to { opacity: 1; transform: translateX(0); filter: blur(0); }
}
.animate-slide-in-right {
  animation: slide-in-right 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.animate-delay-100 { animation-delay: 100ms; opacity: 0; }
.animate-delay-200 { animation-delay: 200ms; opacity: 0; }
.animate-delay-300 { animation-delay: 300ms; opacity: 0; }
.animate-delay-400 { animation-delay: 400ms; opacity: 0; }
@keyframes scale-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
.animate-scale-in {
  animation: scale-in 0.3s ease-out forwards;
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.shimmer {
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.08) 50%, transparent 100%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}
@keyframes task-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.task-running {
  animation: task-pulse 1.5s ease-in-out infinite;
}
`;

export default function BuilderPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [generatedHtml, setGeneratedHtml] = useState('');
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('index.html');
  const [viewMode, setViewMode] = useState<ViewMode>('preview');
  const [copied, setCopied] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [isFocused, setIsFocused] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [greeting, setGreeting] = useState('Hello');
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [chatHistory] = useState<ChatHistory[]>([
    { id: '1', title: 'Coffee Shop Website', preview: 'Modern coffee shop with menu...', timestamp: new Date(Date.now() - 86400000), hasWebsite: true },
    { id: '2', title: 'Portfolio Design', preview: 'Minimal portfolio with projects...', timestamp: new Date(Date.now() - 172800000), hasWebsite: true },
    { id: '3', title: 'SaaS Landing Page', preview: 'Dark theme landing page...', timestamp: new Date(Date.now() - 259200000), hasWebsite: true },
  ]);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Get time-based greeting - only on client
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const quickActions = [
    { icon: Globe, label: 'Website', description: 'Build a website' },
    { icon: FileCode, label: 'Landing Page', description: 'Create a landing page' },
    { icon: Palette, label: 'Portfolio', description: 'Design a portfolio' },
    { icon: Zap, label: 'SaaS', description: 'SaaS product page' },
  ];

  useEffect(() => {
    setMounted(true);
    setGreeting(getGreeting());
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const buildConversationContext = () => {
    return messages.map(m => ({
      role: m.role,
      content: m.content
    }));
  };

  const getAIResponse = async (userMessage: string): Promise<string> => {
    const conversationHistory = buildConversationContext();
    conversationHistory.push({ role: 'user', content: userMessage });
    
    try {
      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            {
              role: 'system',
              content: `You are SOVRN, a friendly and intelligent AI assistant that helps users build websites. You can also have normal conversations.

Your capabilities:
- Chat naturally about any topic
- Help users plan and design websites
- When a user wants to generate a website, help them clarify their requirements first

Guidelines:
- Be conversational, friendly, and helpful
- Keep responses concise (1-3 sentences usually)
- If someone wants to build a website, ask about: type, style, colors, sections needed
- When you have enough info to generate, say "I'm ready to generate your website" and summarize what you'll create
- Use the phrase "GENERATE_WEBSITE:" followed by a description only when ready to generate

Example for website generation:
User: "I want a coffee shop website"
You: "Nice! What style - modern, cozy, minimal? Any specific sections like menu, about, contact?"
User: "Modern with a menu and contact form"
You: "GENERATE_WEBSITE: Modern coffee shop website with hero section, menu display, and contact form"`
            },
            ...conversationHistory
          ],
          temperature: 0.7
        })
      });

      if (response.ok) {
        const data = await response.json();
        return data.content || "I'm having trouble thinking right now. Could you try again?";
      }
    } catch (error) {
      console.error('AI chat error:', error);
    }
    
    return "I'm here to help! Tell me what you'd like to create or just chat.";
  };

  const generateWebsite = async (prompt: string): Promise<{ success: boolean; files: GeneratedFile[] }> => {
    // Show thinking animation
    setTaskSteps([
      { id: 'thinking', label: 'Thinking', status: 'running' },
    ]);

    try {
      const response = await fetch('/api/v1/mml/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, style: 'modern' })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.html) {
          setGeneratedHtml(data.html);
          setShowPreview(true);
          
          // Store all generated files
          const files: GeneratedFile[] = data.files || [];
          setGeneratedFiles(files);
          
          return { success: true, files };
        }
      }
    } catch (error) {
      console.error('Generation error:', error);
    }
    return { success: false, files: [] };
  };

  const streamText = async (messageId: string, fullText: string) => {
    const words = fullText.split(' ');
    let currentText = '';
    
    for (let i = 0; i < words.length; i++) {
      currentText += (i === 0 ? '' : ' ') + words[i];
      const textToShow = currentText;
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, content: textToShow } : msg
      ));
      
      const delay = Math.random() * 30 + 15;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, isStreaming: false } : msg
    ));
  };

  const sendMessage = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isThinking) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
      isNew: true
    };
    
    setMessages(prev => [...prev.map(m => ({ ...m, isNew: false })), userMessage]);
    setInput('');
    setIsThinking(true);

    const aiResponse = await getAIResponse(messageText);
    
    setIsThinking(false);
    
    const shouldGenerate = aiResponse.includes('GENERATE_WEBSITE:');
    let displayResponse = aiResponse;
    let generatePrompt = '';
    
    if (shouldGenerate) {
      const parts = aiResponse.split('GENERATE_WEBSITE:');
      displayResponse = parts[0].trim();
      generatePrompt = parts[1]?.trim() || messageText;
    }

    // Show AI response if there's one before generation
    if (displayResponse) {
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
        isNew: true
      };
      
      setMessages(prev => [...prev.map(m => ({ ...m, isNew: false })), assistantMessage]);
      await streamText(assistantMessageId, displayResponse);
    }

    // Handle website generation as a separate task
    if (shouldGenerate && generatePrompt) {
      // Add task message that shows generation progress
      const taskMessageId = (Date.now() + 2).toString();
      const startTime = Date.now();
      
      const taskMessage: Message = {
        id: taskMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isNew: true,
        isTask: true,
        taskStatus: 'running'
      };
      
      setMessages(prev => [...prev.map(m => ({ ...m, isNew: false })), taskMessage]);
      setIsGenerating(true);
      
      // Run generation (user can still chat during this)
      const { success, files } = await generateWebsite(generatePrompt);
      const duration = parseFloat(((Date.now() - startTime) / 1000).toFixed(2));
      
      // Format files for display
      const displayFiles = files.map(f => ({
        name: f.name,
        size: `${(f.size / 1024).toFixed(1)} KB`,
        type: f.type
      }));
      
      // Update task message to show completion
      setMessages(prev => prev.map(msg => 
        msg.id === taskMessageId 
          ? { 
              ...msg, 
              taskStatus: 'completed', 
              thinkingDuration: duration,
              generatedFiles: displayFiles.length > 0 ? displayFiles : [
                { name: 'index.html', size: '0 KB', type: 'html' },
              ],
              content: success 
                ? "✨ Done! Your website is ready. Check the preview panel!"
                : "I created a template for you. Let me know if you'd like any changes!"
            } 
          : msg
      ));
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleQuickAction = (action: typeof quickActions[0]) => {
    sendMessage(`I want to create a ${action.label.toLowerCase()}`);
  };

  const copyCode = async () => {
    await navigator.clipboard.writeText(generatedHtml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadHtml = () => {
    // If we have multiple files and in code view, download selected file
    if (generatedFiles.length > 0 && viewMode === 'code') {
      const file = generatedFiles.find(f => f.name === selectedFile);
      if (file) {
        const mimeTypes: Record<string, string> = {
          'html': 'text/html',
          'css': 'text/css',
          'js': 'application/javascript',
          'javascript': 'application/javascript',
          'json': 'application/json'
        };
        const blob = new Blob([file.content], { type: mimeTypes[file.type] || 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }
    }
    
    // Default: download the preview HTML
    const blob = new Blob([generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'website.html';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openFullscreen = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' });
    window.open(URL.createObjectURL(blob), '_blank');
  };

  const startNewChat = () => {
    setGeneratedHtml('');
    setGeneratedFiles([]);
    setSelectedFile('index.html');
    setMessages([]);
  };

  const isNewChat = messages.length === 0;

  return (
    <div className={`h-screen flex transition-colors duration-300 ${
      isDark ? 'bg-[#0c0c0c]' : 'bg-[#f8f9fa]'
    }`}>
      <style dangerouslySetInnerHTML={{ __html: styles }} />
      
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} flex-shrink-0 transition-all duration-300 overflow-hidden ${
        isDark ? 'bg-[#111111]' : 'bg-white'
      } border-r ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
        <div className="w-64 h-full flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                isDark 
                  ? 'bg-gradient-to-br from-white/10 to-white/5' 
                  : 'bg-gradient-to-br from-black/5 to-black/10'
              }`}>
                <Sparkles className={`w-4 h-4 ${isDark ? 'text-white' : 'text-black'}`} />
              </div>
              <span className={`font-semibold text-[15px] ${isDark ? 'text-white' : 'text-black'}`}>
                SOVRN
              </span>
            </div>
          </div>

          {/* New Chat Button */}
          <div className="px-3 mb-2">
            <button
              onClick={startNewChat}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isDark 
                  ? 'bg-white/[0.06] hover:bg-white/[0.1] text-white' 
                  : 'bg-black/[0.04] hover:bg-black/[0.08] text-black'
              }`}
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          {/* Search */}
          <div className="px-3 mb-4">
            <div className={`flex items-center gap-2 px-3 py-2 rounded-xl ${
              isDark ? 'bg-white/[0.04]' : 'bg-black/[0.02]'
            }`}>
              <Search className={`w-4 h-4 ${isDark ? 'text-white/30' : 'text-black/30'}`} />
              <input
                type="text"
                placeholder="Search chats..."
                className={`flex-1 bg-transparent text-sm outline-none ${
                  isDark ? 'text-white placeholder-white/30' : 'text-black placeholder-black/30'
                }`}
              />
            </div>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-3">
            <div className={`text-xs font-medium mb-2 px-2 ${isDark ? 'text-white/40' : 'text-black/40'}`}>
              Recent
            </div>
            <div className="space-y-1">
              {chatHistory.map((chat) => (
                <button
                  key={chat.id}
                  className={`w-full text-left px-3 py-2.5 rounded-xl transition-all group ${
                    isDark 
                      ? 'hover:bg-white/[0.06]' 
                      : 'hover:bg-black/[0.04]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {chat.hasWebsite ? (
                      <Globe className={`w-4 h-4 flex-shrink-0 ${isDark ? 'text-white/40' : 'text-black/40'}`} />
                    ) : (
                      <MessageSquare className={`w-4 h-4 flex-shrink-0 ${isDark ? 'text-white/40' : 'text-black/40'}`} />
                    )}
                    <span className={`text-sm truncate ${isDark ? 'text-white/80' : 'text-black/80'}`}>
                      {chat.title}
                    </span>
                  </div>
                  <p className={`text-xs truncate mt-1 ml-6 ${isDark ? 'text-white/30' : 'text-black/30'}`}>
                    {chat.preview}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Sidebar Footer */}
          <div className={`p-3 border-t ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
            <button
              onClick={() => setIsDark(!isDark)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                isDark 
                  ? 'hover:bg-white/[0.06] text-white/60 hover:text-white' 
                  : 'hover:bg-black/[0.04] text-black/60 hover:text-black'
              }`}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              {isDark ? 'Light Mode' : 'Dark Mode'}
            </button>
            <button
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                isDark 
                  ? 'hover:bg-white/[0.06] text-white/60 hover:text-white' 
                  : 'hover:bg-black/[0.04] text-black/60 hover:text-black'
              }`}
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </div>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className={`flex-shrink-0 h-14 flex items-center justify-between px-4 border-b ${
          isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'
        }`}>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className={`p-2 rounded-lg transition-all ${
                isDark 
                  ? 'hover:bg-white/[0.06] text-white/60' 
                  : 'hover:bg-black/[0.04] text-black/60'
              }`}
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            {!isNewChat && (
              <span className={`text-sm font-medium ${isDark ? 'text-white/60' : 'text-black/60'}`}>
                New conversation
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {generatedHtml && (
              <button
                onClick={() => setShowPreview(!showPreview)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all ${
                  isDark 
                    ? 'bg-white/[0.06] text-white/80 hover:bg-white/[0.1]' 
                    : 'bg-black/[0.04] text-black/80 hover:bg-black/[0.08]'
                }`}
              >
                {showPreview ? <PanelRightClose className="w-4 h-4" /> : <PanelRight className="w-4 h-4" />}
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </button>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Panel */}
          <div className={`flex-1 flex flex-col transition-all duration-300 ${
            showPreview && generatedHtml ? 'w-1/2' : 'w-full'
          }`}>
            
            {/* New Chat State */}
            {isNewChat ? (
              <div className="flex-1 flex flex-col items-center justify-center px-6">
                <div className="max-w-2xl w-full">
                  {/* Greeting */}
                  <h1 className={`animate-slide-in-right text-4xl font-semibold text-center mb-3 ${
                    isDark ? 'text-white' : 'text-black'
                  }`}>
                    {greeting}
                  </h1>
                  <p className={`animate-slide-in-right animate-delay-100 text-lg text-center mb-12 ${
                    isDark ? 'text-white/50' : 'text-black/50'
                  }`}>
                    What would you like to create today?
                  </p>

                  {/* Input */}
                  <div 
                    className={`animate-slide-in-right animate-delay-200 relative rounded-2xl transition-all duration-300 overflow-hidden ${
                      isDark 
                        ? 'bg-[#141414]' 
                        : 'bg-white shadow-xl shadow-black/5'
                    } ${isFocused 
                      ? isDark 
                        ? 'ring-1 ring-white/20' 
                        : 'ring-2 ring-black/10'
                      : isDark
                        ? 'ring-1 ring-white/[0.08]'
                        : 'ring-1 ring-black/[0.08]'
                    }`}
                  >
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onFocus={() => setIsFocused(true)}
                      onBlur={() => setIsFocused(false)}
                      placeholder="Describe the website you want to build..."
                      rows={3}
                      className={`w-full px-5 py-4 bg-transparent resize-none text-[15px] outline-none border-none focus:ring-0 ${
                        isDark 
                          ? 'text-white placeholder-white/40' 
                          : 'text-black placeholder-black/40'
                      }`}
                    />
                    <div className={`flex items-center justify-between px-4 pb-3 border-t ${
                      isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'
                    }`}>
                      <div className="flex items-center gap-2 pt-3">
                        <div className={`flex items-center gap-1.5 ${isDark ? 'text-white/30' : 'text-black/30'}`}>
                          <Sparkles className="w-3 h-3" />
                          <span className="text-xs font-medium">SOVRN</span>
                        </div>
                      </div>
                      <button
                        onClick={() => sendMessage()}
                        disabled={!input.trim()}
                        className={`mt-3 px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all ${
                          input.trim()
                            ? isDark
                              ? 'bg-white text-black hover:opacity-90'
                              : 'bg-black text-white hover:opacity-90'
                            : isDark
                              ? 'bg-white/[0.08] text-white/30'
                              : 'bg-black/[0.04] text-black/30'
                        } disabled:cursor-not-allowed`}
                      >
                        <Send className="w-4 h-4" />
                        Run
                      </button>
                    </div>
                  </div>

                  {/* Quick Actions */}
                  <div className="animate-slide-in-right animate-delay-300 flex flex-wrap items-center justify-center gap-2 mt-8">
                    {quickActions.map((action) => (
                      <button
                        key={action.label}
                        onClick={() => handleQuickAction(action)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm transition-all ${
                          isDark 
                            ? 'bg-white/[0.04] hover:bg-white/[0.08] text-white/70 hover:text-white border border-white/[0.06]' 
                            : 'bg-white hover:bg-black/[0.02] text-black/70 hover:text-black border border-black/[0.08] shadow-sm'
                        }`}
                      >
                        <action.icon className="w-4 h-4" />
                        {action.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto">
                  <div className="max-w-3xl mx-auto px-6 py-8 space-y-5">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`${message.isNew ? 'animate-fade-in-up' : ''} ${message.role === 'user' ? 'flex justify-end' : ''}`}
                      >
                        {message.role === 'assistant' ? (
                          <div className={`${
                            isDark ? 'text-white/90' : 'text-black/90'
                          }`}>
                            {/* Task indicator - running */}
                            {message.isTask && message.taskStatus === 'running' && (
                              <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                  <div className="flex items-center gap-1">
                                    <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/50' : 'bg-black/50'}`} style={{ animationDelay: '0ms' }} />
                                    <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/50' : 'bg-black/50'}`} style={{ animationDelay: '200ms' }} />
                                    <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/50' : 'bg-black/50'}`} style={{ animationDelay: '400ms' }} />
                                  </div>
                                  <span className={`text-sm ${isDark ? 'text-white/40' : 'text-black/40'}`}>
                                    Generating website
                                  </span>
                                </div>
                                <div className={`rounded-xl overflow-hidden border ${isDark ? 'border-white/[0.08] bg-white/[0.02]' : 'border-black/[0.08] bg-black/[0.02]'}`}>
                                  <div className={`px-4 py-2.5 flex items-center justify-between border-b ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
                                    <span className={`text-sm font-medium ${isDark ? 'text-white/70' : 'text-black/70'}`}>Files</span>
                                  </div>
                                  <div className={`px-4 py-3 ${isDark ? 'text-white/30' : 'text-black/30'}`}>
                                    <div className="flex items-center gap-2">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                      <span className="text-sm">Creating files...</span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                            {/* Task indicator - completed */}
                            {message.isTask && message.taskStatus === 'completed' && message.thinkingDuration && (
                              <p className={`text-sm mb-3 ${isDark ? 'text-white/40' : 'text-black/40'}`}>
                                Thinking Process {message.thinkingDuration}s
                              </p>
                            )}
                            {/* Generated files list */}
                            {message.isTask && message.taskStatus === 'completed' && message.generatedFiles && (
                              <div className={`mb-4 rounded-xl overflow-hidden border ${isDark ? 'border-white/[0.08] bg-white/[0.02]' : 'border-black/[0.08] bg-black/[0.02]'}`}>
                                <div className={`px-4 py-2.5 flex items-center justify-between border-b ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
                                  <span className={`text-sm font-medium ${isDark ? 'text-white/70' : 'text-black/70'}`}>Generated Files</span>
                                </div>
                                <div className="divide-y divide-white/[0.04]">
                                  {message.generatedFiles.map((file, idx) => (
                                    <div key={idx} className="px-4 py-2.5 flex items-center justify-between">
                                      <div className="flex items-center gap-2.5">
                                        <FileCode className={`w-4 h-4 ${isDark ? 'text-white/40' : 'text-black/40'}`} />
                                        <span className={`text-sm ${isDark ? 'text-white/80' : 'text-black/80'}`}>{file.name}</span>
                                      </div>
                                      <span className={`text-xs ${isDark ? 'text-white/30' : 'text-black/30'}`}>{file.size}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {/* Regular thinking duration for non-task messages */}
                            {!message.isTask && message.thinkingDuration && (
                              <p className={`text-sm mb-2 ${isDark ? 'text-white/40' : 'text-black/40'}`}>
                                Thinking Process {message.thinkingDuration}s
                              </p>
                            )}
                            {/* Message content - only show if not running task or has content */}
                            {(message.content || (message.isTask && message.taskStatus === 'completed')) && (
                              <p className="text-[15px] leading-[1.7]">
                                {message.content}
                                {message.isStreaming && (
                                  <span className={`typing-cursor inline-block w-[3px] h-[1.1em] ml-1 align-middle rounded-sm ${
                                    isDark ? 'bg-white/70' : 'bg-black/70'
                                  }`} />
                                )}
                              </p>
                            )}
                            {/* Action buttons */}
                            {!message.isStreaming && message.content && (!message.isTask || message.taskStatus === 'completed') && (
                              <div className="flex items-center gap-1 mt-3">
                                <button 
                                  onClick={() => navigator.clipboard.writeText(message.content)}
                                  className={`p-1.5 rounded-lg transition-all ${isDark ? 'hover:bg-white/[0.06] text-white/40 hover:text-white/70' : 'hover:bg-black/[0.04] text-black/40 hover:text-black/70'}`}
                                  title="Copy"
                                >
                                  <Copy className="w-4 h-4" />
                                </button>
                                <button 
                                  className={`p-1.5 rounded-lg transition-all ${isDark ? 'hover:bg-white/[0.06] text-white/40 hover:text-white/70' : 'hover:bg-black/[0.04] text-black/40 hover:text-black/70'}`}
                                  title="Good response"
                                >
                                  <ThumbsUp className="w-4 h-4" />
                                </button>
                                <button 
                                  className={`p-1.5 rounded-lg transition-all ${isDark ? 'hover:bg-white/[0.06] text-white/40 hover:text-white/70' : 'hover:bg-black/[0.04] text-black/40 hover:text-black/70'}`}
                                  title="Bad response"
                                >
                                  <ThumbsDown className="w-4 h-4" />
                                </button>
                                <button 
                                  className={`p-1.5 rounded-lg transition-all ${isDark ? 'hover:bg-white/[0.06] text-white/40 hover:text-white/70' : 'hover:bg-black/[0.04] text-black/40 hover:text-black/70'}`}
                                  title="Try again"
                                >
                                  <RotateCw className="w-4 h-4" />
                                </button>
                                <button 
                                  className={`p-1.5 rounded-lg transition-all ${isDark ? 'hover:bg-white/[0.06] text-white/40 hover:text-white/70' : 'hover:bg-black/[0.04] text-black/40 hover:text-black/70'}`}
                                  title="More actions"
                                >
                                  <MoreHorizontal className="w-4 h-4" />
                                </button>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className={`inline-block max-w-[80%] rounded-2xl px-4 py-2.5 ${
                            isDark 
                              ? 'bg-white/[0.08] text-white' 
                              : 'bg-black/[0.06] text-black'
                          }`}>
                            <p className="text-[15px] leading-relaxed">
                              {message.content}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* Thinking animation - while AI is working */}
                    {isThinking && (
                      <div className="animate-fade-in-up">
                        <div className="flex items-center gap-1">
                          <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/60' : 'bg-black/60'}`} style={{ animationDelay: '0ms' }} />
                          <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/60' : 'bg-black/60'}`} style={{ animationDelay: '200ms' }} />
                          <div className={`thinking-dot w-1.5 h-1.5 rounded-full ${isDark ? 'bg-white/60' : 'bg-black/60'}`} style={{ animationDelay: '400ms' }} />
                        </div>
                      </div>
                    )}
                    
                    <div ref={messagesEndRef} />
                  </div>
                </div>

                {/* Input */}
                <div className="flex-shrink-0">
                  <div className="max-w-3xl mx-auto px-6 py-4">
                    <div 
                      className={`relative rounded-2xl transition-all duration-300 overflow-hidden ${
                        isDark 
                          ? 'bg-[#1a1a1a]' 
                          : 'bg-white shadow-sm'
                      } ${isFocused 
                        ? isDark 
                          ? 'ring-1 ring-white/15' 
                          : 'ring-2 ring-black/10'
                        : isDark
                          ? 'ring-1 ring-white/[0.08]'
                          : 'ring-1 ring-black/[0.08]'
                      }`}
                    >
                      <div className="flex items-center">
                        <textarea
                          ref={inputRef}
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={handleKeyDown}
                          onFocus={() => setIsFocused(true)}
                          onBlur={() => setIsFocused(false)}
                          placeholder="Continue the conversation..."
                          disabled={isThinking}
                          rows={1}
                          className={`flex-1 px-4 py-3.5 bg-transparent resize-none text-[15px] outline-none border-none focus:ring-0 leading-normal ${
                            isDark 
                              ? 'text-white placeholder-white/40' 
                              : 'text-black placeholder-black/40'
                          } disabled:opacity-50`}
                        />
                        
                        <button
                          onClick={() => sendMessage()}
                          disabled={!input.trim() || isThinking}
                          className={`mr-2 w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
                            input.trim() && !isThinking
                              ? isDark
                                ? 'bg-white/10 text-white hover:bg-white/15'
                                : 'bg-black text-white hover:opacity-90'
                              : isDark
                                ? 'bg-white/[0.04] text-white/20'
                                : 'bg-black/[0.04] text-black/20'
                          } disabled:cursor-not-allowed`}
                        >
                          {isThinking ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                    <p className={`text-center text-xs mt-3 ${
                      isDark ? 'text-white/30' : 'text-black/30'
                    }`}>
                      Sovrn can make mistakes. Check important info.
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Preview Panel */}
          {showPreview && generatedHtml && (
            <div className={`w-1/2 flex flex-col border-l animate-scale-in ${
              isDark ? 'border-white/[0.06] bg-[#0a0a0a]' : 'border-black/[0.06] bg-[#fafafa]'
            }`}>
              {/* Toolbar */}
              <div className={`flex-shrink-0 px-4 py-3 flex items-center justify-between border-b ${
                isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'
              }`}>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setViewMode('preview')}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 ${
                      viewMode === 'preview'
                        ? isDark ? 'bg-white/10 text-white' : 'bg-black/10 text-black'
                        : isDark ? 'text-white/40 hover:text-white/60' : 'text-black/40 hover:text-black/60'
                    }`}
                  >
                    <Eye className="w-4 h-4" />
                    Preview
                  </button>
                  <button
                    onClick={() => setViewMode('code')}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 ${
                      viewMode === 'code'
                        ? isDark ? 'bg-white/10 text-white' : 'bg-black/10 text-black'
                        : isDark ? 'text-white/40 hover:text-white/60' : 'text-black/40 hover:text-black/60'
                    }`}
                  >
                    <Code2 className="w-4 h-4" />
                    Code
                  </button>
                </div>

                <div className="flex items-center gap-1">
                  <button onClick={openFullscreen} className={`p-2 rounded-lg transition-all ${isDark ? 'text-white/40 hover:text-white hover:bg-white/[0.06]' : 'text-black/40 hover:text-black hover:bg-black/[0.04]'}`} title="Fullscreen">
                    <Maximize2 className="w-4 h-4" />
                  </button>
                  <button onClick={copyCode} className={`p-2 rounded-lg transition-all ${isDark ? 'text-white/40 hover:text-white hover:bg-white/[0.06]' : 'text-black/40 hover:text-black hover:bg-black/[0.04]'}`} title="Copy code">
                    {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={downloadHtml} className={`p-2 rounded-lg transition-all ${isDark ? 'text-white/40 hover:text-white hover:bg-white/[0.06]' : 'text-black/40 hover:text-black hover:bg-black/[0.04]'}`} title="Download">
                    <Download className="w-4 h-4" />
                  </button>
                  <button onClick={startNewChat} className={`p-2 rounded-lg transition-all ${isDark ? 'text-white/40 hover:text-white hover:bg-white/[0.06]' : 'text-black/40 hover:text-black hover:bg-black/[0.04]'}`} title="New chat">
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 relative overflow-hidden">
                {viewMode === 'preview' ? (
                  <iframe
                    ref={iframeRef}
                    srcDoc={generatedHtml}
                    className="w-full h-full bg-white"
                    sandbox="allow-scripts"
                    title="Preview"
                  />
                ) : (
                  <div className={`h-full flex flex-col ${isDark ? 'bg-[#0a0a0a]' : 'bg-[#fafafa]'}`}>
                    {/* File tabs */}
                    {generatedFiles.length > 0 && (
                      <div className={`flex items-center gap-1 px-4 py-2 border-b ${
                        isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'
                      }`}>
                        {generatedFiles.map((file) => (
                          <button
                            key={file.name}
                            onClick={() => setSelectedFile(file.name)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                              selectedFile === file.name
                                ? isDark ? 'bg-white/10 text-white' : 'bg-black/10 text-black'
                                : isDark ? 'text-white/40 hover:text-white/60 hover:bg-white/[0.04]' : 'text-black/40 hover:text-black/60 hover:bg-black/[0.04]'
                            }`}
                          >
                            {file.name}
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="flex-1 overflow-auto p-6">
                      <pre className={`text-xs font-mono whitespace-pre-wrap leading-relaxed ${isDark ? 'text-white/70' : 'text-black/70'}`}>
                        {generatedFiles.find(f => f.name === selectedFile)?.content || generatedHtml}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
