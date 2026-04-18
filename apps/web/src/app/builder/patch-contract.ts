import type {
  PatchContractLanguage,
  PatchContractOperationData,
  PatchContractRequestData,
} from '@/lib/api';
import type { GeneratedFile } from './preview-lifecycle';

const FALLBACK_MODE: NonNullable<PatchContractRequestData['fallback_mode']> = 'safe_rewrite';
const textEncoder = new TextEncoder();

function inferPatchLanguageFromPath(filePath: string): PatchContractLanguage | undefined {
  const extension = filePath.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
    case 'json':
    case 'css':
    case 'html':
      return extension;
    case 'htm':
      return 'html';
    default:
      return undefined;
  }
}

function createReplaceFileOperation(
  filePath: string,
  content: string
): PatchContractOperationData {
  return {
    op: 'replace_file',
    path: filePath,
    language: inferPatchLanguageFromPath(filePath),
    content,
  };
}

export function applyEditorDraftsToGeneratedFiles(
  generatedFiles: GeneratedFile[],
  editorDrafts: Record<string, string>
): GeneratedFile[] {
  return generatedFiles.map((file) => {
    const draftContent = editorDrafts[file.name];
    if (draftContent === undefined || draftContent === file.content) {
      return file;
    }

    return {
      ...file,
      content: draftContent,
      size: textEncoder.encode(draftContent).length,
    };
  });
}

export function buildPatchContractRequestFromDrafts(params: {
  generatedFiles: GeneratedFile[];
  editorDrafts: Record<string, string>;
  projectId?: string;
  generationId?: string;
}): PatchContractRequestData | null {
  const { generatedFiles, editorDrafts, projectId, generationId } = params;

  const operations: PatchContractOperationData[] = [];

  for (const file of generatedFiles) {
    const draftContent = editorDrafts[file.name];
    if (draftContent === undefined || draftContent === file.content) {
      continue;
    }

    operations.push(createReplaceFileOperation(file.name, draftContent));
  }

  if (operations.length === 0) {
    return null;
  }

  return {
    version: '1.0',
    project_id: projectId,
    generation_id: generationId,
    fallback_mode: FALLBACK_MODE,
    operations,
  };
}
