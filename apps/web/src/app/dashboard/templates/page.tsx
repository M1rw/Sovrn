import { Metadata } from 'next';
import Link from 'next/link';
import { templatesApi } from '@/lib/api';
import { Search, Filter, Star } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Templates',
};

interface TemplatesPageProps {
  searchParams: { category?: string; industry?: string; page?: string };
}

export default async function TemplatesPage({ searchParams }: TemplatesPageProps) {
  let templates;
  let categories: string[] = [];
  let industries: string[] = [];

  try {
    [templates, categories, industries] = await Promise.all([
      templatesApi.list({
        page: parseInt(searchParams.page || '1'),
        category: searchParams.category,
        industry: searchParams.industry,
      }),
      templatesApi.categories(),
      templatesApi.industries(),
    ]);
  } catch {
    templates = { items: [], total: 0, page: 1, page_size: 12, pages: 0 };
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Templates</h1>
        <p className="text-muted-foreground">
          Start with a professional template and customize it with AI
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search templates..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <select
          defaultValue={searchParams.category || ''}
          className="px-3 py-2 rounded-lg border bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
        <select
          defaultValue={searchParams.industry || ''}
          className="px-3 py-2 rounded-lg border bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All Industries</option>
          {industries.map((ind) => (
            <option key={ind} value={ind}>
              {ind}
            </option>
          ))}
        </select>
      </div>

      {/* Templates Grid */}
      {templates.items.length === 0 ? (
        <div className="rounded-xl border border-dashed p-12 text-center">
          <h3 className="font-semibold">No templates found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Try adjusting your filters or check back later
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.items.map((template) => (
            <TemplateCard key={template.id} template={template} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {templates.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <span className="text-sm text-muted-foreground">
            Page {templates.page} of {templates.pages}
          </span>
        </div>
      )}

      {/* CTA */}
      <div className="rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border p-6 text-center">
        <h3 className="font-semibold text-lg">Can't find what you need?</h3>
        <p className="text-muted-foreground mt-1">
          Just describe your website and our AI will generate it from scratch
        </p>
        <Link
          href="/dashboard/projects/new"
          className="inline-flex items-center gap-2 mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
        >
          Create with AI
        </Link>
      </div>
    </div>
  );
}

function TemplateCard({ template }: { template: any }) {
  return (
    <div className="group rounded-xl border bg-card overflow-hidden hover:shadow-lg transition">
      <div className="aspect-video bg-muted relative">
        {template.thumbnail_url ? (
          <img
            src={template.thumbnail_url}
            alt={template.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            No preview
          </div>
        )}
        {template.is_premium && (
          <span className="absolute top-2 right-2 inline-flex items-center gap-1 bg-yellow-500 text-yellow-950 px-2 py-0.5 rounded text-xs font-medium">
            <Star className="h-3 w-3" />
            Premium
          </span>
        )}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-2">
          <Link
            href={template.preview_url || '#'}
            className="px-4 py-2 rounded-md bg-white text-black text-sm font-medium hover:bg-white/90 transition"
          >
            Preview
          </Link>
          <Link
            href={`/dashboard/projects/new?template=${template.id}`}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition"
          >
            Use Template
          </Link>
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-semibold">{template.name}</h3>
        {template.description && (
          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
            {template.description}
          </p>
        )}
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          {template.category && (
            <span className="px-2 py-0.5 rounded bg-muted">{template.category}</span>
          )}
          {template.industry && (
            <span className="px-2 py-0.5 rounded bg-muted">{template.industry}</span>
          )}
        </div>
      </div>
    </div>
  );
}
