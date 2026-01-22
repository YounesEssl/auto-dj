import { useDrop } from 'react-dnd';
import { Sparkles, Loader2, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { cn } from '@autodj/ui';
import { Button } from '@autodj/ui';
import type { Track, Transition, Project } from '@/services/projects.service';
import { useStudioStore } from '@/stores/studioStore';
import { TimelineTrack } from './TimelineTrack';
import { TransitionIndicator } from './TransitionIndicator';
import { TRACK_DND_TYPE } from './TrackMiniCard';

interface TimelineProps {
  project: Project;
  onAutoArrange?: () => void;
  isOrdering?: boolean;
}

/**
 * Compact horizontal timeline for track arrangement
 */
export function Timeline({ project, onAutoArrange, isOrdering }: TimelineProps) {
  const {
    selection,
    setSelection,
    timelineTracks,
    moveTrackInTimeline,
    addTrackToTimeline,
    removeTrackFromTimeline,
  } = useStudioStore();

  // Note: Timeline sync with project.orderedTracks is handled in StudioPage.tsx

  // Get track and transition data from project
  const tracksMap = new Map(project.tracks.map((t) => [t.id, t]));
  const transitionsMap = new Map(
    project.transitions.map((t) => [`${t.fromTrackId}-${t.toTrackId}`, t])
  );

  // Filter timeline tracks to only include valid ones (defensive coding)
  const validTimelineTracks = timelineTracks.filter((id) => tracksMap.has(id));

  // Drop zone for adding tracks from pool
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: TRACK_DND_TYPE,
      drop: (item: { trackId: string }) => {
        addTrackToTimeline(item.trackId);
      },
      canDrop: (item: { trackId: string }) => {
        return !validTimelineTracks.includes(item.trackId);
      },
      collect: (monitor) => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    [validTimelineTracks, addTrackToTimeline]
  );

  const handleTrackClick = (track: Track) => {
    if (selection.type === 'track' && selection.id === track.id) {
      setSelection(null, null, null);
    } else {
      setSelection('track', track.id, track);
    }
  };

  const handleTransitionClick = (transition: Transition) => {
    if (selection.type === 'transition' && selection.id === transition.id) {
      setSelection(null, null, null);
    } else {
      setSelection('transition', transition.id, transition);
    }
  };

  const handleMoveTrack = (fromIndex: number, toIndex: number) => {
    moveTrackInTimeline(fromIndex, toIndex);
  };

  const handleRemoveTrack = (trackId: string) => {
    removeTrackFromTimeline(trackId);
    if (selection.type === 'track' && selection.id === trackId) {
      setSelection(null, null, null);
    }
  };

  const analyzedTracks = project.tracks.filter((t) => t.analysis);
  const canAutoArrange = analyzedTracks.length >= 2;

  // Calculate total duration
  const totalDuration = validTimelineTracks.reduce((acc, trackId) => {
    const track = tracksMap.get(trackId);
    return acc + (track?.duration || 0);
  }, 0);

  const formatTotalDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Empty state
  if (validTimelineTracks.length === 0) {
    return (
      <div
        ref={drop}
        className={cn(
          'h-full flex items-center justify-center rounded-lg border border-dashed transition-all',
          isOver && canDrop
            ? 'border-primary bg-primary/5'
            : 'border-border/50 bg-muted/20'
        )}
      >
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-3">
              Drag tracks here or use auto-arrange
            </p>
            {canAutoArrange && (
              <Button
                variant="outline"
                size="sm"
                onClick={onAutoArrange}
                disabled={isOrdering}
                className="gap-2"
              >
                {isOrdering ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                Auto-arrange {analyzedTracks.length} tracks
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={drop}
      className={cn(
        'h-full flex flex-col rounded-lg border border-border/30 bg-muted/10 transition-all overflow-hidden',
        isOver && canDrop && 'ring-2 ring-primary border-primary/50'
      )}
    >
      {/* Compact Timeline Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border/30 bg-muted/30 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-muted-foreground">
            {validTimelineTracks.length} tracks
          </span>
          <span className="text-xs text-muted-foreground/60">•</span>
          <span className="text-xs font-mono text-muted-foreground">
            {formatTotalDuration(totalDuration)}
          </span>
        </div>
        {canAutoArrange && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onAutoArrange}
            disabled={isOrdering}
            className="h-6 px-2 text-xs gap-1.5"
          >
            {isOrdering ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Sparkles className="w-3 h-3" />
            )}
            Auto-arrange
          </Button>
        )}
      </div>

      {/* Timeline Track Lane */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden scrollbar-studio">
        <div className="flex items-center gap-0 px-6 py-3 min-h-full">
          <AnimatePresence mode="popLayout">
            {validTimelineTracks.map((trackId, index) => {
              const track = tracksMap.get(trackId);
              if (!track) return null;

              const nextTrackId = validTimelineTracks[index + 1];
              const transition = nextTrackId
                ? transitionsMap.get(`${trackId}-${nextTrackId}`)
                : null;

              return (
                <motion.div
                  key={trackId}
                  layout
                  initial={{ opacity: 0, scale: 0.9, x: -20 }}
                  animate={{ opacity: 1, scale: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="flex items-center"
                >
                  <TimelineTrack
                    track={track}
                    index={index}
                    isSelected={selection.type === 'track' && selection.id === trackId}
                    onClick={() => handleTrackClick(track)}
                    onRemove={() => handleRemoveTrack(trackId)}
                    onMove={handleMoveTrack}
                  />

                  {/* Transition Indicator (not after last track) */}
                  {index < validTimelineTracks.length - 1 && (
                    <TransitionIndicator
                      transition={transition || null}
                      isSelected={
                        selection.type === 'transition' &&
                        selection.id === transition?.id
                      }
                      onClick={() => transition && handleTransitionClick(transition)}
                    />
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Drop zone at end */}
          <div
            className={cn(
              'flex items-center justify-center w-12 h-12 rounded border-2 border-dashed ml-2 transition-all',
              isOver && canDrop
                ? 'border-primary bg-primary/10'
                : 'border-border/30 hover:border-border/50'
            )}
          >
            <Plus className={cn(
              'w-4 h-4 transition-colors',
              isOver && canDrop ? 'text-primary' : 'text-muted-foreground/30'
            )} />
          </div>
        </div>
      </div>
    </div>
  );
}
