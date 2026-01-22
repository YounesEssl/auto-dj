import { useEffect, forwardRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Music2, Trash2, Loader2, ChevronLeft, ChevronRight, User, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

import { Button } from '@autodj/ui';
import { cn } from '@autodj/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@autodj/ui';
import { useProjectStore } from '@/stores/projectStore';
import { useStudioStore } from '@/stores/studioStore';
import { useAuthStore } from '@/stores/authStore';
import type { Project } from '@/services/projects.service';

const STATUS_COLORS: Record<string, string> = {
  CREATED: 'bg-zinc-500',
  UPLOADING: 'bg-blue-500 animate-pulse',
  ANALYZING: 'bg-violet-500 animate-pulse',
  READY: 'bg-amber-500',
  ORDERING: 'bg-violet-500 animate-pulse',
  MIXING: 'bg-blue-500 animate-pulse',
  COMPLETED: 'bg-emerald-500',
  FAILED: 'bg-red-500',
};

interface MixItemProps {
  project: Project;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

const MixItem = forwardRef<HTMLDivElement, MixItemProps>(
  ({ project, isActive, onSelect, onDelete }, ref) => {
    return (
      <motion.div
        ref={ref}
        layout
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className={cn(
          'group relative flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
        )}
        onClick={onSelect}
      >
        {/* Status LED */}
        <div className={cn(
          'w-2.5 h-2.5 rounded-full flex-shrink-0 ring-1 ring-white/20',
          STATUS_COLORS[project.status] || 'bg-zinc-500'
        )} />

        {/* Mix Info */}
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{project.name}</p>
          <p className="text-xs text-muted-foreground">
            {(project.tracks?.length ?? 0)} track{(project.tracks?.length ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Delete Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </motion.div>
    );
  }
);

/**
 * Sidebar component showing list of mixes with create button
 * Supports collapsing for more workspace
 */
export function MixList() {
  const navigate = useNavigate();
  const { id: activeId } = useParams();
  const { projects, isLoadingList, fetchProjects, createProject, deleteProject } = useProjectStore();
  const { isSidebarCollapsed, toggleSidebar } = useStudioStore();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
    toast.success('Logged out');
  };

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateMix = async () => {
    try {
      const project = await createProject(`Mix ${projects.length + 1}`);
      navigate(`/studio/${project.id}`);
      toast.success('New mix created');
    } catch {
      toast.error('Failed to create mix');
    }
  };

  const handleDeleteMix = async (id: string) => {
    try {
      await deleteProject(id);
      if (activeId === id) {
        navigate('/studio');
      }
      toast.success('Mix deleted');
    } catch {
      toast.error('Failed to delete mix');
    }
  };

  const handleSelectMix = (id: string) => {
    navigate(`/studio/${id}`);
  };

  return (
    <TooltipProvider>
      <motion.aside
        initial={false}
        animate={{ width: isSidebarCollapsed ? 48 : 224 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="h-full border-r border-border bg-card/30 flex flex-col relative"
      >
        {/* Toggle Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={toggleSidebar}
              className="absolute -right-3 top-1/2 -translate-y-1/2 z-10 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center hover:bg-muted transition-colors"
            >
              {isSidebarCollapsed ? (
                <ChevronRight className="w-3.5 h-3.5" />
              ) : (
                <ChevronLeft className="w-3.5 h-3.5" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          </TooltipContent>
        </Tooltip>

        {/* Header */}
        <div className="p-2 border-b border-border">
          {isSidebarCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={handleCreateMix}
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">New Mix</TooltipContent>
            </Tooltip>
          ) : (
            <Button
              onClick={handleCreateMix}
              className="w-full gap-2 btn-glow"
              size="sm"
            >
              <Plus className="w-4 h-4" />
              New Mix
            </Button>
          )}
        </div>

        {/* Mix List */}
        <div className="flex-1 overflow-y-auto p-2 scrollbar-studio">
          {isLoadingList ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : projects.length === 0 ? (
            !isSidebarCollapsed && (
              <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                <div className="rounded-full bg-muted/50 p-3 mb-3">
                  <Music2 className="w-6 h-6 text-muted-foreground" />
                </div>
                <p className="text-sm text-muted-foreground">No mixes yet</p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Create your first mix to get started
                </p>
              </div>
            )
          ) : (
            <AnimatePresence mode="popLayout">
              {projects.map((project) => (
                isSidebarCollapsed ? (
                  <Tooltip key={project.id}>
                    <TooltipTrigger asChild>
                      <motion.div
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className={cn(
                          'w-8 h-8 mx-auto mb-1 rounded-lg flex items-center justify-center cursor-pointer transition-colors',
                          project.id === activeId
                            ? 'bg-primary/20 text-primary'
                            : 'hover:bg-muted/50 text-muted-foreground'
                        )}
                        onClick={() => handleSelectMix(project.id)}
                      >
                        <div className={cn(
                          'w-2.5 h-2.5 rounded-full ring-1 ring-white/20',
                          STATUS_COLORS[project.status] || 'bg-zinc-500'
                        )} />
                      </motion.div>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <div>
                        <p className="font-medium">{project.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {project.tracks?.length ?? 0} track{(project.tracks?.length ?? 0) !== 1 ? 's' : ''}
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <MixItem
                    key={project.id}
                    project={project}
                    isActive={project.id === activeId}
                    onSelect={() => handleSelectMix(project.id)}
                    onDelete={() => handleDeleteMix(project.id)}
                  />
                )
              ))}
            </AnimatePresence>
          )}
        </div>

        {/* User Section */}
        <div className="border-t border-border p-2">
          {isSidebarCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleLogout}
                  className="w-8 h-8 mx-auto rounded-lg flex items-center justify-center hover:bg-muted/50 text-muted-foreground hover:text-destructive transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <div>
                  <p className="font-medium">{user?.name || user?.email}</p>
                  <p className="text-xs text-muted-foreground">Click to logout</p>
                </div>
              </TooltipContent>
            </Tooltip>
          ) : (
            <div className="flex items-center gap-2 px-2 py-1.5">
              <div className="w-7 h-7 rounded-full bg-muted/50 flex items-center justify-center flex-shrink-0">
                <User className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{user?.name || user?.email}</p>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 rounded hover:bg-destructive/10 hover:text-destructive transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Logout</TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}
