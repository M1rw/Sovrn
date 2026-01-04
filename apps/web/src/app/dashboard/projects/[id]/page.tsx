import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { projectsApi } from '@/lib/api';
import { ProjectDetail } from './project-detail';

interface ProjectPageProps {
  params: { id: string };
}

export async function generateMetadata({
  params,
}: ProjectPageProps): Promise<Metadata> {
  const session = await getServerSession(authOptions);
  if (!session) return { title: 'Project' };

  try {
    const project = await projectsApi.get(session.accessToken, params.id);
    return { title: project.name };
  } catch {
    return { title: 'Project' };
  }
}

export default async function ProjectPage({ params }: ProjectPageProps) {
  const session = await getServerSession(authOptions);
  if (!session) notFound();

  let project;
  try {
    project = await projectsApi.get(session.accessToken, params.id);
  } catch {
    notFound();
  }

  return <ProjectDetail project={project} />;
}
