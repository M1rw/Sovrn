import type { GeneratedFile } from './preview-lifecycle';

const MAX_TEXT_SNIPPET_LENGTH = 160;
const MAX_CLASS_COUNT = 8;

export interface PreviewNodeSelection {
  tagName: string;
  id?: string;
  classes: string[];
  textSnippet?: string;
  sourcePath?: string;
}

export interface PreviewNodeSourceMatch {
  fileName: string;
  line: number;
  score: number;
  reason: string;
}

interface FileMatchCandidate {
  fileName: string;
  score: number;
  anchorIndex: number;
  reasons: string[];
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

function sanitizeToken(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function toLineNumber(content: string, index: number): number {
  if (index <= 0) {
    return 1;
  }

  let line = 1;
  for (let cursor = 0; cursor < Math.min(index, content.length); cursor += 1) {
    if (content[cursor] === '\n') {
      line += 1;
    }
  }

  return line;
}

function scoreFileAgainstSelection(
  file: GeneratedFile,
  selection: PreviewNodeSelection
): FileMatchCandidate | null {
  const content = file.content;
  const lowerContent = content.toLowerCase();

  let score = 0;
  let anchorIndex = -1;
  const reasons: string[] = [];

  const anchor = (index: number) => {
    if (index >= 0 && (anchorIndex < 0 || index < anchorIndex)) {
      anchorIndex = index;
    }
  };

  if (selection.id) {
    const idTokens = [`id=\"${selection.id}\"`, `id='${selection.id}'`, `#${selection.id}`];
    for (const token of idTokens) {
      const index = lowerContent.indexOf(token.toLowerCase());
      if (index >= 0) {
        score += token.startsWith('#') ? 8 : 14;
        reasons.push(token.startsWith('#') ? 'id-selector' : 'id-attr');
        anchor(index);
      }
    }
  }

  for (const className of selection.classes) {
    const classTokens = [
      `class=\"${className}`,
      `class='${className}`,
      ` ${className} `,
      `.${className}`,
    ];

    for (const token of classTokens) {
      const index = lowerContent.indexOf(token.toLowerCase());
      if (index >= 0) {
        score += token.startsWith('.') ? 5 : 4;
        reasons.push(token.startsWith('.') ? 'class-selector' : 'class-token');
        anchor(index);
      }
    }
  }

  if (selection.textSnippet && selection.textSnippet.length >= 4) {
    const textIndex = lowerContent.indexOf(selection.textSnippet.toLowerCase());
    if (textIndex >= 0) {
      score += 10;
      reasons.push('text-snippet');
      anchor(textIndex);
    }
  }

  if (selection.tagName) {
    const tagToken = `<${selection.tagName}`;
    const tagIndex = lowerContent.indexOf(tagToken);
    if (tagIndex >= 0) {
      score += 2;
      reasons.push('tag');
      anchor(tagIndex);
    }
  }

  if (score <= 0) {
    return null;
  }

  return {
    fileName: file.name,
    score,
    anchorIndex,
    reasons,
  };
}

export function parsePreviewNodeSelection(value: unknown): PreviewNodeSelection | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const raw = value as {
    tagName?: unknown;
    id?: unknown;
    classes?: unknown;
    textSnippet?: unknown;
    sourcePath?: unknown;
  };

  const tagName = sanitizeToken(raw.tagName)?.toLowerCase();
  if (!tagName) {
    return null;
  }

  const id = sanitizeToken(raw.id);
  const sourcePath = sanitizeToken(raw.sourcePath)?.replace(/^\.\//, '');
  const textSnippet = sanitizeToken(raw.textSnippet)
    ? normalizeWhitespace(String(raw.textSnippet)).slice(0, MAX_TEXT_SNIPPET_LENGTH)
    : undefined;

  const rawClasses = Array.isArray(raw.classes) ? raw.classes : [];
  const classes = rawClasses
    .map((entry) => sanitizeToken(entry))
    .filter((entry): entry is string => Boolean(entry))
    .map((entry) => entry.toLowerCase())
    .slice(0, MAX_CLASS_COUNT);

  return {
    tagName,
    id,
    classes,
    textSnippet,
    sourcePath,
  };
}

export function mapPreviewNodeSelectionToGeneratedFiles(
  selection: PreviewNodeSelection,
  generatedFiles: GeneratedFile[]
): PreviewNodeSourceMatch | null {
  if (generatedFiles.length === 0) {
    return null;
  }

  if (selection.sourcePath) {
    const directMatch = generatedFiles.find(
      (file) =>
        file.name === selection.sourcePath ||
        file.name.endsWith(`/${selection.sourcePath}`)
    );

    if (directMatch) {
      const anchorToken = selection.textSnippet || (selection.id ? `id=\"${selection.id}\"` : '');
      const anchorIndex = anchorToken
        ? directMatch.content.toLowerCase().indexOf(anchorToken.toLowerCase())
        : 0;
      return {
        fileName: directMatch.name,
        line: toLineNumber(directMatch.content, anchorIndex >= 0 ? anchorIndex : 0),
        score: 100,
        reason: 'source-path',
      };
    }
  }

  let bestCandidate: FileMatchCandidate | null = null;
  for (const file of generatedFiles) {
    const candidate = scoreFileAgainstSelection(file, selection);
    if (!candidate) {
      continue;
    }

    if (
      !bestCandidate ||
      candidate.score > bestCandidate.score ||
      (candidate.score === bestCandidate.score && candidate.anchorIndex < bestCandidate.anchorIndex)
    ) {
      bestCandidate = candidate;
    }
  }

  if (!bestCandidate) {
    return null;
  }

  const file = generatedFiles.find((entry) => entry.name === bestCandidate.fileName);
  if (!file) {
    return null;
  }

  return {
    fileName: bestCandidate.fileName,
    line: toLineNumber(file.content, bestCandidate.anchorIndex >= 0 ? bestCandidate.anchorIndex : 0),
    score: bestCandidate.score,
    reason: bestCandidate.reasons.join(','),
  };
}