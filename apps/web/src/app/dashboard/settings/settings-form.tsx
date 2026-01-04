'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { usersApi } from '@/lib/api';

const profileSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').optional(),
  email: z.string().email('Please enter a valid email'),
});

type ProfileFormData = z.infer<typeof profileSchema>;

interface SettingsFormProps {
  user: {
    id: string;
    email: string;
    name?: string;
  };
}

export function SettingsForm({ user }: SettingsFormProps) {
  const { data: session, update } = useSession();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: user.name || '',
      email: user.email,
    },
  });

  const onSubmit = async (data: ProfileFormData) => {
    if (!session?.accessToken) return;

    setIsLoading(true);
    try {
      await usersApi.updateProfile(session.accessToken, {
        name: data.name,
      });

      // Update session
      await update({
        ...session,
        user: {
          ...session.user,
          name: data.name,
        },
      });

      toast({
        title: 'Profile updated',
        description: 'Your profile has been updated successfully',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to update profile',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="name" className="text-sm font-medium">
          Name
        </label>
        <input
          id="name"
          type="text"
          className="w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          {...register('name')}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          disabled
          className="w-full rounded-md border bg-muted px-3 py-2 text-sm cursor-not-allowed"
          {...register('email')}
        />
        <p className="text-xs text-muted-foreground">
          Email cannot be changed. Contact support if needed.
        </p>
      </div>

      <div className="pt-4">
        <button
          type="submit"
          disabled={isLoading || !isDirty}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none transition"
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save Changes
        </button>
      </div>
    </form>
  );
}
