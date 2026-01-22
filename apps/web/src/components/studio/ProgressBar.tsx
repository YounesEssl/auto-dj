import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Check, X, Music, Waves, Sliders, Download } from 'lucide-react';

import { cn } from '@autodj/ui';
import { socketService, TransitionProgressEvent } from '@/services/socket.service';
import type { Project } from '@/services/projects.service';
import type { JobProgress } from '@autodj/shared-types';

interface ProgressBarProps {
  project: Project | null;
}

interface ProgressState {
  stage: string;
  progress: number;
  currentStep?: string;
  error?: string;
}

interface TransitionProgressState {
  transitionId: string;
  stage: string;
  progress: number;
  message?: string;
}

const STAGE_LABELS: Record<string, string> = {
  uploading: 'Uploading tracks...',
  analyzing: 'Analyzing tracks...',
  ordering: 'Calculating optimal order...',
  ready: 'Ready to generate mix',
  mixing: 'Generating transitions...',
  completed: 'Mix complete!',
  failed: 'Generation failed',
};

const STAGE_COLORS: Record<string, string> = {
  uploading: 'bg-blue-500',
  analyzing: 'bg-accent',
  ordering: 'bg-violet-500',
  ready: 'bg-amber-500',
  mixing: 'bg-primary',
  completed: 'bg-success',
  failed: 'bg-destructive',
};

// Transition generation stage labels
const TRANSITION_STAGE_LABELS: Record<string, string> = {
  extraction: 'Loading audio...',
  'time-stretch': 'Syncing BPM...',
  stems: 'Separating stems...',
  beatmatch: 'Aligning beats...',
  mixing: 'Creating mix...',
  eq: 'Applying EQ...',
  export: 'Exporting...',
};

// Icons for each transition stage
const TRANSITION_STAGE_ICONS: Record<string, React.ReactNode> = {
  extraction: <Music className="w-3 h-3" />,
  'time-stretch': <Sliders className="w-3 h-3" />,
  stems: <Waves className="w-3 h-3" />,
  beatmatch: <Sliders className="w-3 h-3" />,
  mixing: <Waves className="w-3 h-3" />,
  eq: <Sliders className="w-3 h-3" />,
  export: <Download className="w-3 h-3" />,
};

/**
 * Progress bar component for showing real-time WebSocket progress
 * Displays during analysis, ordering, and mix generation
 */
