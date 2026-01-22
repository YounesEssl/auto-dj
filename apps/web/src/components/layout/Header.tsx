import { Link } from 'react-router-dom';
import { Zap, LogOut, User } from 'lucide-react';

import { Button } from '@autodj/ui';
import { useAuthStore } from '@/stores/authStore';

/**
 * Application header - Midnight Studio hardware-inspired design
 */
export function Header() {
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      {/* Top hardware strip */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent" />

      <div className="container flex h-14 items-center justify-between">
        {/* Logo / Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 bg-primary rounded flex items-center justify-center shadow-[0_0_15px_rgba(251,191,36,0.4)] group-hover:shadow-[0_0_20px_rgba(251,191,36,0.6)] transition-shadow">
            <Zap size={16} className="text-primary-foreground fill-current" />
          </div>
          <span className="text-sm font-bold tracking-tight uppercase">
            AutoDJ<span className="text-primary font-mono">.io</span>
          </span>
        </Link>

        {/* Navigation Links (hidden on mobile) */}
        <nav className="hidden md:flex items-center gap-8">
          <Link
            to="/studio"
            className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground hover:text-primary transition-colors font-medium"
          >
            Mix Studio
          </Link>
        </nav>

        {/* User Section */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="flex items-center gap-4">
              {/* Status LED */}
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[hsl(142,70%,45%)] shadow-[0_0_8px_hsl(142,70%,45%)]" />
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider hidden sm:block">
                  Online
                </span>
              </div>

              <div className="h-6 w-px bg-border hidden sm:block" />

              {/* User info */}
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded bg-muted/50 border border-border/50">
                  <User size={14} className="text-muted-foreground" />
                </div>
                <span className="text-[11px] text-muted-foreground font-medium hidden sm:block max-w-[120px] truncate">
                  {user?.name || user?.email}
                </span>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-8 px-3 text-[10px] uppercase tracking-widest text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              >
                <LogOut size={14} className="mr-1.5" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-4 text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground"
                >
                  Login
                </Button>
              </Link>
              <Link to="/register">
                <Button
                  size="sm"
                  className="btn-glow h-8 px-4 text-[10px] uppercase tracking-widest font-bold"
                >
                  Sign Up
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
