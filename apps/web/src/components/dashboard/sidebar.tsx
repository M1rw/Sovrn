'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Plus,
  LayoutDashboard,
  FolderOpen,
  Sparkles,
  Settings,
  FileCode,
  HelpCircle,
  MessageSquare,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
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
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={cn(
      'hidden md:block border-r border-border/70 bg-muted/20 min-h-[calc(100vh-4rem)] transition-all duration-200',
      collapsed ? 'w-20' : 'w-72'
    )}>
      <div className="sticky top-16 h-[calc(100vh-4rem)] p-3 flex flex-col gap-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Sparkles className="h-4 w-4 text-primary" />
            {!collapsed && <span>SOVRN</span>}
          </div>
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        </div>

        <Link
          href="/builder"
          className={cn(
            'flex items-center rounded-xl py-2.5 text-sm font-medium transition bg-background hover:bg-accent border border-border/70',
            collapsed ? 'justify-center px-0' : 'gap-2.5 px-3'
          )}
          title="New Chat"
        >
          <Plus className="h-4 w-4" />
          {!collapsed && 'New Chat'}
        </Link>

        <div className="rounded-xl border border-border/60 bg-background p-2">
          {!collapsed && (
            <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Workspace
            </div>
          )}
          <nav className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href ||
                (item.href !== '/dashboard' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={item.name}
                  className={cn(
                    'group flex items-center rounded-lg py-2 text-sm transition',
                    collapsed ? 'justify-center px-0' : 'justify-between px-2.5',
                    isActive
                      ? 'bg-primary/12 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
                  )}
                >
                  <span className={cn('flex items-center', collapsed ? 'justify-center' : 'gap-2.5')}>
                    <item.icon className="h-4 w-4" />
                    {!collapsed && item.name}
                  </span>
                  {!collapsed && (
                    <ChevronRight className={cn(
                      'h-3.5 w-3.5 transition-opacity',
                      isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-60'
                    )} />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="rounded-xl border border-border/60 bg-background p-2">
          {!collapsed && (
            <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Resources
            </div>
          )}
          <nav className="space-y-1">
            {secondaryNavigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                title={item.name}
                className={cn(
                  'flex items-center rounded-lg py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/80 transition',
                  collapsed ? 'justify-center px-0' : 'gap-2.5 px-2.5'
                )}
              >
                <item.icon className="h-4 w-4" />
                {!collapsed && item.name}
              </Link>
            ))}
          </nav>
        </div>

        <div className="mt-auto rounded-xl border border-border/70 bg-gradient-to-b from-primary/10 to-background p-3.5">
          <div className={cn('flex items-center text-sm font-medium text-foreground', collapsed ? 'justify-center' : 'gap-2')}>
            <MessageSquare className="h-4 w-4" />
            {!collapsed && 'AI Credits'}
          </div>
          {!collapsed && (
            <>
              <p className="mt-1 text-xs text-muted-foreground">
                Upgrade your Sparks to keep generating sites without interruption.
              </p>
              <Link
                href="/dashboard/sparks"
                className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition"
              >
                Manage Sparks
              </Link>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
