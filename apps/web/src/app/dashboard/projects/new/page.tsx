import { Metadata } from 'next';
import { NewProjectForm } from './new-project-form';

export const metadata: Metadata = {
  title: 'New Project',
};

export default function NewProjectPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Create New Project</h1>
        <p className="text-muted-foreground mt-1">
          Tell us about your website and we'll generate it with AI
        </p>
      </div>

      <div className="rounded-xl border bg-card p-6">
        <NewProjectForm />
      </div>
    </div>
  );
}
