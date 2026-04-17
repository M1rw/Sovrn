'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useSession } from 'next-auth/react';
import { 
  Send, 
  Bot,
  Brain,
  Briefcase,
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
  PanelLeftClose,
  PanelLeftOpen,
  FolderPlus,
  Gamepad2,
  Music2,
  Plus,
  Search,
  Globe,
  FileCode,
  Palette,
  Zap,
  MessageSquare,
  Settings,
} from 'lucide-react';
import {
  buildPreviewEventsStreamPath,
  jobsApi,
  projectsApi,
  resolveCanonicalJobResult,
  type Job,
  type PreviewSessionResponse,
} from '@/lib/api';
import { usePreviewRuntime } from '@/hooks/use-preview-runtime';
import {
  createCorrelationId,
  getClientSessionId,
  recordClientMetric,
  recordRequestMetric,
  recordUiError,
} from '@/lib/telemetry';
import {
  getPreviewStreamFallbackMessage,
  getPreviewStreamStateOnError,
  shouldMarkPreviewStreamStale,
  toMountDescriptorFromArtifact,
  toMountDescriptorFromPreviewUpdate,
  type GeneratedFile,
  type PreviewStreamState,
} from './preview-lifecycle';

type ViewMode = 'preview' | 'code';
type PreviewBridgeState = 'idle' | 'pending' | 'connected' | 'failed';

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
  resolvedAction?: BuilderResolvedAction;
  actionReason?: string;
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

interface BuilderChatApiResponse {
  content: string;
  resolvedAction?: BuilderResolvedAction;
  resolvedActionReason?: string;
  proposedAction?: BuilderResolvedAction;
  generationHandoffAllowed?: boolean;
  conversationMeta?: {
    threadId?: string;
    turnIndex?: number;
    stateVersion?: number;
    idempotencyKey?: string;
  };
}

type BuilderResolvedAction =
  | 'respond'
  | 'ask_clarification'
  | 'ready_to_generate'
  | 'propose_revision'
  | 'error_recoverable';

const FRONTEND_RESOLVED_ACTION_ENABLED =
  process.env.NEXT_PUBLIC_BUILDER_RESOLVED_ACTION_ENABLED !== 'false';
const FRONTEND_CONVERSATION_STATE_ENABLED =
  process.env.NEXT_PUBLIC_BUILDER_CONVERSATION_STATE_ENABLED === 'true';
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ALLOWED_RESOLVED_ACTIONS: ReadonlySet<BuilderResolvedAction> = new Set([
  'respond',
  'ask_clarification',
  'ready_to_generate',
  'propose_revision',
  'error_recoverable',
]);
const PREVIEW_BRIDGE_FLAG = '__sovrnPreviewBridge';
const PREVIEW_STREAM_STALE_THRESHOLD_MS = 6000;

const isUuid = (value: unknown): value is string =>
  typeof value === 'string' && UUID_PATTERN.test(value);

const isResolvedAction = (value: unknown): value is BuilderResolvedAction =>
  typeof value === 'string' && ALLOWED_RESOLVED_ACTIONS.has(value as BuilderResolvedAction);

const parseIntegerField = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isInteger(value) ? value : undefined;

