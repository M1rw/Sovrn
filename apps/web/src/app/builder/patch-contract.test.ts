import {
  applyEditorDraftsToGeneratedFiles,
  buildPatchContractRequestFromDrafts,
} from './patch-contract';
import type { GeneratedFile } from './preview-lifecycle';

describe('patch contract helpers', () => {
  const generatedFiles: GeneratedFile[] = [
    {
      name: 'index.html',
      content: '<html><body>before</body></html>',
      type: 'html',
      size: 32,
    },
    {
      name: 'src/app/page.tsx',
      content: 'export default function Page() { return null; }\n',
      type: 'tsx',
      size: 46,
    },
    {
      name: 'README.md',
      content: '# title\n',
      type: 'md',
      size: 8,
    },
  ];

  it('builds a patch-contract request with changed files only', () => {
    const request = buildPatchContractRequestFromDrafts({
      generatedFiles,
      editorDrafts: {
        'index.html': '<html><body>after</body></html>',
        'src/app/page.tsx': 'export default function Page() { return <main />; }\n',
      },
      projectId: 'project-123',
      generationId: 'generation-456',
    });

    expect(request).not.toBeNull();
    expect(request?.version).toBe('1.0');
    expect(request?.project_id).toBe('project-123');
    expect(request?.generation_id).toBe('generation-456');
    expect(request?.fallback_mode).toBe('safe_rewrite');
    expect(request?.operations).toHaveLength(2);

    expect(request?.operations[0]).toEqual({
      op: 'replace_file',
      path: 'index.html',
      language: 'html',
      content: '<html><body>after</body></html>',
    });

    expect(request?.operations[1]).toEqual({
      op: 'replace_file',
      path: 'src/app/page.tsx',
      language: 'tsx',
      content: 'export default function Page() { return <main />; }\n',
    });
  });

  it('returns null when there are no draft changes', () => {
    const request = buildPatchContractRequestFromDrafts({
      generatedFiles,
      editorDrafts: {
        'index.html': '<html><body>before</body></html>',
      },
      projectId: 'project-123',
    });

    expect(request).toBeNull();
  });

  it('maps unknown extensions to undefined language', () => {
    const request = buildPatchContractRequestFromDrafts({
      generatedFiles,
      editorDrafts: {
        'README.md': '# updated\n',
      },
      projectId: 'project-123',
    });

    expect(request).not.toBeNull();
    expect(request?.operations).toHaveLength(1);
    expect(request?.operations[0].path).toBe('README.md');
    expect(request?.operations[0].language).toBeUndefined();
  });

  it('applies draft content and recalculates file byte size', () => {
    const patched = applyEditorDraftsToGeneratedFiles(generatedFiles, {
      'src/app/page.tsx': 'export default function Page() { return <main>hello</main>; }\n',
    });

    expect(patched).toHaveLength(3);
    expect(patched[0]).toEqual(generatedFiles[0]);
    expect(patched[2]).toEqual(generatedFiles[2]);

    expect(patched[1].content).toBe('export default function Page() { return <main>hello</main>; }\n');
    expect(patched[1].size).toBe(
      new TextEncoder().encode('export default function Page() { return <main>hello</main>; }\n').length
    );
  });
});
