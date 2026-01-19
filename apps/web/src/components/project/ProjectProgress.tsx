import { Loader2, CheckCircle2 } from 'lucide-react';
import type { JobProgress } from '@autodj/shared-types';

import { Card, CardContent, Progress, cn } from '@autodj/ui';
import type { Project } from '@/services/projects.service';

interface ProjectProgressProps {
  project: Project;
  progress: JobProgress | null;
}

const stageLabels: Record<string, string> = {
  analyzing: 'Analyzing tracks',
  ordering: 'Calculating optimal order',
  ready: 'Ready to generate mix!',
  mixing: 'Generating mix',
  completed: 'Complete',
  failed: 'Failed',
};

/**
 * Project progress indicator component
 */
export function ProjectProgress({ project, progress }: ProjectProgressProps) {
  const currentStage = progress?.stage || project.status.toLowerCase();
  const currentProgress = progress?.progress || 0;
  const currentStep = progress?.currentStep || stageLabels[currentStage] || 'Processing...';
  const isReady = currentStage === 'ready';
  const isCompleted = currentStage === 'completed';

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isReady || isCompleted ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              <span className="font-medium">{currentStep}</span>
            </div>
            <span className="text-sm text-muted-foreground">{currentProgress}%</span>
          </div>

          <Progress value={currentProgress} className="h-2" />

          {/* Stage indicators */}
          <div className="flex justify-between text-xs">
            {['analyzing', 'ordering', 'mixing', 'completed'].map((stage, index) => {
              const stages = ['analyzing', 'ordering', 'mixing', 'completed'];
              // Map 'ready' to after 'ordering' for display purposes
              const displayStage = currentStage === 'ready' ? 'ordering' : currentStage;
              const currentIndex = stages.indexOf(displayStage);
              const isComplete = index < currentIndex || (currentStage === 'ready' && index <= 1);
              const isCurrent = stage === displayStage || (stage === 'ordering' && currentStage === 'ready');

              return (
                <div
                  key={stage}
                  className={cn(
                    'flex flex-col items-center',
                    isComplete && 'text-primary',
                    isCurrent && 'text-primary font-medium',
                    !isComplete && !isCurrent && 'text-muted-foreground'
                  )}
                >
                  <div
                    className={cn(
                      'w-3 h-3 rounded-full mb-1',
                      isComplete && 'bg-primary',
                      isCurrent && (currentStage === 'ready' ? 'bg-green-500' : 'bg-primary animate-pulse'),
                      !isComplete && !isCurrent && 'bg-muted'
                    )}
                  />
                  <span className="capitalize">{stage === 'ordering' && currentStage === 'ready' ? 'Ready' : stage}</span>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
