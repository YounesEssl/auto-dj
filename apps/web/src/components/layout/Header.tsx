import { Link } from 'react-router-dom';
import { Music2 } from 'lucide-react';

import { Button } from '@autodj/ui';
import { useAuthStore } from '@/stores/authStore';

/**
 * Application header with navigation and user menu
 */
export function Header() {
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex">
          <Link to="/" className="mr-6 flex items-center space-x-2">
            <Music2 className="h-6 w-6 text-primary" />
            <span className="font-bold">AutoDJ</span>
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-end space-x-4">
          {isAuthenticated ? (
            <div className="flex items-center space-x-4">
              <span className="text-sm text-muted-foreground">
                {user?.name || user?.email}
              </span>
              <Button variant="ghost" size="sm" onClick={logout}>
                Logout
              </Button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  Login
                </Button>
              </Link>
              <Link to="/register">
                <Button size="sm">Sign Up</Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
