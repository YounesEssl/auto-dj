import { useDrag, useDrop } from 'react-dnd';
import { GripVertical, X } from 'lucide-react';

import { cn } from '@autodj/ui';
import type { Track } from '@/services/projects.service';
import { TRACK_DND_TYPE } from './TrackMiniCard';

const TIMELINE_TRACK_TYPE = 'TIMELINE_TRACK';

interface TimelineTrackProps {
  track: Track;
  index: number;
  isSelected?: boolean;
  onClick?: () => void;
  onRemove?: () => void;
  onMove?: (fromIndex: number, toIndex: number) => void;
}

interface DragItem {
  type: string;
  index: number;
  trackId: string;
}

/**
 * Compact track block in the timeline, draggable for reordering
 */
export function TimelineTrack({
  track,
  index,
  isSelected,
  onClick,
  onRemove,
  onMove,
}: TimelineTrackProps) {
  const [{ isDragging }, drag, preview] = useDrag(
    () => ({
      type: TIMELINE_TRACK_TYPE,
      item: { type: TIMELINE_TRACK_TYPE, index, trackId: track.id },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    }),
    [index, track.id]
  );

  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: [TIMELINE_TRACK_TYPE, TRACK_DND_TYPE],
      hover: (item: DragItem, monitor) => {
        if (!monitor.isOver({ shallow: true })) return;
        if (item.type !== TIMELINE_TRACK_TYPE) return;
        if (item.index === index) return;

        onMove?.(item.index, index);
        item.index = index;
      },
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop(),
      }),
    }),
    [index, onMove]
  );

  const analysis = track.analysis;
  const duration = track.duration ? formatDuration(track.duration) : '--:--';
  const trackName = track.originalName.replace(/\.[^/.]+$/, '');

  return (
    <div
      ref={(node) => {
        preview(drop(node));
      }}
      onClick={onClick}
      className={cn(
        'relative rounded transition-all cursor-pointer group',
        'flex items-center h-12 min-w-[140px] max-w-[200px]',
        'bg-gradient-to-r from-muted/80 to-muted/40',
        'border border-border/50',
        isDragging && 'opacity-50 scale-95',
        isSelected && 'ring-2 ring-primary border-primary/50',
        isOver && canDrop && 'ring-2 ring-accent',
        !isDragging && !isSelected && 'hover:border-primary/30 hover:from-muted hover:to-muted/60'
      )}
    >
      {/* Track number badge */}
      <div className="absolute -left-2.5 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center">
        <span className="text-[10px] font-bold text-muted-foreground">{index + 1}</span>
      </div>

      {/* Drag Handle */}
      <div
        ref={drag}
        className="cursor-grab active:cursor-grabbing px-2 h-full flex items-center hover:bg-muted/50"
      >
        <GripVertical className="w-3 h-3 text-muted-foreground/50" />
      </div>

      {/* Track Info - Compact */}
      <div className="flex-1 min-w-0 pr-2 py-1.5">
        <p className="text-xs font-medium truncate leading-tight" title={trackName}>
          {trackName}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[10px] font-mono text-muted-foreground">{duration}</span>
          {analysis && (
            <>
              <span className="text-[10px] font-mono text-muted-foreground">{Math.round(analysis.bpm)}</span>
              <span className="text-[10px] font-mono text-accent font-semibold">{analysis.camelot}</span>
            </>
          )}
        </div>
      </div>

      {/* Remove Button - Shows on hover */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove?.();
        }}
        className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-background border border-border flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-destructive hover:border-destructive hover:text-destructive-foreground transition-all"
      >
        <X className="w-3 h-3" />
      </button>

      {/* Waveform-like decoration */}
      <div className="absolute bottom-0 left-0 right-0 h-1 overflow-hidden rounded-b opacity-50">
        <div className="h-full bg-gradient-to-r from-primary/30 via-accent/30 to-primary/30" />
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
