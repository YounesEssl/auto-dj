import { AlertTriangle, Check, Loader2, ChevronRight } from 'lucide-react';

import { cn } from '@autodj/ui';
import type { Transition } from '@/services/projects.service';

interface TransitionIndicatorProps {
  transition: Transition | null;
  isSelected?: boolean;
  onClick?: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-success';
  if (score >= 60) return 'text-primary';
  if (score >= 40) return 'text-warning';
  return 'text-destructive';
}

function getScoreBorderColor(score: number): string {
  if (score >= 80) return 'border-success/50';
  if (score >= 60) return 'border-primary/50';
  if (score >= 40) return 'border-warning/50';
  return 'border-destructive/50';
}

/**
 * Compact transition indicator between tracks
 */
export function TransitionIndicator({ transition, isSelected, onClick }: TransitionIndicatorProps) {
  // No transition calculated yet
  if (!transition) {
    return (
      <div className="flex items-center justify-center w-8 h-12">
        <ChevronRight className="w-4 h-4 text-muted-foreground/30" />
      </div>
    );
  }

  const isProcessing = transition.audioStatus === 'PROCESSING';
  const isCompleted = transition.audioStatus === 'COMPLETED';
  const isError = transition.audioStatus === 'ERROR';

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center justify-center w-10 h-12 transition-all group',
        isSelected && 'scale-110'
      )}
    >
      <div
        className={cn(
          'relative flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all',
          'bg-background/80 backdrop-blur-sm',
          isSelected ? 'ring-2 ring-primary ring-offset-1 ring-offset-background' : 'hover:scale-110',
          getScoreBorderColor(transition.score)
        )}
      >
        {/* Score or status */}
        {isProcessing ? (
          <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
        ) : isError ? (
          <AlertTriangle className="w-3.5 h-3.5 text-destructive" />
        ) : (
          <span className={cn('text-[10px] font-bold tabular-nums', getScoreColor(transition.score))}>
            {Math.round(transition.score)}
          </span>
        )}

        {/* Completed checkmark badge */}
        {isCompleted && !isProcessing && !isError && (
          <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-success flex items-center justify-center">
            <Check className="w-2 h-2 text-success-foreground" />
          </div>
        )}
      </div>
    </button>
  );
}
