import Link from 'next/link';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { projectsApi, sparksApi } from '@/lib/api';
import { Plus, ArrowRight, Sparkles, FolderOpen, Zap } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

async function getProjects(token: string) {
  try {
    return await projectsApi.list(token, { page: 1 });
  } catch {
    return { items: [], total: 0, page: 1, page_size: 10, pages: 0 };
  }
}

async function getBalance(token: string) {
  try {
    return await sparksApi.getBalance(token);
  } catch {
    return { sparks_balance: 0, sparks_used_total: 0 };
  }
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  const [projectsData, balance] = await Promise.all([
    getProjects(session!.accessToken),
    getBalance(session!.accessToken),
  ]);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Welcome Banner */}
      <div className="rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border p-6">
        <h1 className="text-2xl font-bold">
          Welcome back{session?.user.name ? `, ${session.user.name}` : ''}!
        </h1>
        <p className="text-muted-foreground mt-1">
          Build something amazing today with AI-powered website generation.
        </p>
        <div className="mt-4 flex items-center gap-4">
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition"
          >
            <Plus className="h-4 w-4" />
            New Project
          </Link>
          <Link
            href="/dashboard/sparks"
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition"
          >
            <Sparkles className="h-4 w-4" />
            {balance.sparks_balance} Sparks Available
          </Link>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard
          icon={<FolderOpen className="h-5 w-5" />}
          label="Total Projects"
          value={projectsData.total.toString()}
        />
        <StatCard
          icon={<Sparkles className="h-5 w-5" />}
          label="Sparks Balance"
          value={balance.sparks_balance.toString()}
        />
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Sparks Used"
          value={balance.sparks_used_total.toString()}
        />
      </div>

      {/* Recent Projects */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Projects</h2>
          <Link
            href="/dashboard/projects"
            className="text-sm text-primary hover:underline inline-flex items-center gap-1"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {projectsData.items.length === 0 ? (
          <div className="rounded-xl border border-dashed p-12 text-center">
            <FolderOpen className="h-12 w-12 mx-auto text-muted-foreground/50" />
            <h3 className="mt-4 font-semibold">No projects yet</h3>
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
            {projectsData.items.slice(0, 6).map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2 text-primary">{icon}</div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  );
}

function ProjectCard({ project }: { project: any }) {
  const statusColors = {
    draft: 'bg-gray-500',
    generating: 'bg-yellow-500 animate-pulse',
    generated: 'bg-green-500',
    deployed: 'bg-blue-500',
    failed: 'bg-red-500',
  };

  return (
    <Link
      href={`/dashboard/projects/${project.id}`}
      className="group rounded-xl border bg-card p-4 hover:shadow-md transition"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium truncate group-hover:text-primary transition">
            {project.name}
          </h3>
          {project.description && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {project.description}
            </p>
          )}
        </div>
        <div
          className={`w-2 h-2 rounded-full ml-2 mt-1.5 ${
            statusColors[project.status as keyof typeof statusColors] || 'bg-gray-500'
          }`}
        />
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
        <span>{formatRelativeTime(project.updated_at)}</span>
        {project.locale && (
          <>
            <span>•</span>
            <span>{project.locale}</span>
          </>
        )}
      </div>
    </Link>
  );
}
