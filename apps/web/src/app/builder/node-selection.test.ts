import {
  mapPreviewNodeSelectionToGeneratedFiles,
  parsePreviewNodeSelection,
} from './node-selection';
import type { GeneratedFile } from './preview-lifecycle';

function file(name: string, content: string, type = 'html'): GeneratedFile {
  return {
    name,
    content,
    type,
    size: Buffer.byteLength(content, 'utf8'),
  };
}

describe('parsePreviewNodeSelection', () => {
  it('normalizes tag name, classes, and text snippet', () => {
    const parsed = parsePreviewNodeSelection({
      tagName: '  DIV ',
      id: ' hero ',
      classes: [' Hero ', '', 'CTA'],
      textSnippet: '  Build    Offline   Websites  ',
      sourcePath: './index.html',
    });

    expect(parsed).toEqual({
      tagName: 'div',
      id: 'hero',
      classes: ['hero', 'cta'],
      textSnippet: 'Build Offline Websites',
      sourcePath: 'index.html',
    });
  });

  it('returns null for invalid payload', () => {
    expect(parsePreviewNodeSelection(null)).toBeNull();
    expect(parsePreviewNodeSelection({ id: 'missing-tag-name' })).toBeNull();
  });
});

describe('mapPreviewNodeSelectionToGeneratedFiles', () => {
  it('prefers direct source path matches when present', () => {
    const files = [
      file('index.html', '<div>fallback</div>'),
      file(
        'src/components/Hero.tsx',
        [
          'export function Hero() {',
          '  return (',
          '    <button className="cta">Start free trial</button>',
          '  );',
          '}',
        ].join('\n'),
        'tsx'
      ),
    ];

    const selection = parsePreviewNodeSelection({
      tagName: 'button',
      sourcePath: 'src/components/Hero.tsx',
      textSnippet: 'Start free trial',
      classes: ['cta'],
    });

    expect(selection).not.toBeNull();
    const mapped = mapPreviewNodeSelectionToGeneratedFiles(selection!, files);

    expect(mapped).toEqual(
      expect.objectContaining({
        fileName: 'src/components/Hero.tsx',
        line: 3,
        score: 100,
        reason: 'source-path',
      })
    );
  });

  it('uses heuristic scoring when source path is unavailable', () => {
    const files = [
      file(
        'index.html',
        [
          '<main>',
          '  <section id="hero" class="hero shell">',
          '    <h1>Build offline websites</h1>',
          '  </section>',
          '</main>',
        ].join('\n')
      ),
      file('styles.css', '.hero { color: red; }', 'css'),
    ];

    const selection = parsePreviewNodeSelection({
      tagName: 'section',
      id: 'hero',
      classes: ['hero'],
      textSnippet: 'Build offline websites',
    });

    expect(selection).not.toBeNull();
    const mapped = mapPreviewNodeSelectionToGeneratedFiles(selection!, files);

    expect(mapped).toEqual(
      expect.objectContaining({
        fileName: 'index.html',
        line: 2,
      })
    );
    expect(mapped?.score).toBeGreaterThan(20);
    expect(mapped?.reason).toContain('id-attr');
  });

  it('returns null when there is no probable match', () => {
    const files = [file('index.html', '<div>Unrelated content</div>')];

    const selection = parsePreviewNodeSelection({
      tagName: 'button',
      classes: ['purchase-now'],
      textSnippet: 'Buy now',
    });

    expect(selection).not.toBeNull();
    expect(mapPreviewNodeSelectionToGeneratedFiles(selection!, files)).toBeNull();
  });
});
