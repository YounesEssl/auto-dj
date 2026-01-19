import { Music, Trash2, Clock, GripVertical } from 'lucide-react';
import { toast } from 'sonner';
import { useMemo } from 'react';

import { Button, cn } from '@autodj/ui';
import type { Track, Transition } from '@/services/projects.service';
import { projectsService } from '@/services/projects.service';
import { useProjectStore } from '@/stores/projectStore';
import { TrackAnalysisCard } from './TrackAnalysisCard';
import { TransitionIndicator } from './TransitionIndicator';

interface TrackListProps {
  tracks: Track[];
  projectId: string;
  orderedTrackIds?: string[];
  transitions?: Transition[];
}

/**
 * Format duration in seconds to mm:ss
 */
function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format file size in bytes to human readable
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Track list component with analysis status and transition indicators
 */
export function TrackList({ tracks, projectId, orderedTrackIds, transitions }: TrackListProps) {
  const { fetchProject } = useProjectStore();

  // Sort tracks by order if orderedTrackIds is available
  const sortedTracks = useMemo(() => {
    if (!orderedTrackIds || orderedTrackIds.length === 0) {
      return tracks;
    }

    // Create a map for quick lookup
    const trackMap = new Map(tracks.map(t => [t.id, t]));

    // Sort by orderedTrackIds, keeping tracks not in the order at the end
    const ordered: Track[] = [];
    const unordered: Track[] = [];

    for (const id of orderedTrackIds) {
      const track = trackMap.get(id);
      if (track) {
        ordered.push(track);
        trackMap.delete(id);
      }
    }

    // Add remaining tracks that weren't in orderedTrackIds
    for (const track of trackMap.values()) {
      unordered.push(track);
    }

    return [...ordered, ...unordered];
  }, [tracks, orderedTrackIds]);

  // Create transition map for quick lookup
  const transitionMap = useMemo(() => {
    if (!transitions) return new Map<string, Transition>();
    return new Map(transitions.map(t => [`${t.fromTrackId}-${t.toTrackId}`, t]));
  }, [transitions]);

  const handleDelete = async (trackId: string) => {
    if (!confirm('Are you sure you want to delete this track?')) return;

    try {
      await projectsService.deleteTrack(projectId, trackId);
      toast.success('Track deleted');
      fetchProject(projectId);
    } catch {
      toast.error('Failed to delete track');
    }
  };

  if (tracks.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Music className="mx-auto h-12 w-12 mb-4 opacity-50" />
        <p>No tracks uploaded yet</p>
      </div>
    );
  }

  const hasOrder = orderedTrackIds && orderedTrackIds.length > 0;

  return (
    <div className="space-y-0">
      {sortedTracks.map((track, index) => {
        // Find transition to next track
        const nextTrack = sortedTracks[index + 1];
        const transition = nextTrack
          ? transitionMap.get(`${track.id}-${nextTrack.id}`)
          : undefined;

        const isOrdered = orderedTrackIds?.includes(track.id);

        return (
          <div key={track.id}>
            {/* Track card */}
            <div
              className={cn(
                'flex items-center gap-4 p-4 rounded-lg border bg-card',
                hasOrder && !isOrdered && 'opacity-60'
              )}
            >
              {/* Order indicator */}
              <div className="flex-shrink-0 flex items-center gap-2">
                {hasOrder && (
                  <GripVertical className="h-4 w-4 text-muted-foreground" />
                )}
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                  isOrdered ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                )}>
                  {hasOrder ? (orderedTrackIds?.indexOf(track.id) ?? -1) + 1 || '-' : index + 1}
                </div>
              </div>

              {/* Track info */}
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{track.originalName}</p>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{formatDuration(track.duration)}</span>
                  <span>{formatFileSize(track.fileSize)}</span>
                </div>
              </div>

              {/* Analysis data or loading */}
              {track.analysis ? (
                <TrackAnalysisCard analysis={track.analysis} duration={track.duration} />
              ) : (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-4 w-4 animate-pulse" />
                  <span className="text-sm">Analyzing...</span>
                </div>
              )}

              {/* Delete button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(track.id)}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>

            {/* Transition indicator (if there's a next track and transition data) */}
            {transition && (
              <TransitionIndicator transition={transition} />
            )}
          </div>
        );
      })}
    </div>
  );
}
