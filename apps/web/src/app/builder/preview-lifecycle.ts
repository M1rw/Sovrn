import type { PreviewArtifactResponse } from '@/lib/api';

export type PreviewStreamState =
  | 'idle'
  | 'connecting'
  | 'live'
  | 'stale'
  | 'disconnected'
  | 'error';

export interface GeneratedFile {
  name: string;
  content: string;
  type: string;
  size: number;
}

export interface PreviewStreamUpdatePayload {
  project_id: string;
  generation_id: string;
  generation_version: number;
  entrypoint: string;
  preview_html: string;
  artifact_endpoint: string;
  files: Array<{
    path: string;
    content: string;
    language?: string;
    size_bytes?: number;
  }>;
}

export interface PreviewMountDescriptor {
  mountFiles: Array<{
    path: string;
    content: string;
    language?: string;
  }>;
  generatedFiles: GeneratedFile[];
  entrypoint: string;
  fallbackHtml?: string;
  nextGeneratedHtml: string;
}

const DEFAULT_ENTRYPOINT = 'index.html';

function inferFileTypeFromPath(filePath: string): string {
  const extension = filePath.split('.').pop()?.toLowerCase() || 'txt';
  if (extension === 'js') {
    return 'javascript';
  }
  return extension;
}

function utf8Size(value: string): number {
  return Buffer.byteLength(value, 'utf8');
}

function normalizePreviewFiles(
  files: unknown,
  fallbackPrefix: string
): GeneratedFile[] {
  if (!Array.isArray(files)) {
    return [];
  }

  return files.map((file, index) => {
    const entry = typeof file === 'object' && file !== null
      ? (file as {
          path?: unknown;
          content?: unknown;
          language?: unknown;
          size_bytes?: unknown;
        })
      : {};

    const path =
      typeof entry.path === 'string' && entry.path.trim()
        ? entry.path
        : `${fallbackPrefix}-${index}.txt`;
    const content = typeof entry.content === 'string' ? entry.content : '';
    const type =
      typeof entry.language === 'string' && entry.language.trim()
        ? entry.language
        : inferFileTypeFromPath(path);
    const size =
      typeof entry.size_bytes === 'number' && Number.isFinite(entry.size_bytes)
        ? entry.size_bytes
        : utf8Size(content);

    return {
      name: path,
      content,
      type,
      size,
    };
  });
}

function buildDescriptor(
  generatedFiles: GeneratedFile[],
  entrypoint: string,
  htmlCandidate: string,
  htmlFallback?: string
): PreviewMountDescriptor {
  const normalizedEntrypoint = entrypoint.trim() || DEFAULT_ENTRYPOINT;
  const nextGeneratedHtml =
    typeof htmlCandidate === 'string' && htmlCandidate.trim()
      ? htmlCandidate
      : htmlFallback || '';

  return {
    mountFiles: generatedFiles.map((file) => ({
      path: file.name,
      content: file.content,
      language: file.type,
    })),
    generatedFiles,
    entrypoint: normalizedEntrypoint,
    fallbackHtml: nextGeneratedHtml.trim() ? nextGeneratedHtml : undefined,
    nextGeneratedHtml,
  };
}

export function toMountDescriptorFromArtifact(
  artifact: PreviewArtifactResponse,
  entrypoint: string,
  generatedHtmlFallback?: string
): PreviewMountDescriptor {
  const generatedFiles = normalizePreviewFiles(artifact.files, 'artifact-file');
  return buildDescriptor(
    generatedFiles,
    entrypoint,
    artifact.preview_html,
    generatedHtmlFallback
  );
}

export function toMountDescriptorFromPreviewUpdate(
  payload: unknown
): PreviewMountDescriptor {
  const update = (payload || {}) as Partial<PreviewStreamUpdatePayload>;
  const generatedFiles = normalizePreviewFiles(update.files, 'stream-file');

  return buildDescriptor(
    generatedFiles,
    typeof update.entrypoint === 'string' ? update.entrypoint : DEFAULT_ENTRYPOINT,
    typeof update.preview_html === 'string' ? update.preview_html : ''
  );
}

export function getPreviewStreamStateOnError(
  eventSourceReadyState: number
): PreviewStreamState {
  // EventSource.CLOSED is 2 in browser environments.
  return eventSourceReadyState === 2 ? 'disconnected' : 'error';
}

export function shouldMarkPreviewStreamStale(
  lastEventAt: number | null,
  now: number,
  staleThresholdMs: number
): boolean {
  if (lastEventAt === null) {
    return false;
  }

  return now - lastEventAt >= staleThresholdMs;
}

export function getPreviewStreamFallbackMessage(
  state: PreviewStreamState
): string | null {
  if (state === 'stale') {
    return 'Live preview stream is stale. New updates may be delayed.';
  }
  if (state === 'disconnected') {
    return 'Live preview stream disconnected. Reconnect to resume incremental updates.';
  }
  if (state === 'error') {
    return 'Live preview stream encountered an error. Reconnect to recover updates.';
  }
  return null;
}