const createClientIdempotencyKey = (): string =>
  `builder-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

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
  const { data: session } = useSession();
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
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChatId, setSelectedChatId] = useState<string | null>('1');
  const [greeting, setGreeting] = useState('Hello');
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [conversationThreadId, setConversationThreadId] = useState<string | null>(null);
  const [conversationTurnIndex, setConversationTurnIndex] = useState<number | null>(null);
  const [conversationStateVersion, setConversationStateVersion] = useState<number | null>(null);
  const [previewBootstrapSession, setPreviewBootstrapSession] = useState<PreviewSessionResponse | null>(null);
  const [previewBridgeState, setPreviewBridgeState] = useState<PreviewBridgeState>('idle');
  const [previewBridgeLastEventAt, setPreviewBridgeLastEventAt] = useState<number | null>(null);
  const [previewStreamState, setPreviewStreamState] = useState<PreviewStreamState>('idle');
  const [previewStreamLastEventAt, setPreviewStreamLastEventAt] = useState<number | null>(null);
  const [previewStreamReconnectNonce, setPreviewStreamReconnectNonce] = useState(0);
  const [editorDrafts, setEditorDrafts] = useState<Record<string, string>>({});
  const [isApplyingEditorPatch, setIsApplyingEditorPatch] = useState(false);
  const [editorBridgeLastAppliedAt, setEditorBridgeLastAppliedAt] = useState<number | null>(null);
  const [isRestartingPreviewRuntime, setIsRestartingPreviewRuntime] = useState(false);
  const {
    kind: previewRuntimeKind,
    status: previewRuntimeStatus,
    detail: previewRuntimeDetail,
    previewUrl: previewRuntimeUrl,
    bridgeChannel: previewRuntimeBridgeChannel,
    mountedFileCount: previewRuntimeMountedFileCount,
    boot: bootPreviewRuntime,
    mountWorkspace,
    clearMountedWorkspace,
  } = usePreviewRuntime();
  const [chatHistory] = useState<ChatHistory[]>([
    { id: '1', title: 'Coffee Shop Website', preview: 'Modern coffee shop with menu...', timestamp: new Date(Date.now() - 86400000), hasWebsite: true },
    { id: '2', title: 'Portfolio Design', preview: 'Minimal portfolio with projects...', timestamp: new Date(Date.now() - 172800000), hasWebsite: true },
    { id: '3', title: 'SaaS Landing Page', preview: 'Dark theme landing page...', timestamp: new Date(Date.now() - 259200000), hasWebsite: true },
  ]);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const previewEventSourceRef = useRef<EventSource | null>(null);
  const previewUpdateStartedAtRef = useRef<number | null>(null);

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

  const projectCollections = [
    { id: 'brainstorms', label: 'Brainstorms', icon: Brain, tone: 'text-pink-400' },
    { id: 'smartvision', label: 'SmartVision', icon: Briefcase, tone: 'text-zinc-300' },
    { id: 'music-song', label: 'Music & Song', icon: Music2, tone: 'text-red-400' },
    { id: 'programming', label: 'Programming', icon: Code2, tone: 'text-emerald-400' },
    { id: 'roblox', label: 'Roblox', icon: Gamepad2, tone: 'text-sky-400' },
  ];

  useEffect(() => {
    setMounted(true);
    setGreeting(getGreeting());
  }, []);

  useEffect(() => {
    void bootPreviewRuntime();
  }, [bootPreviewRuntime]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  useEffect(() => {
    setEditorDrafts((previousDrafts) => {
      const nextDrafts: Record<string, string> = {};
      for (const file of generatedFiles) {
        if (Object.prototype.hasOwnProperty.call(previousDrafts, file.name)) {
          nextDrafts[file.name] = previousDrafts[file.name];
        }
      }
      return nextDrafts;
    });

    if (generatedFiles.length > 0 && !generatedFiles.some((file) => file.name === selectedFile)) {
      setSelectedFile(generatedFiles[0].name);
    }
  }, [generatedFiles, selectedFile]);

  useEffect(() => {
    if (!generatedHtml && generatedFiles.length === 0) {
      setPreviewBridgeState('idle');
      return;
    }

    let isCancelled = false;

    const mountLocalWorkspace = async () => {
      const mounted = await mountWorkspace({
        files: generatedFiles.map((file) => ({
          path: file.name,
          content: file.content,
          language: file.type,
        })),
        entrypoint: 'index.html',
        fallbackHtml: generatedHtml,
      });

      if (!isCancelled) {
        setPreviewBridgeState(mounted ? 'pending' : 'failed');
      }
    };

    const mountVerifiedPreviewSessionWorkspace = async () => {
      if (!previewBootstrapSession) {
        await mountLocalWorkspace();
        return;
      }

      try {
        const verifiedSession = await projectsApi.verifyPreviewSession(
          previewBootstrapSession.project_id,
          {
            token: previewBootstrapSession.token,
            generation_id: previewBootstrapSession.generation_id,
            entrypoint: previewBootstrapSession.entrypoint,
          },
          session?.accessToken
        );

        const artifact = await projectsApi.previewArtifactFromEndpoint(
          previewBootstrapSession.token,
          verifiedSession.artifact_endpoint
        );

        if (isCancelled) {
          return;
        }

        const artifactMount = toMountDescriptorFromArtifact(
          artifact,
          verifiedSession.entrypoint,
          generatedHtml
        );

        const mounted = await mountWorkspace({
          files: artifactMount.mountFiles,
          entrypoint: artifactMount.entrypoint,
          fallbackHtml: artifactMount.fallbackHtml,
        });

        if (!isCancelled) {
          setPreviewBridgeState(mounted ? 'pending' : 'failed');
        }
      } catch (error) {
        console.warn('Preview session artifact bootstrap failed, using local workspace fallback.', error);
        if (!isCancelled) {
          await mountLocalWorkspace();
        }
      }
    };

    void mountVerifiedPreviewSessionWorkspace();

    return () => {
      isCancelled = true;
    };
  }, [generatedFiles, generatedHtml, mountWorkspace, previewBootstrapSession, session?.accessToken]);

  useEffect(() => {
    if (!previewRuntimeBridgeChannel || !previewRuntimeUrl) {
      return;
    }

    const handlePreviewBridgeMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }

      if (!event.data || typeof event.data !== 'object') {
        return;
      }

      const payload = event.data as Record<string, unknown>;
      if (payload[PREVIEW_BRIDGE_FLAG] !== true) {
        return;
      }

      if (payload.channel !== previewRuntimeBridgeChannel) {
        return;
      }

      const messageType = payload.type;
      if (messageType === 'sovrn.preview.ready' || messageType === 'sovrn.preview.pong') {
        setPreviewBridgeState('connected');
        setPreviewBridgeLastEventAt(Date.now());
        setIsRestartingPreviewRuntime(false);
      }
    };

    window.addEventListener('message', handlePreviewBridgeMessage);

    return () => {
      window.removeEventListener('message', handlePreviewBridgeMessage);
    };
  }, [previewRuntimeBridgeChannel, previewRuntimeUrl]);

  useEffect(() => {
    if (
      !previewBootstrapSession?.project_id ||
      !previewBootstrapSession?.token ||
      !showPreview
    ) {
      if (previewEventSourceRef.current) {
        previewEventSourceRef.current.close();
        previewEventSourceRef.current = null;
      }
      setPreviewStreamState('idle');
      setPreviewStreamLastEventAt(null);
      return;
    }

    const streamUrl = buildPreviewEventsStreamPath(previewBootstrapSession.project_id, {
      generation_id: previewBootstrapSession.generation_id,
      entrypoint: previewBootstrapSession.entrypoint,
      preview_token: previewBootstrapSession.token,
      poll_interval_ms: 1500,
    });

    const eventSource = new EventSource(streamUrl);
    previewEventSourceRef.current = eventSource;
    setPreviewStreamState('connecting');

    const handleHeartbeat = () => {
      setPreviewStreamState('live');
      setPreviewStreamLastEventAt(Date.now());
    };

    const handlePreviewUpdated = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as unknown;
        const updateMount = toMountDescriptorFromPreviewUpdate(payload);
        const nextGeneratedFiles = updateMount.generatedFiles;

        if (nextGeneratedFiles.length > 0) {
          setGeneratedFiles(nextGeneratedFiles);
          setEditorDrafts({});
          setSelectedFile((previous) =>
            nextGeneratedFiles.some((file) => file.name === previous)
              ? previous
              : nextGeneratedFiles[0].name
          );
        }

        const nextHtml = updateMount.nextGeneratedHtml;
        if (nextHtml) {
          previewUpdateStartedAtRef.current = Date.now();
          setGeneratedHtml(nextHtml);
        }

        void mountWorkspace({
          files: updateMount.mountFiles,
          entrypoint: updateMount.entrypoint,
          fallbackHtml: updateMount.fallbackHtml,
        });

        setPreviewBridgeState('pending');
        setPreviewStreamState('live');
        setPreviewStreamLastEventAt(Date.now());
        recordClientMetric('builder_preview_stream_update_count', 1, {
          source: 'sse',
        });
      } catch (error) {
        console.error('Failed to process preview stream update event:', error);
        setPreviewStreamState('error');
      }
    };

    const handleStreamError = () => {
      setPreviewStreamState(getPreviewStreamStateOnError(eventSource.readyState));
    };

    eventSource.addEventListener('heartbeat', handleHeartbeat as EventListener);
    eventSource.addEventListener('preview.updated', handlePreviewUpdated as EventListener);
    eventSource.onerror = handleStreamError;

    return () => {
      eventSource.removeEventListener('heartbeat', handleHeartbeat as EventListener);
      eventSource.removeEventListener('preview.updated', handlePreviewUpdated as EventListener);
      eventSource.close();
      if (previewEventSourceRef.current === eventSource) {
        previewEventSourceRef.current = null;
      }
    };
  }, [
    mountWorkspace,
    previewBootstrapSession?.entrypoint,
    previewBootstrapSession?.generation_id,
    previewBootstrapSession?.project_id,
    previewBootstrapSession?.token,
    previewStreamReconnectNonce,
    showPreview,
  ]);

  useEffect(() => {
    if (!showPreview || previewStreamState !== 'live' || !previewStreamLastEventAt) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (
        shouldMarkPreviewStreamStale(
          previewStreamLastEventAt,
          Date.now(),
          PREVIEW_STREAM_STALE_THRESHOLD_MS
        )
      ) {
        setPreviewStreamState((current) => (current === 'live' ? 'stale' : current));
      }
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [previewStreamLastEventAt, previewStreamState, showPreview]);

  const filteredChats = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return chatHistory;
    return chatHistory.filter(
      (chat) =>
        chat.title.toLowerCase().includes(query) ||
        chat.preview.toLowerCase().includes(query)
    );
  }, [chatHistory, searchQuery]);

  const groupedChats = useMemo(() => {
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;

    const groups: Record<string, ChatHistory[]> = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    };

    for (const chat of filteredChats) {
      const diff = now - chat.timestamp.getTime();
      if (diff < oneDay) {
        groups.Today.push(chat);
      } else if (diff < oneDay * 2) {
        groups.Yesterday.push(chat);
      } else if (diff < oneDay * 7) {
        groups['Previous 7 Days'].push(chat);
      } else {
        groups.Older.push(chat);
      }
    }

    return groups;
  }, [filteredChats]);

  const buildConversationContext = () => {
    return messages.map(m => ({
      role: m.role,
      content: m.content
    }));
  };

  const getAIResponse = async (userMessage: string): Promise<BuilderChatApiResponse> => {
    const conversationHistory = buildConversationContext();
    const isIncrementalConversationRequest =
      FRONTEND_CONVERSATION_STATE_ENABLED && isUuid(conversationThreadId);
    const requestMessages = isIncrementalConversationRequest
      ? [{ role: 'user' as const, content: userMessage }]
      : [...conversationHistory, { role: 'user' as const, content: userMessage }];

    const systemPrompt = `You are SOVRN, a friendly and intelligent AI assistant that helps users build websites.

