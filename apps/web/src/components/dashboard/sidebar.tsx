'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderOpen,
  Sparkles,
  Settings,
  FileCode,
  HelpCircle,
} from 'lucide-react';

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Projects',
    href: '/dashboard/projects',
    icon: FolderOpen,
  },
  {
    name: 'Templates',
    href: '/dashboard/templates',
    icon: FileCode,
  },
  {
    name: 'Sparks',
    href: '/dashboard/sparks',
    icon: Sparkles,
  },
  {
    name: 'Settings',
    href: '/dashboard/settings',
    icon: Settings,
  },
];

const secondaryNavigation = [
  {
    name: 'Documentation',
    href: '/docs',
    icon: HelpCircle,
  },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r min-h-[calc(100vh-4rem)] p-4 hidden md:block">
      <nav className="space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== '/dashboard' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="mt-8">
        <div className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Resources
        </div>
        <nav className="mt-2 space-y-1">
          {secondaryNavigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition"
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </Link>
          ))}
        </nav>
      </div>

      {/* Sparks CTA */}
      <div className="mt-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 p-4">
        <div className="flex items-center gap-2 text-primary">
          <Sparkles className="h-4 w-4" />
          <span className="text-sm font-medium">Need more Sparks?</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Purchase spark packs to generate more websites
        </p>
        <Link
          href="/dashboard/sparks"
          className="mt-3 inline-flex w-full items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition"
        >
          View Plans
        </Link>
      </div>
    </aside>
  );
}
