'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Sparkles, ArrowRight, ArrowLeft } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { projectsApi } from '@/lib/api';

const projectSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(100),
  description: z.string().max(500).optional(),
  locale: z.string().default('en-US'),
  industry: z.string().optional(),
  business_type: z.string().optional(),
  brief: z.string().min(20, 'Please provide more detail about your website'),
});

type ProjectFormData = z.infer<typeof projectSchema>;

const industries = [
  { value: '', label: 'Select industry...' },
  { value: 'technology', label: 'Technology' },
  { value: 'ecommerce', label: 'E-Commerce' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'finance', label: 'Finance' },
  { value: 'education', label: 'Education' },
  { value: 'restaurant', label: 'Restaurant & Food' },
  { value: 'realestate', label: 'Real Estate' },
  { value: 'professional', label: 'Professional Services' },
  { value: 'creative', label: 'Creative & Design' },
  { value: 'nonprofit', label: 'Non-Profit' },
  { value: 'other', label: 'Other' },
];

const businessTypes = [
  { value: '', label: 'Select type...' },
  { value: 'landing', label: 'Landing Page' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'business', label: 'Business Website' },
  { value: 'saas', label: 'SaaS Product' },
  { value: 'blog', label: 'Blog' },
  { value: 'agency', label: 'Agency' },
  { value: 'startup', label: 'Startup' },
  { value: 'personal', label: 'Personal Brand' },
];

const locales = [
  { value: 'en-US', label: '🇺🇸 English (US)' },
  { value: 'en-GB', label: '🇬🇧 English (UK)' },
  { value: 'de-DE', label: '🇩🇪 German' },
  { value: 'fr-FR', label: '🇫🇷 French' },
  { value: 'es-ES', label: '🇪🇸 Spanish' },
  { value: 'pt-BR', label: '🇧🇷 Portuguese (Brazil)' },
  { value: 'ar-SA', label: '🇸🇦 Arabic (Saudi Arabia)' },
  { value: 'ar-EG', label: '🇪🇬 Arabic (Egypt)' },
  { value: 'hi-IN', label: '🇮🇳 Hindi' },
  { value: 'ja-JP', label: '🇯🇵 Japanese' },
  { value: 'zh-CN', label: '🇨🇳 Chinese (Simplified)' },
  { value: 'sw-KE', label: '🇰🇪 Swahili' },
];

export function NewProjectForm() {
  const router = useRouter();
  const { data: session } = useSession();
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      locale: 'en-US',
    },
  });

  const watchedFields = watch(['name', 'brief']);

  const onSubmit = async (data: ProjectFormData) => {
    if (!session?.accessToken) return;

    setIsLoading(true);
    try {
      // Create project
      const project = await projectsApi.create(session.accessToken, {
        name: data.name,
        description: data.description,
        locale: data.locale,
        industry: data.industry,
        business_type: data.business_type,
      });

      // Start generation
      await projectsApi.generate(session.accessToken, project.id, {
        brief: data.brief,
        locale: data.locale,
        industry: data.industry,
        business_type: data.business_type,
      });

      toast({
        title: 'Project created!',
        description: 'Your website is being generated...',
        variant: 'success',
      });

      router.push(`/dashboard/projects/${project.id}`);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create project',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {step === 1 && (
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium">
              Project Name *
            </label>
            <input
              id="name"
              type="text"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="My Awesome Website"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium">
              Description <span className="text-muted-foreground">(optional)</span>
            </label>
            <textarea
              id="description"
              rows={2}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="A brief description of your project"
              {...register('description')}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="industry" className="text-sm font-medium">
                Industry
              </label>
              <select
                id="industry"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                {...register('industry')}
              >
                {industries.map((ind) => (
                  <option key={ind.value} value={ind.value}>
                    {ind.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="business_type" className="text-sm font-medium">
                Website Type
              </label>
              <select
                id="business_type"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                {...register('business_type')}
              >
                {businessTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="locale" className="text-sm font-medium">
              Target Region
            </label>
            <select
              id="locale"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...register('locale')}
            >
              {locales.map((loc) => (
                <option key={loc.value} value={loc.value}>
                  {loc.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Cultural adaptations will be applied for this region
            </p>
          </div>

          <div className="pt-4">
            <button
              type="button"
              onClick={() => setStep(2)}
              disabled={!watchedFields[0]}
              className="w-full inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none transition"
            >
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="brief" className="text-sm font-medium">
              Tell us about your website *
            </label>
            <textarea
              id="brief"
              rows={8}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="Describe your business, your target audience, what you want to achieve with this website, and any specific features or pages you need. The more detail you provide, the better the result!"
              {...register('brief')}
            />
            {errors.brief && (
              <p className="text-sm text-destructive">{errors.brief.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Include: your business goal, target audience, key features, brand style preferences
            </p>
          </div>

          <div className="bg-primary/5 rounded-lg p-4 border border-primary/20">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <p className="font-medium text-sm">Generation Cost: 1 Spark</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Our AI will analyze your brief and generate a complete, production-ready website
                </p>
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="flex-1 inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </button>
            <button
              type="submit"
              disabled={isLoading || !watchedFields[1]}
              className="flex-1 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none transition"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Website
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </form>
  );
}
