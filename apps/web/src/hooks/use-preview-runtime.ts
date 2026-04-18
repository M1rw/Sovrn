'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const WEB_CONTAINER_ENV_ENABLED =
  process.env.NEXT_PUBLIC_BUILDER_WEBCONTAINER_ENABLED === 'true';

const PREVIEW_BRIDGE_FLAG = '__sovrnPreviewBridge';

function createPreviewBridgeChannel(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `preview-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

export function buildBridgeScript(channel: string): string {
  const payloadFlag = JSON.stringify(PREVIEW_BRIDGE_FLAG);
  const payloadChannel = JSON.stringify(channel);

  return `<script>(function(){const FLAG=${payloadFlag};const CHANNEL=${payloadChannel};const safePost=(type,extra)=>{try{window.parent.postMessage(Object.assign({[FLAG]:true,type,channel:CHANNEL,timestamp:Date.now()},extra||{}),'*');}catch(_err){}};const normalizeText=(value)=>String(value||'').replace(/\s+/g,' ').trim();const extractClasses=(target)=>{if(typeof target.className!=='string'){return [];}return target.className.split(/\s+/).map((entry)=>entry.trim()).filter(Boolean).slice(0,8);};const toNodePayload=(target)=>{const nearestSource=target.closest('[data-source-path]');const sourcePath=target.getAttribute('data-source-path')||(nearestSource&&nearestSource.getAttribute('data-source-path'))||undefined;const textSnippet=normalizeText(target.textContent).slice(0,160);return{tagName:String(target.tagName||'').toLowerCase(),id:target.id||undefined,classes:extractClasses(target),textSnippet:textSnippet||undefined,sourcePath};};window.addEventListener('message',(event)=>{const data=event.data;if(!data||typeof data!=='object'){return;}if(data[FLAG]!==true||data.channel!==CHANNEL){return;}if(data.type==='sovrn.preview.ping'){safePost('sovrn.preview.pong');}if(data.type==='sovrn.preview.reload'){window.location.reload();}},false);window.addEventListener('click',(event)=>{const target=event.target;if(!(target instanceof Element)){return;}safePost('sovrn.preview.node.select',{node:toNodePayload(target)});},true);safePost('sovrn.preview.ready',{location:window.location.href});})();</script>`;
}

export function injectBridgeScript(html: string, channel: string): string {
  const bridgeScript = buildBridgeScript(channel);

  if (/<\/body>/i.test(html)) {
    return html.replace(/<\/body>/i, `${bridgeScript}</body>`);
  }

  if (/<\/html>/i.test(html)) {
    return html.replace(/<\/html>/i, `${bridgeScript}</html>`);
  }

  return `<!doctype html><html><head><meta charset="utf-8" /></head><body>${html}${bridgeScript}</body></html>`;
}

export type PreviewRuntimeKind = 'iframe' | 'webcontainer';
export type PreviewRuntimeStatus = 'idle' | 'booting' | 'mounting' | 'ready' | 'failed';

export interface PreviewRuntimeFile {
  path: string;
  content: string;
  language?: string;
}

export interface MountWorkspaceRequest {
  files: PreviewRuntimeFile[];
  entrypoint?: string;
  fallbackHtml?: string;
}

export interface PreviewRuntimeState {
  kind: PreviewRuntimeKind;
  status: PreviewRuntimeStatus;
  detail: string;
  previewUrl: string | null;
  bridgeChannel: string | null;
  mountedFileCount: number;
  mountedAt: string | null;
}

export interface UsePreviewRuntimeResult extends PreviewRuntimeState {
  boot: () => Promise<void>;
  mountWorkspace: (request: MountWorkspaceRequest) => Promise<boolean>;
  clearMountedWorkspace: () => void;
}

export function usePreviewRuntime(): UsePreviewRuntimeResult {
  const [kind, setKind] = useState<PreviewRuntimeKind>('iframe');
  const [status, setStatus] = useState<PreviewRuntimeStatus>('idle');
  const [detail, setDetail] = useState('Runtime is idle.');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [bridgeChannel, setBridgeChannel] = useState<string | null>(null);
  const [mountedFileCount, setMountedFileCount] = useState(0);
  const [mountedAt, setMountedAt] = useState<string | null>(null);

  const runtimeBootedRef = useRef(false);
  const currentBlobUrlRef = useRef<string | null>(null);

  const revokeCurrentBlobUrl = useCallback(() => {
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current);
      currentBlobUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      revokeCurrentBlobUrl();
    };
  }, [revokeCurrentBlobUrl]);

  const boot = useCallback(async () => {
    if (runtimeBootedRef.current) {
      if (status === 'idle') {
        setStatus('ready');
      }
      return;
    }

    runtimeBootedRef.current = true;
    setStatus('booting');
    setDetail('Booting preview runtime...');

    if (!WEB_CONTAINER_ENV_ENABLED) {
      setKind('iframe');
      setStatus('ready');
      setDetail('Iframe runtime ready. Set NEXT_PUBLIC_BUILDER_WEBCONTAINER_ENABLED=true to probe WebContainer support.');
      return;
    }

    try {
      const moduleName = '@webcontainer/api';
      const imported = await import(moduleName);
      const hasWebContainerApi =
        typeof imported === 'object' && imported !== null && 'WebContainer' in imported;

      if (hasWebContainerApi) {
        setKind('webcontainer');
        setStatus('ready');
        setDetail('WebContainer API discovered. Runtime boot lifecycle initialized.');
        return;
      }

      setKind('iframe');
      setStatus('ready');
      setDetail('WebContainer package loaded without runtime export. Using iframe runtime fallback.');
    } catch {
      setKind('iframe');
      setStatus('ready');
      setDetail('WebContainer runtime unavailable. Using iframe runtime fallback.');
    }
  }, [status]);

  const mountWorkspace = useCallback(
    async (request: MountWorkspaceRequest): Promise<boolean> => {
      const files = Array.isArray(request.files) ? request.files : [];
      const entrypoint = request.entrypoint?.trim() || 'index.html';

      setStatus('mounting');
      setDetail(`Mounting ${files.length} file${files.length === 1 ? '' : 's'} to preview runtime...`);
      setMountedFileCount(files.length);

      const exactMatch = files.find((file) => file.path === entrypoint);
      const indexMatch = files.find((file) => file.path.endsWith('/index.html'));
      const rootIndex = files.find((file) => file.path === 'index.html');
      const htmlSource = exactMatch?.content || rootIndex?.content || indexMatch?.content || request.fallbackHtml;

      if (!htmlSource || !htmlSource.trim()) {
        setStatus('failed');
        setDetail(`Preview mount failed: no HTML content found for entrypoint \"${entrypoint}\".`);
        return false;
      }

      const nextBridgeChannel = createPreviewBridgeChannel();
      const htmlWithBridge = injectBridgeScript(htmlSource, nextBridgeChannel);

      revokeCurrentBlobUrl();
      const nextPreviewUrl = URL.createObjectURL(new Blob([htmlWithBridge], { type: 'text/html' }));
      currentBlobUrlRef.current = nextPreviewUrl;
      setPreviewUrl(nextPreviewUrl);
      setBridgeChannel(nextBridgeChannel);
      setMountedAt(new Date().toISOString());
      setStatus('ready');
      setDetail(
        kind === 'webcontainer'
          ? `Workspace mounted (${files.length} files). Preview bridge is serving entrypoint \"${entrypoint}\".`
          : `Workspace mounted (${files.length} files) with iframe runtime.`
      );

      return true;
    },
    [kind, revokeCurrentBlobUrl]
  );

  const clearMountedWorkspace = useCallback(() => {
    revokeCurrentBlobUrl();
    setPreviewUrl(null);
    setBridgeChannel(null);
    setMountedFileCount(0);
    setMountedAt(null);
    if (status !== 'failed') {
      setStatus(runtimeBootedRef.current ? 'ready' : 'idle');
      setDetail(runtimeBootedRef.current ? 'Runtime ready for the next workspace mount.' : 'Runtime is idle.');
    }
  }, [revokeCurrentBlobUrl, status]);

  return {
    kind,
    status,
    detail,
    previewUrl,
    bridgeChannel,
    mountedFileCount,
    mountedAt,
    boot,
    mountWorkspace,
    clearMountedWorkspace,
  };
}
