import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FolderPlus, Music2 } from 'lucide-react';

import { cn } from '@autodj/ui';

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'New Project',
    href: '/projects/new',
    icon: FolderPlus,
  },
  {
    title: 'Drafts',
    href: '/drafts',
    icon: Music2,
  },
];

/**
 * Sidebar navigation component
 */
export function Sidebar() {
  return (
    <aside className="hidden w-64 border-r bg-muted/40 md:block">
      <div className="flex h-full flex-col gap-2 p-4">
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.title}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}