Return only valid JSON matching this schema:
{
  "version": "1.0",
  "action": "respond" | "ask_clarification" | "ready_to_generate" | "propose_revision" | "error_recoverable",
  "assistant_message": "string",
  "questions": ["string"],
  "generation_request": { "brief": "string" } | null,
  "revision_request": null,
  "state_patch": {},
  "meta": { "source": "builder" }
}

Rules:
- Use action "ready_to_generate" only when you have enough detail to build the site now.
- Keep assistant_message concise and user-friendly.
- If action is "ready_to_generate", include generation_request.brief.`;
    
    const aiChatStartedAt = Date.now();
    const correlationId = createCorrelationId('/api/v1/ai/chat');

    try {
      const requestBody: Record<string, unknown> = {
        messages: [
          {
            role: 'system',
            content: systemPrompt
          },
          ...requestMessages
        ],
        temperature: 0.7,
        max_tokens: 512,
        json_mode: true,
      };

      if (FRONTEND_CONVERSATION_STATE_ENABLED) {
        requestBody.idempotency_key = createClientIdempotencyKey();
        if (isUuid(conversationThreadId)) {
          requestBody.thread_id = conversationThreadId;
        }

        const sessionUserId = session?.user?.id;
        if (isUuid(sessionUserId)) {
          requestBody.user_id = sessionUserId;
        }
      }

      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Correlation-ID': correlationId,
          'X-Client-Session-ID': getClientSessionId(),
        },
        body: JSON.stringify(requestBody)
      });

      recordRequestMetric('/api/v1/ai/chat', 'POST', response.status, Date.now() - aiChatStartedAt);

      if (response.ok) {
        const data = await response.json() as {
          content?: unknown;
          resolved_action?: unknown;
          resolved_action_reason?: unknown;
          proposed_action?: unknown;
          generation_handoff_allowed?: unknown;
          thread_id?: unknown;
          turn_index?: unknown;
          state_version?: unknown;
          idempotency_key?: unknown;
        };

        const threadId = isUuid(data.thread_id) ? data.thread_id : undefined;
        const turnIndex = parseIntegerField(data.turn_index);
        const stateVersion = parseIntegerField(data.state_version);
        const idempotencyKey =
          typeof data.idempotency_key === 'string' ? data.idempotency_key : undefined;
        const hasConversationMeta =
          threadId !== undefined ||
          turnIndex !== undefined ||
          stateVersion !== undefined ||
          idempotencyKey !== undefined;

        return {
          content: typeof data.content === 'string'
            ? data.content
            : "I'm having trouble thinking right now. Could you try again?",
          resolvedAction: isResolvedAction(data.resolved_action) ? data.resolved_action : undefined,
          resolvedActionReason:
            typeof data.resolved_action_reason === 'string'
              ? data.resolved_action_reason
              : undefined,
          proposedAction: isResolvedAction(data.proposed_action) ? data.proposed_action : undefined,
          generationHandoffAllowed:
            typeof data.generation_handoff_allowed === 'boolean'
              ? data.generation_handoff_allowed
              : undefined,
          conversationMeta: hasConversationMeta
            ? {
                threadId,
                turnIndex,
                stateVersion,
                idempotencyKey,
              }
            : undefined,
        };
      }
    } catch (error) {
      recordRequestMetric('/api/v1/ai/chat', 'POST', 0, Date.now() - aiChatStartedAt);
      recordUiError(error, 'boundary', { scope: 'builder_ai_chat' });
      console.error('AI chat error:', error);
    }
    
    return {
      content: "I'm here to help! Tell me what you'd like to create or just chat.",
    };
  };

  const generateWebsite = async (
    prompt: string
  ): Promise<{
    success: boolean;
    files: GeneratedFile[];
    projectId?: string;
    jobId?: string;
    generationId?: string;
    previewSession?: PreviewSessionResponse;
    error?: string;
  }> => {
    const generationStartedAt = Date.now();
    setTaskSteps([
      { id: 'create-project', label: 'Create project', status: 'running' },
      { id: 'queue-job', label: 'Queue generation job', status: 'pending' },
      { id: 'process-job', label: 'Process generation job', status: 'pending' },
    ]);

    let projectId: string | undefined;
    let jobId: string | undefined;

    try {
      const token = session?.accessToken;
      if (!token) {
        throw new Error('Sign in is required for canonical generation.');
      }

      const projectName = prompt.trim().split(/\s+/).slice(0, 6).join(' ') || 'Generated Site';
      const project = await projectsApi.create(token, {
        name: projectName,
        description: prompt.slice(0, 180),
        locale: 'en',
      });
      projectId = project.id;

      setTaskSteps([
        { id: 'create-project', label: 'Create project', status: 'completed' },
        { id: 'queue-job', label: 'Queue generation job', status: 'running' },
        { id: 'process-job', label: 'Process generation job', status: 'pending' },
      ]);

      const job = await projectsApi.generate(token, project.id, {
        brief: prompt,
        locale: 'en',
        settings: { style: 'modern' },
      });
      jobId = job.id;

      setTaskSteps([
        { id: 'create-project', label: 'Create project', status: 'completed' },
        { id: 'queue-job', label: 'Queue generation job', status: 'completed' },
        { id: 'process-job', label: 'Process generation job', status: 'running' },
      ]);

      const pollStartedAt = Date.now();
      let currentJob: Job = job;

      while (currentJob.status === 'queued' || currentJob.status === 'processing') {
        if (Date.now() - pollStartedAt > 180000) {
          throw new Error('Generation timed out waiting for job completion.');
        }

        await new Promise((resolve) => setTimeout(resolve, 1500));
        currentJob = await jobsApi.get(token, job.id);
      }

      const projectWithGenerations = await projectsApi.get(token, project.id);
      const resolved = resolveCanonicalJobResult(currentJob, projectWithGenerations);
      if (!resolved.ok || !resolved.previewHtml) {
        throw new Error(resolved.error || 'Canonical artifacts could not be resolved.');
      }

      const files = (resolved.files || []) as GeneratedFile[];

      let previewSession: PreviewSessionResponse | undefined;
      try {
        previewSession = await projectsApi.createPreviewSession(token, project.id, {
          generation_id: resolved.generationId,
          entrypoint: 'index.html',
        });
        setPreviewBootstrapSession(previewSession);
      } catch (previewSessionError) {
        console.warn('Preview session bootstrap skipped:', previewSessionError);
        setPreviewBootstrapSession(null);
      }

      previewUpdateStartedAtRef.current = Date.now();
      setGeneratedHtml(resolved.previewHtml);
      setShowPreview(true);
      setGeneratedFiles(files);
      setTaskSteps((prev) => prev.map((step) => ({ ...step, status: 'completed' })));
      recordClientMetric('builder_generation_duration_ms', Date.now() - generationStartedAt, {
        success: true,
      });

      return {
        success: true,
        files,
        projectId,
        jobId,
        generationId: resolved.generationId,
        previewSession,
      };
    } catch (error) {
      console.error('Canonical generation error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown canonical generation error.';
      recordClientMetric('builder_generation_duration_ms', Date.now() - generationStartedAt, {
        success: false,
      });
      recordUiError(error, 'boundary', { scope: 'builder_generation' });
      return {
        success: false,
        files: [],
        projectId,
        jobId,
        error: errorMessage,
      };
    }
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

    const aiRoundTripStartedAt = Date.now();
    const aiResponse = await getAIResponse(messageText);
    if (FRONTEND_CONVERSATION_STATE_ENABLED && aiResponse.conversationMeta) {
      if (isUuid(aiResponse.conversationMeta.threadId)) {
        setConversationThreadId(aiResponse.conversationMeta.threadId);
      }
      if (typeof aiResponse.conversationMeta.turnIndex === 'number') {
        setConversationTurnIndex(aiResponse.conversationMeta.turnIndex);
      }
      if (typeof aiResponse.conversationMeta.stateVersion === 'number') {
        setConversationStateVersion(aiResponse.conversationMeta.stateVersion);
      }
    }
    recordClientMetric('builder_chat_roundtrip_ms', Date.now() - aiRoundTripStartedAt, {
      endpoint: '/api/v1/ai/chat',
    });
    
    setIsThinking(false);

    const content = aiResponse.content || '';
    let shouldGenerate = false;
    let displayResponse = content;
    let generatePrompt = '';
    let parsedAction: BuilderResolvedAction | undefined;

    let structuredAssistantMessage: string | undefined;
    let structuredGenerationBrief: string | undefined;

    try {
      const parsed = JSON.parse(content) as {
        action?: unknown;
        assistant_message?: unknown;
        generation_request?: unknown;
      };

      if (isResolvedAction(parsed.action)) {
        parsedAction = parsed.action;
      }

      if (typeof parsed.assistant_message === 'string' && parsed.assistant_message.trim()) {
        structuredAssistantMessage = parsed.assistant_message.trim();
      }

      const generationRequest = parsed.generation_request;
      if (generationRequest && typeof generationRequest === 'object' && !Array.isArray(generationRequest)) {
        const brief = (generationRequest as { brief?: unknown }).brief;
        if (typeof brief === 'string' && brief.trim()) {
          structuredGenerationBrief = brief.trim();
        }
      }
    } catch {
      // Keep raw content display when the model response is not valid JSON.
    }

    const resolvedAction = aiResponse.resolvedAction || parsedAction;
    const generationHandoffAllowed =
      aiResponse.generationHandoffAllowed ?? (resolvedAction === 'ready_to_generate');

    displayResponse = structuredAssistantMessage || content;
    shouldGenerate = resolvedAction === 'ready_to_generate' && generationHandoffAllowed === true;
    generatePrompt = shouldGenerate
      ? (structuredGenerationBrief || messageText)
      : '';

    // Show AI response if there's one before generation
    if (displayResponse) {
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
        isNew: true,
        resolvedAction: aiResponse.resolvedAction,
        actionReason: aiResponse.resolvedActionReason,
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
      const { success, files, projectId, jobId, generationId, previewSession, error } = await generateWebsite(generatePrompt);
      const duration = parseFloat(((Date.now() - startTime) / 1000).toFixed(2));
      
      // Format files for display
      const displayFiles = files.map(f => ({
        name: f.name,
        size: `${(f.size / 1024).toFixed(1)} KB`,
        type: f.type
      }));
      const traceParts = [
        projectId ? `Project: ${projectId}` : null,
        jobId ? `Job: ${jobId}` : null,
        generationId ? `Generation: ${generationId}` : null,
        previewSession ? `Preview session: active` : null,
      ].filter(Boolean).join(', ');
      
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
                ? `✨ Done! Your website is ready. Check the preview panel! (${traceParts})`
                : `❌ Generation failed${traceParts ? ` (${traceParts})` : ''}: ${error || 'Unknown error.'}`
            } 
          : msg
      ));
      setIsGenerating(false);
    }
  };

  const selectedGeneratedFile = generatedFiles.find((file) => file.name === selectedFile);
  const selectedFileDraftContent = selectedGeneratedFile
    ? (editorDrafts[selectedGeneratedFile.name] ?? selectedGeneratedFile.content)
    : generatedHtml;
  const draftCount = Object.keys(editorDrafts).length;

  const updateEditorDraft = (fileName: string, nextContent: string) => {
    setEditorDrafts((previous) => {
      const sourceContent = generatedFiles.find((file) => file.name === fileName)?.content;
      if (sourceContent === undefined || sourceContent === nextContent) {
        if (!Object.prototype.hasOwnProperty.call(previous, fileName)) {
          return previous;
        }

        const { [fileName]: _, ...rest } = previous;
        return rest;
      }

      return {
        ...previous,
        [fileName]: nextContent,
      };
    });
  };

  const discardEditorDrafts = () => {
    setEditorDrafts({});
  };

  const applyEditorPatchToPreview = async () => {
    if (generatedFiles.length === 0 || isApplyingEditorPatch) {
      return;
    }

    setIsApplyingEditorPatch(true);
    try {
      const patchedFiles: GeneratedFile[] = generatedFiles.map((file) => {
        const patchedContent = editorDrafts[file.name] ?? file.content;
        return {
          ...file,
          content: patchedContent,
          size: new TextEncoder().encode(patchedContent).length,
        };
      });

      setGeneratedFiles(patchedFiles);

      const indexHtml =
        patchedFiles.find((file) => file.name === 'index.html')?.content ||
        patchedFiles.find((file) => file.name.endsWith('/index.html'))?.content ||
        generatedHtml;

      if (indexHtml) {
        previewUpdateStartedAtRef.current = Date.now();
        setGeneratedHtml(indexHtml);
      }

      const mounted = await mountWorkspace({
        files: patchedFiles.map((file) => ({
          path: file.name,
          content: file.content,
          language: file.type,
        })),
        entrypoint: 'index.html',
        fallbackHtml: indexHtml,
      });

      setPreviewBridgeState(mounted ? 'pending' : 'failed');
      setEditorBridgeLastAppliedAt(Date.now());
      setEditorDrafts({});
      recordClientMetric('builder_editor_patch_apply_count', 1, {
        file_count: patchedFiles.length,
      });
    } catch (error) {
      console.error('Failed to apply editor patch to preview runtime:', error);
      setPreviewBridgeState('failed');
      recordUiError(error, 'boundary', { scope: 'builder_editor_patch_apply' });
    } finally {
      setIsApplyingEditorPatch(false);
    }
  };

  const requestPreviewRuntimeRestart = () => {
    if (!previewRuntimeBridgeChannel || !iframeRef.current?.contentWindow) {
      return;
    }

    setIsRestartingPreviewRuntime(true);
    setPreviewBridgeState('pending');
    iframeRef.current.contentWindow.postMessage(
      {
        [PREVIEW_BRIDGE_FLAG]: true,
        type: 'sovrn.preview.reload',
        channel: previewRuntimeBridgeChannel,
        timestamp: Date.now(),
      },
      '*'
    );
    recordClientMetric('builder_preview_runtime_restart_count', 1, {
      runtime_kind: previewRuntimeKind,
    });
  };

  const reconnectPreviewStream = () => {
    if (!previewBootstrapSession?.project_id || !previewBootstrapSession?.token) {
      return;
    }

    if (previewEventSourceRef.current) {
      previewEventSourceRef.current.close();
      previewEventSourceRef.current = null;
    }

    setPreviewStreamState('connecting');
    setPreviewStreamLastEventAt(null);
    setPreviewStreamReconnectNonce((previous) => previous + 1);
    recordClientMetric('builder_preview_stream_reconnect_count', 1, {
      previous_state: previewStreamState,
    });
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
    if (viewMode === 'code' && selectedGeneratedFile) {
      await navigator.clipboard.writeText(selectedFileDraftContent);
    } else {
      await navigator.clipboard.writeText(generatedHtml);
    }
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
        const resolvedContent = editorDrafts[file.name] ?? file.content;
        const blob = new Blob([resolvedContent], { type: mimeTypes[file.type] || 'text/plain' });
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
    if (previewRuntimeUrl) {
      window.open(previewRuntimeUrl, '_blank');
      return;
    }

    const blob = new Blob([generatedHtml], { type: 'text/html' });
    window.open(URL.createObjectURL(blob), '_blank');
  };

  const startNewChat = () => {
    if (previewEventSourceRef.current) {
      previewEventSourceRef.current.close();
      previewEventSourceRef.current = null;
    }

    setGeneratedHtml('');
    setGeneratedFiles([]);
    setSelectedFile('index.html');
    setMessages([]);
    setSelectedChatId(null);
    setConversationThreadId(null);
    setConversationTurnIndex(null);
    setConversationStateVersion(null);
    setPreviewBootstrapSession(null);
    setPreviewBridgeState('idle');
    setPreviewBridgeLastEventAt(null);
    setPreviewStreamState('idle');
    setPreviewStreamLastEventAt(null);
    setPreviewStreamReconnectNonce(0);
    setEditorDrafts({});
    setEditorBridgeLastAppliedAt(null);
    setIsRestartingPreviewRuntime(false);
    clearMountedWorkspace();
  };

  const streamFallbackMessage = getPreviewStreamFallbackMessage(previewStreamState);

  const isNewChat = messages.length === 0;

  return (
    <div className={`h-screen flex transition-colors duration-300 ${
      isDark ? 'bg-[#0c0c0c]' : 'bg-[#f8f9fa]'
    }`}>
      <style dangerouslySetInnerHTML={{ __html: styles }} />
      
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-[270px]' : 'w-[62px]'} flex-shrink-0 transition-all duration-300 ease-out overflow-hidden ${
        isDark ? 'bg-[#101113]' : 'bg-white'
      } border-r ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
        <div className="w-full h-full flex flex-col">
          <div className={`px-3 py-3 ${sidebarOpen ? 'space-y-1.5' : 'space-y-1'}`}>
            <button
              onClick={startNewChat}
              className={`w-full flex items-center ${sidebarOpen ? 'justify-start gap-2.5 px-2.5' : 'justify-center px-0'} h-9 rounded-lg text-sm font-medium transition-all duration-200 ${
                isDark ? 'text-white hover:bg-white/[0.08]' : 'text-black hover:bg-black/[0.06]'
              }`}
              title="New chat"
            >
              <Plus className="w-4 h-4" />
              {sidebarOpen && 'New chat'}
            </button>

            <div className={`w-full flex items-center ${sidebarOpen ? 'gap-2 px-2.5' : 'justify-center px-0'} h-9 rounded-lg transition-all duration-200 ${
              isDark ? 'text-white/85 hover:bg-white/[0.06]' : 'text-black/85 hover:bg-black/[0.04]'
            }`}>
              <Search className="w-4 h-4 flex-shrink-0" />
              {sidebarOpen && (
                <input
                  type="text"
                  placeholder="Search chats"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full min-w-0 bg-transparent border-0 ring-0 outline-none focus:outline-none focus:ring-0 focus:border-0 appearance-none text-[13px] leading-5 ${
                    isDark ? 'text-white placeholder:text-white/30' : 'text-black placeholder:text-black/35'
                  }`}
                />
              )}
            </div>

            <button
              className={`w-full flex items-center ${sidebarOpen ? 'justify-start gap-2.5 px-2.5' : 'justify-center px-0'} h-9 rounded-lg text-sm transition-all duration-200 ${
                isDark ? 'text-white/85 hover:bg-white/[0.06]' : 'text-black/85 hover:bg-black/[0.04]'
              }`}
              title="Codex"
            >
              <Bot className="w-4 h-4" />
              {sidebarOpen && 'Codex'}
            </button>

            <button
              className={`w-full flex items-center ${sidebarOpen ? 'justify-start gap-2.5 px-2.5' : 'justify-center px-0'} h-9 rounded-lg text-sm transition-all duration-200 ${
                isDark ? 'text-white/70 hover:bg-white/[0.06]' : 'text-black/70 hover:bg-black/[0.04]'
              }`}
              title="More"
            >
              <MoreHorizontal className="w-4 h-4" />
              {sidebarOpen && 'More'}
            </button>
          </div>

          {sidebarOpen && (
            <div className="px-3 pb-2 pt-1">
              <div className={`text-[12px] mb-1.5 px-2 ${isDark ? 'text-white/45' : 'text-black/45'}`}>Projects</div>
              <button
                className={`w-full flex items-center gap-2.5 px-2.5 h-9 rounded-lg text-sm transition-all duration-200 ${
                  isDark ? 'text-white/85 hover:bg-white/[0.06]' : 'text-black/85 hover:bg-black/[0.04]'
                }`}
                title="New project"
              >
                <FolderPlus className="w-4 h-4" />
                New project
              </button>

              <div className="space-y-1 mt-1.5">
                {projectCollections.map((item, idx) => (
                  <button
                    key={item.id}
                    className={`w-full flex items-center gap-2.5 px-2.5 h-8 rounded-lg text-sm transition-all duration-200 ${
                      idx === 1
                        ? isDark
                          ? 'bg-white/[0.08] text-white'
                          : 'bg-black/[0.08] text-black'
                        : isDark
                          ? 'text-white/80 hover:bg-white/[0.05]'
                          : 'text-black/80 hover:bg-black/[0.04]'
                    }`}
                    title={item.label}
                  >
                    <item.icon className={`w-4 h-4 ${item.tone}`} />
                    <span className="truncate">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className={`flex-1 overflow-y-auto ${sidebarOpen ? 'px-3 pb-3' : 'px-2 pb-2'}`}>
            {sidebarOpen && (
              <div className="space-y-3">
                {Object.entries(groupedChats).map(([groupName, chats]) => {
                  if (chats.length === 0) return null;

                  return (
                    <div key={groupName}>
                      <div className={`text-[11px] mb-1.5 px-2 ${isDark ? 'text-white/38' : 'text-black/38'}`}>
                        {groupName}
                      </div>
                      <div className="space-y-1">
                        {chats.map((chat) => (
                          <button
                            key={chat.id}
                            title={chat.title}
                            onClick={() => setSelectedChatId(chat.id)}
                            className={`w-full text-left px-2.5 py-2 rounded-lg transition-all duration-200 group ${
                              selectedChatId === chat.id
                                ? isDark
                                  ? 'bg-white/[0.10] text-white'
                                  : 'bg-black/[0.10] text-black'
                                : isDark
                                  ? 'hover:bg-white/[0.06]'
                                  : 'hover:bg-black/[0.04]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className={`text-[13px] truncate ${isDark ? 'text-white/88' : 'text-black/88'}`}>
                                {chat.title}
                              </span>
                              <MoreHorizontal className={`w-3.5 h-3.5 opacity-0 group-hover:opacity-60 transition-all ${isDark ? 'text-white/40' : 'text-black/40'}`} />
                            </div>
                            <p className={`text-[11px] truncate mt-0.5 ${isDark ? 'text-white/30' : 'text-black/30'}`}>
                              {chat.preview}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {filteredChats.length === 0 && (
                  <div className={`px-2 py-3 text-[11px] ${isDark ? 'text-white/35' : 'text-black/35'}`}>
                    No chats found.
                  </div>
                )}
              </div>
            )}
          </div>

          <div className={`p-2 border-t ${isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'}`}>
            <button
              onClick={() => setIsDark(!isDark)}
              className={`w-full flex items-center ${sidebarOpen ? 'gap-2.5 px-2.5 justify-start' : 'justify-center px-0'} h-9 rounded-lg text-sm transition-all duration-200 ${
                isDark
                  ? 'text-white/65 hover:bg-white/[0.06] hover:text-white'
                  : 'text-black/65 hover:bg-black/[0.04] hover:text-black'
              }`}
              title={isDark ? 'Light mode' : 'Dark mode'}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              {sidebarOpen && (isDark ? 'Light mode' : 'Dark mode')}
            </button>
            <button
              className={`w-full flex items-center ${sidebarOpen ? 'gap-2.5 px-2.5 justify-start' : 'justify-center px-0'} h-9 rounded-lg text-sm transition-all duration-200 ${
                isDark
                  ? 'text-white/65 hover:bg-white/[0.06] hover:text-white'
                  : 'text-black/65 hover:bg-black/[0.04] hover:text-black'
              }`}
              title="Settings"
            >
              <Settings className="w-4 h-4" />
              {sidebarOpen && 'Settings'}
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
              title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
            {!isNewChat && (
              <div className="flex flex-col leading-tight">
                <span className={`text-sm font-medium ${isDark ? 'text-white/60' : 'text-black/60'}`}>
                  New conversation
                </span>
                {FRONTEND_CONVERSATION_STATE_ENABLED && conversationThreadId && (
                  <span className={`text-[11px] ${isDark ? 'text-white/35' : 'text-black/35'}`}>
                    Compacted context synced
                    {typeof conversationTurnIndex === 'number' ? ` · turn ${conversationTurnIndex}` : ''}
                    {typeof conversationStateVersion === 'number' ? ` · v${conversationStateVersion}` : ''}
                  </span>
                )}
                {previewBootstrapSession && (
                  <span className={`text-[11px] ${isDark ? 'text-white/35' : 'text-black/35'}`}>
                    Preview token ready
                  </span>
                )}
              </div>
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
                <div className="flex-1 flex flex-col items-center justify-center px-4">
                <div className="max-w-2xl w-full">
                  {/* Greeting */}
                  <h1 className={`animate-slide-in-right text-3xl font-semibold text-center mb-2.5 ${
                    isDark ? 'text-white' : 'text-black'
                  }`}>
                    {greeting}
                  </h1>
                  <p className={`animate-slide-in-right animate-delay-100 text-base text-center mb-8 ${
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
                  <div className="animate-slide-in-right animate-delay-300 flex flex-wrap items-center justify-center gap-2 mt-6">
                    {quickActions.map((action) => (
                      <button
                        key={action.label}
                        onClick={() => handleQuickAction(action)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
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
                  <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`${message.isNew ? 'animate-fade-in-up' : ''} ${message.role === 'user' ? 'flex justify-end' : ''}`}
                      >
                        {message.role === 'assistant' ? (
                          <div className={`${
                            isDark ? 'text-white/90' : 'text-black/90'
                          }`}>
                            {!message.isTask && FRONTEND_RESOLVED_ACTION_ENABLED && message.resolvedAction && (
                              <div className="mb-2 flex flex-wrap items-center gap-2">
                                <span
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${
                                    isDark
                                      ? 'bg-white/[0.08] text-white/70 border border-white/[0.12]'
                                      : 'bg-black/[0.06] text-black/70 border border-black/[0.12]'
                                  }`}
                                >
                                  {message.resolvedAction.replace(/_/g, ' ')}
                                </span>
                                {message.actionReason && (
                                  <span className={`text-[11px] ${isDark ? 'text-white/45' : 'text-black/45'}`}>
                                    {message.actionReason.replace(/_/g, ' ')}
                                  </span>
                                )}
                              </div>
                            )}
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
                  <div className="max-w-3xl mx-auto px-4 py-3">
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
                <div className="flex items-center gap-2">
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

                  <div
                    title={`${previewRuntimeDetail}${previewBridgeLastEventAt ? ` | bridge last seen: ${new Date(previewBridgeLastEventAt).toISOString()}` : ''}${previewStreamLastEventAt ? ` | stream last seen: ${new Date(previewStreamLastEventAt).toISOString()}` : ''}`}
                    className={`px-2.5 py-1 rounded-lg text-[11px] uppercase tracking-wide border ${
                      isDark
                        ? 'border-white/[0.12] text-white/55 bg-white/[0.03]'
                        : 'border-black/[0.12] text-black/55 bg-black/[0.03]'
                    }`}
                  >
                    {previewRuntimeKind} {previewRuntimeStatus} bridge:{previewBridgeState} stream:{previewStreamState} {previewRuntimeMountedFileCount > 0 ? `(${previewRuntimeMountedFileCount} files)` : ''}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={requestPreviewRuntimeRestart}
                    disabled={!previewRuntimeBridgeChannel}
                    className={`p-2 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed ${isDark ? 'text-white/40 hover:text-white hover:bg-white/[0.06]' : 'text-black/40 hover:text-black hover:bg-black/[0.04]'}`}
                    title={previewRuntimeBridgeChannel ? 'Restart runtime' : 'Runtime bridge unavailable'}
                  >
                    <RotateCw className={`w-4 h-4 ${isRestartingPreviewRuntime ? 'animate-spin' : ''}`} />
                  </button>
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

              {streamFallbackMessage && (
                <div
                  className={`px-4 py-2 flex items-center justify-between border-b ${
                    isDark
                      ? 'border-amber-400/30 bg-amber-500/10 text-amber-100'
                      : 'border-amber-600/20 bg-amber-100 text-amber-900'
                  }`}
                >
                  <p className="text-xs leading-5">{streamFallbackMessage}</p>
                  <button
                    onClick={reconnectPreviewStream}
                    className={`ml-4 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                      isDark
                        ? 'bg-amber-300/20 hover:bg-amber-300/30 text-amber-100'
                        : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-900'
                    }`}
                  >
                    Reconnect stream
                  </button>
                </div>
              )}

              {/* Content */}
              <div className="flex-1 relative overflow-hidden">
                {viewMode === 'preview' ? (
                  <iframe
                    ref={iframeRef}
                    src={previewRuntimeUrl || undefined}
                    srcDoc={previewRuntimeUrl ? undefined : generatedHtml}
                    onLoad={() => {
                      if (previewRuntimeBridgeChannel && iframeRef.current?.contentWindow) {
                        iframeRef.current.contentWindow.postMessage(
                          {
                            [PREVIEW_BRIDGE_FLAG]: true,
                            type: 'sovrn.preview.ping',
                            channel: previewRuntimeBridgeChannel,
                            timestamp: Date.now(),
                          },
                          '*'
                        );
                      }

                      if (previewUpdateStartedAtRef.current === null) {
                        return;
                      }
                      recordClientMetric(
                        'builder_preview_render_ms',
                        Date.now() - previewUpdateStartedAtRef.current,
                        { view_mode: viewMode }
                      );
                      previewUpdateStartedAtRef.current = null;
                    }}
                    className="w-full h-full bg-white"
                    sandbox="allow-scripts"
                    title="Preview"
                  />
                ) : (
                  <div className={`h-full flex ${isDark ? 'bg-[#0a0a0a]' : 'bg-[#fafafa]'}`}>
                    <aside
                      className={`w-56 border-r ${
                        isDark ? 'border-white/[0.06] bg-[#0d0d0d]' : 'border-black/[0.06] bg-white'
                      }`}
                    >
                      <div
                        className={`px-3 py-2 text-[11px] uppercase tracking-wide border-b ${
                          isDark ? 'text-white/45 border-white/[0.06]' : 'text-black/45 border-black/[0.06]'
                        }`}
                      >
                        Workspace {draftCount > 0 ? `(${draftCount} draft${draftCount === 1 ? '' : 's'})` : ''}
                      </div>
                      <div className="h-full overflow-auto p-2 space-y-1">
                        {generatedFiles.map((file) => {
                          const hasDraft = Object.prototype.hasOwnProperty.call(editorDrafts, file.name);
                          return (
                            <button
                              key={file.name}
                              onClick={() => setSelectedFile(file.name)}
                              className={`w-full text-left px-2 py-1.5 rounded-md text-xs font-mono transition-all ${
                                selectedFile === file.name
                                  ? isDark
                                    ? 'bg-white/12 text-white'
                                    : 'bg-black/10 text-black'
                                  : isDark
                                    ? 'text-white/60 hover:text-white hover:bg-white/[0.06]'
                                    : 'text-black/60 hover:text-black hover:bg-black/[0.05]'
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="truncate">{file.name}</span>
                                {hasDraft && (
                                  <span className={`${isDark ? 'text-emerald-300/80' : 'text-emerald-700'} text-[10px]`}>●</span>
                                )}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </aside>

                    <div className="flex-1 flex flex-col min-w-0">
                      <div
                        className={`flex items-center justify-between gap-2 px-3 py-2 border-b ${
                          isDark ? 'border-white/[0.06]' : 'border-black/[0.06]'
                        }`}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <span className={`text-xs font-mono truncate ${isDark ? 'text-white/70' : 'text-black/70'}`}>
                            {selectedGeneratedFile?.name || 'index.html'}
                          </span>
                          {editorBridgeLastAppliedAt && (
                            <span className={`text-[10px] ${isDark ? 'text-white/40' : 'text-black/45'}`}>
                              last applied {new Date(editorBridgeLastAppliedAt).toLocaleTimeString()}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={discardEditorDrafts}
                            disabled={draftCount === 0 || isApplyingEditorPatch}
                            className={`px-2.5 py-1 rounded-md text-xs transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                              isDark
                                ? 'text-white/70 hover:bg-white/[0.08]'
                                : 'text-black/70 hover:bg-black/[0.06]'
                            }`}
                          >
                            Discard
                          </button>
                          <button
                            onClick={() => {
                              void applyEditorPatchToPreview();
                            }}
                            disabled={draftCount === 0 || isApplyingEditorPatch}
                            className={`px-2.5 py-1 rounded-md text-xs transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                              isDark
                                ? 'bg-white/12 text-white hover:bg-white/20'
                                : 'bg-black text-white hover:opacity-90'
                            }`}
                          >
                            {isApplyingEditorPatch ? 'Applying...' : 'Apply Patch'}
                          </button>
                        </div>
                      </div>

                      <div className="flex-1 p-3">
                        <textarea
                          value={selectedFileDraftContent}
                          onChange={(event) => {
                            if (!selectedGeneratedFile) {
                              return;
                            }
                            updateEditorDraft(selectedGeneratedFile.name, event.target.value);
                          }}
                          disabled={!selectedGeneratedFile}
                          spellCheck={false}
                          className={`w-full h-full resize-none rounded-lg border px-3 py-2 text-xs font-mono leading-relaxed focus:outline-none ${
                            isDark
                              ? 'bg-[#070707] border-white/[0.12] text-white/80 focus:border-white/30'
                              : 'bg-white border-black/[0.12] text-black/80 focus:border-black/30'
                          } disabled:opacity-50`}
                        />
                      </div>
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
