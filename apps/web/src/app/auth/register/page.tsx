import { Metadata } from 'next';
import Link from 'next/link';
import { RegisterForm } from './register-form';
import { Sparkles } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Create Account',
  description: 'Create your SOVRN account',
};

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-background to-muted/20 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 text-2xl font-bold">
            <Sparkles className="h-8 w-8 text-primary" />
            <span>SOVRN</span>
          </Link>
          <h1 className="mt-6 text-2xl font-semibold tracking-tight">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Start building amazing websites with AI
          </p>
        </div>

        <div className="bg-card rounded-lg border shadow-sm p-6">
          <RegisterForm />
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/auth/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          By creating an account, you agree to our{' '}
          <Link href="/terms" className="underline hover:text-foreground">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link href="/privacy" className="underline hover:text-foreground">
            Privacy Policy
          </Link>
        </p>
      </div>
    </div>
  );
}
