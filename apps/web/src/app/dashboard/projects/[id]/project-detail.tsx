'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ExternalLink,
  Download,
  RefreshCw,
  Trash2,
  Settings,
  Eye,
  Code,
  FileCode,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { formatDate, formatRelativeTime } from '@/lib/utils';
import { projectsApi, jobsApi, type ProjectWithGenerations, type Job } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface ProjectDetailProps {
  project: ProjectWithGenerations;
}

export function ProjectDetail({ project: initialProject }: ProjectDetailProps) {
  const { data: session } = useSession();
  const router = useRouter();
  const { toast } = useToast();
  const [project, setProject] = useState(initialProject);
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'history'>('overview');
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Poll for updates when generating
  useEffect(() => {
    if (project.status !== 'generating') return;

    const interval = setInterval(async () => {
      if (!session?.accessToken) return;
      try {
        const updated = await projectsApi.get(session.accessToken, project.id);
        setProject(updated);
        if (updated.status !== 'generating') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll project status:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [project.id, project.status, session?.accessToken]);

  const latestGeneration = project.generations?.[0];

  const handleRegenerate = async () => {
    if (!session?.accessToken || !project.brief) return;

    setIsRegenerating(true);
    try {
      await projectsApi.generate(session.accessToken, project.id, {
        brief: project.brief,
        locale: project.locale,
        industry: project.industry,
        business_type: project.business_type,
      });

      toast({
        title: 'Regenerating...',
        description: 'Your website is being regenerated',
        variant: 'success',
      });

      // Refresh project data
      const updated = await projectsApi.get(session.accessToken, project.id);
      setProject(updated);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to regenerate',
        variant: 'destructive',
      });
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleDelete = async () => {
    if (!session?.accessToken) return;
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) return;

    setIsDeleting(true);
    try {
      await projectsApi.delete(session.accessToken, project.id);
      toast({
        title: 'Project deleted',
        description: 'Your project has been deleted',
      });
      router.push('/dashboard/projects');
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete project',
        variant: 'destructive',
      });
      setIsDeleting(false);
    }
  };

  const statusConfig: Record<string, { icon: typeof Clock; color: string; bg: string; label: string; animate?: boolean }> = {
    draft: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-800', label: 'Draft' },
    generating: { icon: Loader2, color: 'text-yellow-500', bg: 'bg-yellow-100 dark:bg-yellow-900/30', label: 'Generating', animate: true },
    generated: { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Ready' },
    deployed: { icon: ExternalLink, color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900/30', label: 'Deployed' },
    failed: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30', label: 'Failed' },
  };

  const status = statusConfig[project.status] || statusConfig.draft;
  const StatusIcon = status.icon;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/dashboard/projects"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Projects
          </Link>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
              <StatusIcon className={`h-3 w-3 ${status.animate ? 'animate-spin' : ''}`} />
              {status.label}
            </span>
            <span>•</span>
            <span>Created {formatRelativeTime(project.created_at)}</span>
            {project.locale && (
              <>
                <span>•</span>
                <span className="uppercase">{project.locale}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {project.status === 'generated' && (
            <>
              <button className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition">
                <Eye className="h-4 w-4" />
                Preview
              </button>
              <button className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition">
                <Download className="h-4 w-4" />
                Export
              </button>
            </>
          )}
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating || project.status === 'generating'}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition"
          >
            {isRegenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Regenerate
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-6">
          {(['overview', 'files', 'history'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Generation Status */}
            {project.status === 'generating' && (
              <div className="rounded-xl border bg-card p-6">
                <div className="flex items-center gap-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Sparkles className="h-6 w-6 text-primary animate-pulse" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">Generating your website...</h3>
                    <p className="text-sm text-muted-foreground">
                      Our AI is crafting your website. This usually takes 1-3 minutes.
                    </p>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary animate-pulse rounded-full w-2/3" />
                  </div>
                </div>
              </div>
            )}

            {/* Brief */}
            {project.brief && (
              <div className="rounded-xl border bg-card p-6">
                <h3 className="font-semibold mb-3">Project Brief</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {project.brief}
                </p>
              </div>
            )}

            {/* Latest Generation */}
            {latestGeneration && (
              <div className="rounded-xl border bg-card p-6">
                <h3 className="font-semibold mb-4">Latest Generation</h3>
                <div className="grid sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Version</p>
                    <p className="font-medium">v{latestGeneration.version}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Files</p>
                    <p className="font-medium">{latestGeneration.files?.length || 0} files</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Generated</p>
                    <p className="font-medium">{formatRelativeTime(latestGeneration.created_at)}</p>
                  </div>
                </div>

                {latestGeneration.lighthouse_scores && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm text-muted-foreground mb-2">Lighthouse Scores</p>
                    <div className="flex gap-4">
                      {Object.entries(latestGeneration.lighthouse_scores).map(([key, value]) => (
                        <div key={key} className="text-center">
                          <div className="text-lg font-bold text-primary">{value as number}</div>
                          <div className="text-xs text-muted-foreground capitalize">{key}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <div className="rounded-xl border bg-card p-6">
              <h3 className="font-semibold mb-4">Project Details</h3>
              <dl className="space-y-3 text-sm">
                {project.description && (
                  <div>
                    <dt className="text-muted-foreground">Description</dt>
                    <dd>{project.description}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-muted-foreground">Target Region</dt>
                  <dd className="uppercase">{project.locale || 'en-US'}</dd>
                </div>
                {project.industry && (
                  <div>
                    <dt className="text-muted-foreground">Industry</dt>
                    <dd className="capitalize">{project.industry}</dd>
                  </div>
                )}
                {project.business_type && (
                  <div>
                    <dt className="text-muted-foreground">Type</dt>
                    <dd className="capitalize">{project.business_type}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-muted-foreground">Last Updated</dt>
                  <dd>{formatDate(project.updated_at)}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h3 className="font-semibold mb-4">Actions</h3>
              <div className="space-y-2">
                <button className="w-full inline-flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition">
                  <Settings className="h-4 w-4" />
                  Project Settings
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-destructive/20 px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 transition disabled:opacity-50"
                >
                  {isDeleting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  Delete Project
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'files' && (
        <div className="rounded-xl border bg-card p-6">
          {latestGeneration?.files && latestGeneration.files.length > 0 ? (
            <div className="space-y-2">
              {latestGeneration.files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted transition"
                >
                  <FileCode className="h-5 w-5 text-muted-foreground" />
                  <span className="font-mono text-sm">{file.path}</span>
                  <span className="text-xs text-muted-foreground ml-auto">{file.language}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Code className="h-12 w-12 mx-auto opacity-50" />
              <p className="mt-2">No files generated yet</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="rounded-xl border bg-card p-6">
          {project.generations && project.generations.length > 0 ? (
            <div className="space-y-4">
              {project.generations.map((gen) => (
                <div key={gen.id} className="flex items-center gap-4 p-3 rounded-lg border">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                    v{gen.version}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">Generation #{gen.version}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(gen.created_at)} • {gen.files?.length || 0} files
                    </p>
                  </div>
                  <button className="text-sm text-primary hover:underline">View</button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="h-12 w-12 mx-auto opacity-50" />
              <p className="mt-2">No generation history yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
