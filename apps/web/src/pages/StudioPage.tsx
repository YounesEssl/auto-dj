import { useEffect, useState, useRef, useCallback, MouseEvent as ReactMouseEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { toast } from 'sonner';

import { useProjectStore } from '@/stores/projectStore';
import { useStudioStore } from '@/stores/studioStore';
import { useAuthStore } from '@/stores/authStore';
import { projectsService } from '@/services/projects.service';
import { socketService } from '@/services/socket.service';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { MixList } from '@/components/studio/MixList';
import { TrackPool } from '@/components/studio/TrackPool';
import { Timeline } from '@/components/studio/Timeline';
import { Inspector } from '@/components/studio/Inspector';
import { PlayerBar } from '@/components/studio/PlayerBar';
import { ProgressBar } from '@/components/studio/ProgressBar';
import { StudioSkeleton } from '@/components/studio/Skeleton';
import { Chat } from '@/components/studio/Chat';

/**
 * Main Mix Studio page - unified workspace for creating DJ mixes
 */
export function StudioPage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const { currentProject, fetchProject, isLoading, updateCurrentProject } = useProjectStore();
  const { reset, setTimelineTracks, timelineTracks, setCurrentTime, currentTime, trackPoolHeight, setTrackPoolHeight } = useStudioStore();
  const [isOrdering, setIsOrdering] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartY = useRef(0);
  const resizeStartHeight = useRef(0);

  // Use ref to avoid stale closures in socket handlers
  const idRef = useRef(id);
  idRef.current = id;

  // Keyboard shortcuts for skip back/forward (10 seconds)
  const handleSkipBack = useCallback(() => {
    setCurrentTime(Math.max(0, currentTime - 10));
  }, [currentTime, setCurrentTime]);

  const handleSkipForward = useCallback(() => {
    setCurrentTime(currentTime + 10);
  }, [currentTime, setCurrentTime]);

  // Enable keyboard shortcuts
  useKeyboardShortcuts({
    enabled: !!id,
    onSkipBack: handleSkipBack,
    onSkipForward: handleSkipForward,
  });

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Load project when ID changes
  useEffect(() => {
    if (id) {
      fetchProject(id);
    } else {
      reset();
    }

    return () => {
      reset();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Subscribe to real-time updates
  useEffect(() => {
    if (!id) return;

    socketService.connect();
    socketService.subscribeToProject(id);

    const handleProgress = (data: { stage: string; progress: number; projectId?: string }) => {
      // Only handle events for this project
      if (data.projectId && data.projectId !== idRef.current) return;

      // Refresh project on completion stages
      const completionStages = ['completed', 'ready', 'failed'];
      if ((data.progress === 100 || completionStages.includes(data.stage)) && idRef.current) {
        fetchProject(idRef.current);
      }
    };

    const handleOrdered = () => {
      if (idRef.current) {
        fetchProject(idRef.current);
        toast.success('Tracks arranged');
      }
    };

    socketService.onProgress(handleProgress);
    socketService.onMixOrdered(handleOrdered);

    return () => {
      socketService.offProgress(handleProgress);
      socketService.offMixOrdered(handleOrdered);
      socketService.unsubscribeFromProject(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Sync timeline with project's ordered tracks
  useEffect(() => {
    if (currentProject?.orderedTracks) {
      setTimelineTracks(currentProject.orderedTracks);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject?.orderedTracks]);

  // Track the last saved order to compare for changes
  const lastSavedOrderRef = useRef<string[]>([]);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Auto-save track order with debounce when timeline changes
  useEffect(() => {
    if (!id || !currentProject) return;

    // Skip if timeline is empty or has only 1 track
    if (timelineTracks.length < 2) return;

    // Skip if order hasn't actually changed from what we saved
    const currentOrderStr = timelineTracks.join(',');
    const lastSavedStr = lastSavedOrderRef.current.join(',');
    const serverOrderStr = (currentProject.orderedTracks || []).join(',');

    // If current order matches server or last saved, no need to save
    if (currentOrderStr === serverOrderStr || currentOrderStr === lastSavedStr) {
      return;
    }

    // Clear any pending save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Debounce save by 800ms
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const updatedProject = await projectsService.saveTrackOrder(id, timelineTracks);
        lastSavedOrderRef.current = [...timelineTracks];
        // Update project store with orderedTracks AND transitions (transitions are recalculated by backend)
        updateCurrentProject({
          orderedTracks: updatedProject.orderedTracks,
          transitions: updatedProject.transitions,
          averageMixScore: updatedProject.averageMixScore,
        });
      } catch (err) {
        console.error('Failed to save track order:', err);
        toast.error('Failed to save track order');
      }
    }, 800);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timelineTracks, id]);

  // Handle resizer drag
  const handleResizeStart = useCallback((e: ReactMouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartY.current = e.clientY;
    resizeStartHeight.current = trackPoolHeight;
  }, [trackPoolHeight]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: globalThis.MouseEvent) => {
      const delta = e.clientY - resizeStartY.current;
      setTrackPoolHeight(resizeStartHeight.current + delta);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, setTrackPoolHeight]);

  const handleAutoArrange = async () => {
    if (!id) return;

    setIsOrdering(true);
    try {
      await projectsService.calculateOrder(id);
      await fetchProject(id);
      toast.success('Tracks arranged optimally');
    } catch {
      toast.error('Failed to arrange tracks');
    } finally {
      setIsOrdering(false);
    }
  };

  // Loading state with skeleton
  if (isLoading && id) {
    return <StudioSkeleton />;
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="h-screen flex flex-col bg-background overflow-hidden">
        {/* Progress Bar */}
        <ProgressBar project={currentProject} />

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Mix List Sidebar */}
          <MixList />

          {/* Main Workspace */}
          <main className="flex-1 flex flex-col overflow-hidden">
            {id && currentProject ? (
              <>
                {/* Track Pool */}
                <div
                  className="border-b border-border p-3 relative flex-shrink-0"
                  style={{ height: trackPoolHeight }}
                >
                  <TrackPool
                    projectId={currentProject.id}
                    tracks={currentProject.tracks}
                  />
                </div>

                {/* Resizer Handle */}
                <div
                  onMouseDown={handleResizeStart}
                  className={`
                    h-2 flex-shrink-0 cursor-ns-resize group relative
                    flex items-center justify-center
                    hover:bg-primary/10 transition-colors
                    ${isResizing ? 'bg-primary/20' : ''}
                  `}
                >
                  <div className={`
                    w-12 h-1 rounded-full transition-all
                    ${isResizing ? 'bg-primary' : 'bg-border group-hover:bg-primary/50'}
                  `} />
                </div>

                {/* Timeline */}
                <div className="flex-1 p-3 overflow-hidden min-h-[100px]">
                  <Timeline
                    project={currentProject}
                    onAutoArrange={handleAutoArrange}
                    isOrdering={isOrdering}
                  />
                </div>
              </>
            ) : (
              /* Empty State */
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-md px-4">
                  <div className="rounded-full bg-primary/10 p-6 w-24 h-24 mx-auto mb-6 flex items-center justify-center">
                    <svg
                      className="w-12 h-12 text-primary"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <circle cx="12" cy="12" r="3" />
                      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-semibold mb-2">Welcome to Mix Studio</h2>
                  <p className="text-muted-foreground mb-6">
                    Create a new mix or select an existing one from the sidebar to get started.
                    Upload your tracks, arrange them, and generate a seamless DJ mix.
                  </p>
                </div>
              </div>
            )}
          </main>

          {/* Inspector */}
          {id && currentProject && <Inspector projectId={currentProject.id} />}
        </div>

        {/* Player Bar */}
        <PlayerBar project={currentProject} />

        {/* AI Chat Assistant */}
        {id && currentProject && <Chat projectId={currentProject.id} />}
      </div>
    </DndProvider>
  );
}
