import { Loader2, CheckCircle2, Music2, Scissors, Clock, Sliders, FileAudio } from 'lucide-react';
import type { DraftProgress as DraftProgressType } from '@autodj/shared-types';

import { Card, CardHeader, CardTitle, CardContent, cn } from '@autodj/ui';

interface DraftProgressProps {
  progress: DraftProgressType | null;
}

const stepConfig: Record<
  string,
  { icon: typeof Loader2; label: string; description: string }
> = {
  extraction: {
    icon: Scissors,
    label: 'Extracting Segments',
    description: 'Extracting outro from Track A and intro from Track B',
  },
  stems: {
    icon: Music2,
    label: 'Separating Stems',
    description: 'Using AI to separate drums, bass, vocals, and other instruments',
  },
  'time-stretch': {
    icon: Clock,
    label: 'Time Stretching',
    description: 'Matching BPM between tracks',
  },
  beatmatch: {
    icon: Music2,
    label: 'Beat Matching',
    description: 'Aligning beats for seamless transition',
  },
  mixing: {
    icon: Sliders,
    label: 'Mixing',
    description: 'Applying 4-phase stem mixing with volume curves',
  },
  eq: {
    icon: Sliders,
    label: 'Applying EQ',
    description: 'Progressive EQ filtering for smooth frequency transition',
  },
  export: {
    icon: FileAudio,
    label: 'Exporting',
    description: 'Finalizing and exporting the transition audio',
  },
};

const stepOrder = ['extraction', 'stems', 'time-stretch', 'beatmatch', 'mixing', 'eq', 'export'];

/**
 * Progress indicator for draft transition generation
 */
export function DraftProgress({ progress }: DraftProgressProps) {
  if (!progress) return null;

  const currentStepIndex = stepOrder.indexOf(progress.step);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generating Transition</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-medium">{progress.progress}%</span>
          </div>
          <div className="h-3 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {stepOrder.map((step, index) => {
            const config = stepConfig[step]!;
            const StepIcon = config.icon;
            const isActive = step === progress.step;
            const isComplete = index < currentStepIndex;
            const isPending = index > currentStepIndex;

            return (
              <div
                key={step}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg transition-colors',
                  isActive && 'bg-primary/10',
                  isComplete && 'bg-green-500/10',
                  isPending && 'opacity-50'
                )}
              >
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  isComplete && 'bg-green-500/20 text-green-500',
                  isActive && 'bg-primary/20 text-primary',
                  isPending && 'bg-muted text-muted-foreground'
                )}>
                  {isComplete ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <StepIcon className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={cn(
                    'font-medium text-sm',
                    isActive && 'text-primary',
                    isComplete && 'text-green-600 dark:text-green-400'
                  )}>
                    {config.label}
                  </p>
                  {isActive && (
                    <p className="text-xs text-muted-foreground">{config.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Message */}
        {progress.message && (
          <p className="text-sm text-muted-foreground text-center">
            {progress.message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
