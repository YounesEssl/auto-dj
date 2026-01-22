import { useDrag } from 'react-dnd';
import { Music, Loader2, AlertCircle, Trash2 } from 'lucide-react';

import { cn } from '@autodj/ui';
import type { Track } from '@/services/projects.service';

export const TRACK_DND_TYPE = 'TRACK';

interface TrackMiniCardProps {
  track: Track;
  isSelected?: boolean;
  isInTimeline?: boolean;
  onClick?: () => void;
  onDelete?: () => void;
}

/**
 * Compact track card for the track pool
 * Shows cover art, track info, and is draggable to the timeline
 */
export function TrackMiniCard({ track, isSelected, isInTimeline, onClick, onDelete }: TrackMiniCardProps) {
  const [{ isDragging }, drag] = useDrag(
    () => ({
      type: TRACK_DND_TYPE,
      item: { trackId: track.id },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
      canDrag: !isInTimeline && !!track.analysis,
    }),
    [track.id, isInTimeline, track.analysis]
  );

  const isAnalyzing = !track.analysis;
  const analysis = track.analysis;

  // Parse track name - try to extract artist and title from filename
  const filename = track.originalName.replace(/\.[^/.]+$/, '');
  const hasMetadata = track.metadata?.artist || track.metadata?.title;

  const displayTitle = hasMetadata
    ? track.metadata?.title || filename
    : filename;

  const displayArtist = hasMetadata
    ? track.metadata?.artist
    : null;

  const coverUrl = track.metadata?.coverUrl;

  return (
    <div
      ref={drag}
      onClick={onClick}
      className={cn(
        'studio-panel rounded-lg overflow-hidden cursor-pointer transition-all w-[140px] flex-shrink-0 group',
        isDragging && 'opacity-50 scale-95',
        isSelected && 'ring-2 ring-primary',
        isInTimeline && 'opacity-50 cursor-not-allowed',
        !isInTimeline && track.analysis && 'hover:ring-1 hover:ring-primary/50'
      )}
    >
      {/* Cover Art */}
      <div className="relative aspect-square bg-gradient-to-br from-muted/50 to-muted">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={displayTitle}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Music className="w-10 h-10 text-muted-foreground/50" />
          </div>
        )}

        {/* Analyzing overlay */}
        {isAnalyzing && (
          <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
            <div className="flex flex-col items-center gap-1">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <span className="text-xs text-accent">Analyzing</span>
            </div>
          </div>
        )}

        {/* In Timeline badge */}
        {isInTimeline && (
          <div className="absolute inset-0 bg-background/60 flex items-center justify-center">
            <span className="text-xs text-muted-foreground bg-muted/80 px-2 py-1 rounded">
              In timeline
            </span>
          </div>
        )}

        {/* Warning indicator */}
        {analysis?.mixabilityWarnings && analysis.mixabilityWarnings.length > 0 && (
          <div className="absolute top-1 right-1">
            <AlertCircle className="w-4 h-4 text-destructive drop-shadow-md" />
          </div>
        )}

        {/* Delete button (shown on hover) */}
        {onDelete && !isInTimeline && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="absolute top-1 left-1 p-1.5 rounded-full bg-background/80 text-muted-foreground hover:text-destructive hover:bg-destructive/20 opacity-0 group-hover:opacity-100 transition-all"
            title="Delete track"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Track Info */}
      <div className="p-2 space-y-1">
        {/* Title */}
        <p className="text-xs font-medium truncate leading-tight" title={displayTitle}>
          {displayTitle}
        </p>

        {/* Artist */}
        {displayArtist && (
          <p className="text-xs text-muted-foreground truncate" title={displayArtist}>
            {displayArtist}
          </p>
        )}

        {/* Analysis Data */}
        {analysis && (
          <div className="flex items-center gap-2 pt-1">
            {/* BPM */}
            <span className="text-xs font-mono bg-muted/50 px-1.5 py-0.5 rounded">
              {Math.round(analysis.bpm)}
            </span>

            {/* Key */}
            <span className="text-xs font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded">
              {analysis.camelot}
            </span>

            {/* Energy */}
            <span className={cn(
              'text-xs font-mono px-1.5 py-0.5 rounded',
              analysis.energy >= 0.7 ? 'bg-destructive/20 text-destructive' :
              analysis.energy >= 0.4 ? 'bg-primary/20 text-primary' :
              'bg-success/20 text-success'
            )}>
              {Math.round(analysis.energy * 100)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
