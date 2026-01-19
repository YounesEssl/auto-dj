import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

import { Button } from '@autodj/ui';

/**
 * 404 Not Found page
 */
export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] text-center">
      <h1 className="text-6xl font-bold text-primary mb-4">404</h1>
      <h2 className="text-2xl font-semibold mb-2">Page Not Found</h2>
      <p className="text-muted-foreground mb-6">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/">
        <Button>
          <Home className="mr-2 h-4 w-4" />
          Go Home
        </Button>
      </Link>
    </div>
  );
}
