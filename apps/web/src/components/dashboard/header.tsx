'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { signOut } from 'next-auth/react';
import { useState } from 'react';
import {
  Sparkles,
  Menu,
  User,
  Settings,
  LogOut,
  Moon,
  Sun,
  Bell,
} from 'lucide-react';
import { useTheme } from 'next-themes';

interface DashboardHeaderProps {
  user: {
    id: string;
    email: string;
    name?: string | null;
  };
}

export function DashboardHeader({ user }: DashboardHeaderProps) {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut({ redirect: false });
    router.push('/');
  };

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4">
        {/* Mobile menu button */}
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="md:hidden rounded-md p-2 hover:bg-muted"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-lg ml-2 md:ml-0">
          <Sparkles className="h-5 w-5 text-primary" />
          <span className="hidden sm:inline">SOVRN</span>
        </Link>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right side items */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <button className="rounded-md p-2 hover:bg-muted relative">
            <Bell className="h-5 w-5 text-muted-foreground" />
          </button>

          {/* Theme toggle */}
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="rounded-md p-2 hover:bg-muted"
          >
            {theme === 'dark' ? (
              <Sun className="h-5 w-5 text-muted-foreground" />
            ) : (
              <Moon className="h-5 w-5 text-muted-foreground" />
            )}
          </button>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 rounded-full p-1 hover:bg-muted"
            >
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-sm font-medium text-primary">
                  {(user.name?.[0] || user.email[0]).toUpperCase()}
                </span>
              </div>
            </button>

            {isUserMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setIsUserMenuOpen(false)}
                />
                <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border bg-card shadow-lg z-50">
                  <div className="p-3 border-b">
                    <p className="font-medium truncate">
                      {user.name || 'User'}
                    </p>
                    <p className="text-sm text-muted-foreground truncate">
                      {user.email}
                    </p>
                  </div>
                  <div className="p-1">
                    <Link
                      href="/dashboard/settings"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-muted transition"
                    >
                      <User className="h-4 w-4" />
                      Profile
                    </Link>
                    <Link
                      href="/dashboard/settings"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-muted transition"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                    <button
                      onClick={handleSignOut}
                      className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