export function ProgressBar({ project }: ProgressBarProps) {
  const [progressState, setProgressState] = useState<ProgressState | null>(null);
  const [transitionProgress, setTransitionProgress] = useState<TransitionProgressState | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const projectIdRef = useRef<string | undefined>(project?.id);

  // Keep project ID ref updated
  projectIdRef.current = project?.id;

  // Check if we should show progress based on project status
  const shouldShowProgress = project && ['UPLOADING', 'ANALYZING', 'ORDERING', 'MIXING'].includes(project.status);

  useEffect(() => {
    const handleProgress = (data: JobProgress) => {
      // Only process events for the current project
      if (data.projectId !== projectIdRef.current) return;

      console.log('[ProgressBar] Received progress:', data);

      setProgressState({
        stage: data.stage,
        progress: data.progress,
        currentStep: data.currentStep,
        error: data.error,
      });
      setIsVisible(true);

      // Clear any existing hide timeout
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }

      // Hide after completion with a delay
      if (data.stage === 'completed' || data.stage === 'ready' || data.stage === 'failed') {
        hideTimeoutRef.current = setTimeout(() => {
          setIsVisible(false);
          setProgressState(null);
          setTransitionProgress(null);
        }, 5000);
      }
    };

    // Handle transition-specific progress events
    const handleTransitionProgress = (data: TransitionProgressEvent) => {
      // Only process events for the current project
      if (data.projectId !== projectIdRef.current) return;

      console.log('[ProgressBar] Received transition progress:', data);

      if (data.status === 'PROCESSING' && data.stage) {
        setTransitionProgress({
          transitionId: data.transitionId,
          stage: data.stage,
          progress: data.progress || 0,
          message: data.message,
        });
        setIsVisible(true);

        // Clear hide timeout while processing
        if (hideTimeoutRef.current) {
          clearTimeout(hideTimeoutRef.current);
        }
      } else if (data.status === 'COMPLETED' || data.status === 'ERROR') {
        // Clear transition progress when done
        setTransitionProgress(null);
      }
    };

    socketService.onProgress(handleProgress);
    socketService.onTransitionProgress(handleTransitionProgress);

    return () => {
      socketService.offProgress(handleProgress);
      socketService.offTransitionProgress(handleTransitionProgress);
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
    };
  }, []);

  // Show progress bar immediately when project status changes to a processing state
  useEffect(() => {
    if (shouldShowProgress && !progressState) {
      // Initialize progress from project status
      const stage = project?.status?.toLowerCase() || 'analyzing';
      setProgressState({ stage, progress: 0 });
      setIsVisible(true);
    } else if (!shouldShowProgress && progressState?.stage !== 'completed' && progressState?.stage !== 'ready') {
      // Hide if we're no longer in a processing state (unless showing completion)
      if (!hideTimeoutRef.current) {
        setIsVisible(false);
        setProgressState(null);
      }
    }
  }, [shouldShowProgress, project?.status, progressState]);

  // Don't render if not visible or no progress
  if (!isVisible || !progressState) return null;

  const isComplete = progressState.stage === 'completed' || progressState.stage === 'ready';
  const isFailed = progressState.stage === 'failed';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="bg-card/80 backdrop-blur-sm border-b border-border overflow-hidden"
      >
        <div className="px-4 py-2">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              {isComplete ? (
                <Check className="w-3.5 h-3.5 text-success" />
              ) : isFailed ? (
                <X className="w-3.5 h-3.5 text-destructive" />
              ) : (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              )}
              <span className={cn(
                'text-xs font-medium',
                isComplete && 'text-success',
                isFailed && 'text-destructive'
              )}>
                {progressState.currentStep || STAGE_LABELS[progressState.stage] || progressState.stage}
              </span>
            </div>
            <span className="text-xs text-muted-foreground font-mono tabular-nums">
              {Math.round(progressState.progress)}%
            </span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <motion.div
              className={cn(
                'h-full rounded-full transition-colors',
                STAGE_COLORS[progressState.stage] || 'bg-primary'
              )}
              initial={{ width: 0 }}
              animate={{ width: `${progressState.progress}%` }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            />
          </div>
          {progressState.error && (
            <p className="text-xs text-destructive mt-1">{progressState.error}</p>
          )}

          {/* Transition generation stages */}
          {transitionProgress && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 pt-2 border-t border-border/50"
            >
              <div className="flex items-center gap-3">
                {/* Stage indicator pills */}
                <div className="flex items-center gap-1">
                  {['extraction', 'stems', 'mixing', 'export'].map((stage) => {
                    const isActive = transitionProgress.stage === stage ||
                      (stage === 'stems' && transitionProgress.stage === 'time-stretch') ||
                      (stage === 'mixing' && ['beatmatch', 'eq'].includes(transitionProgress.stage));
                    const isPast = getStageOrder(transitionProgress.stage) > getStageOrder(stage);

                    return (
                      <div
                        key={stage}
                        className={cn(
                          'flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium transition-all',
                          isActive && 'bg-primary/20 text-primary',
                          isPast && 'bg-success/20 text-success',
                          !isActive && !isPast && 'bg-muted/50 text-muted-foreground'
                        )}
                      >
                        {isPast ? (
                          <Check className="w-2.5 h-2.5" />
                        ) : isActive ? (
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        ) : (
                          TRANSITION_STAGE_ICONS[stage]
                        )}
                        <span className="hidden sm:inline">
                          {stage === 'extraction' ? 'Load' :
                           stage === 'stems' ? 'Stems' :
                           stage === 'mixing' ? 'Mix' : 'Export'}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Current step label */}
                <span className="text-[10px] text-muted-foreground flex-1 truncate">
                  {TRANSITION_STAGE_LABELS[transitionProgress.stage] || transitionProgress.message}
                </span>

                {/* Stage progress */}
                <span className="text-[10px] text-primary font-mono tabular-nums">
                  {transitionProgress.progress}%
                </span>
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

// Helper to determine stage order for comparison
function getStageOrder(stage: string): number {
  const order: Record<string, number> = {
    extraction: 1,
    'time-stretch': 2,
    stems: 3,
    beatmatch: 4,
    mixing: 5,
    eq: 6,
    export: 7,
  };
  return order[stage] || 0;
}
