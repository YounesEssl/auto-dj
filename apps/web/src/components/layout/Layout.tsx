import { Outlet } from 'react-router-dom';

import { Header } from './Header';

/**
 * Main layout component with header
 */
export function Layout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
