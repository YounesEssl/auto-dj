import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';

import { Layout } from '@/components/layout/Layout';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ProjectPage } from '@/pages/ProjectPage';
import { NewProjectPage } from '@/pages/NewProjectPage';
import { DraftsListPage } from '@/pages/DraftsListPage';
import { NewDraftPage } from '@/pages/NewDraftPage';
import { DraftPage } from '@/pages/DraftPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * Main application component with routing
 */
function App() {
  return (
    <>
      <Routes>
        {/* Auth routes without layout */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Main app routes with layout */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="projects/new" element={<NewProjectPage />} />
          <Route path="projects/:id" element={<ProjectPage />} />
          <Route path="drafts" element={<DraftsListPage />} />
          <Route path="drafts/new" element={<NewDraftPage />} />
          <Route path="drafts/:id" element={<DraftPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      <Toaster position="bottom-right" richColors />
    </>
  );
}

export default App;
