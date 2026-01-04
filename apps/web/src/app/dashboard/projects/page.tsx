import { Metadata } from 'next';
import { getServerSession } from 'next-auth';
import Link from 'next/link';
import { authOptions } from '@/lib/auth';
import { projectsApi } from '@/lib/api';
import { Plus, Search, Filter } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'Projects',
};

interface ProjectsPageProps {
  searchParams: { page?: string; status?: string; search?: string };
}

export default async function ProjectsPage({ searchParams }: ProjectsPageProps) {
  const session = await getServerSession(authOptions);
  const page = parseInt(searchParams.page || '1');
  const status = searchParams.status;

  let projectsData;
  try {
    projectsData = await projectsApi.list(session!.accessToken, { page, status });
  } catch {
    projectsData = { items: [], total: 0, page: 1, page_size: 10, pages: 0 };
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage and generate your AI-powered websites
          </p>
        </div>
        <Link
          href="/dashboard/projects/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search projects..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <div className="flex gap-2">
          <select
            defaultValue={status || ''}
            className="px-3 py-2 rounded-lg border bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">All Status</option>
            <option value="draft">Draft</option>
            <option value="generating">Generating</option>
            <option value="generated">Generated</option>
            <option value="deployed">Deployed</option>
          </select>
          <button className="px-3 py-2 rounded-lg border bg-background hover:bg-muted transition">
            <Filter className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Projects Grid */}
      {projectsData.items.length === 0 ? (
        <div className="rounded-xl border border-dashed p-12 text-center">
          <h3 className="font-semibold">No projects found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Create your first project to get started
          </p>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
          >
            <Plus className="h-4 w-4" />
            Create Project
          </Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projectsData.items.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {projectsData.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {page > 1 && (
            <Link
              href={`/dashboard/projects?page=${page - 1}${status ? `&status=${status}` : ''}`}
              className="px-3 py-1 rounded border hover:bg-muted transition text-sm"
            >
              Previous
            </Link>
          )}
          <span className="text-sm text-muted-foreground">
            Page {page} of {projectsData.pages}
          </span>
          {page < projectsData.pages && (
            <Link
              href={`/dashboard/projects?page=${page + 1}${status ? `&status=${status}` : ''}`}
              className="px-3 py-1 rounded border hover:bg-muted transition text-sm"
            >
              Next
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project }: { project: any }) {
  const statusConfig = {
    draft: { color: 'bg-gray-500', label: 'Draft' },
    generating: { color: 'bg-yellow-500 animate-pulse', label: 'Generating' },
    generated: { color: 'bg-green-500', label: 'Ready' },
    deployed: { color: 'bg-blue-500', label: 'Deployed' },
    failed: { color: 'bg-red-500', label: 'Failed' },
  };

  const status = statusConfig[project.status as keyof typeof statusConfig] || statusConfig.draft;

  return (
    <Link
      href={`/dashboard/projects/${project.id}`}
      className="group rounded-xl border bg-card p-5 hover:shadow-md transition"
    >
      <div className="flex items-start justify-between">
        <h3 className="font-semibold group-hover:text-primary transition truncate">
          {project.name}
        </h3>
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
            project.status === 'deployed' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
            project.status === 'generated' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
            project.status === 'generating' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
            project.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
            'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${status.color}`} />
          {status.label}
        </span>
      </div>

      {project.description && (
        <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
          {project.description}
        </p>
      )}

      <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
        <span>{formatRelativeTime(project.updated_at)}</span>
        {project.locale && (
          <>
            <span>•</span>
            <span className="uppercase">{project.locale}</span>
          </>
        )}
        {project.industry && (
          <>
            <span>•</span>
            <span className="capitalize">{project.industry}</span>
          </>
        )}
      </div>
    </Link>
  );
}
