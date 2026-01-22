import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';

import { Layout } from '@/components/layout/Layout';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { StudioPage } from '@/pages/StudioPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * Main application component with routing
 * Refactored to use unified Mix Studio instead of separate pages
 */
function App() {
  return (
    <>
      <Routes>
        {/* Auth routes without layout */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Landing page with layout */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        {/* Studio routes (standalone, no layout wrapper) */}
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/studio/:id" element={<StudioPage />} />
      </Routes>
      <Toaster position="bottom-right" richColors />
    </>
  );
}

export default App;
