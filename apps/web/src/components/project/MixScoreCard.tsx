import { Music, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { useState } from 'react';

import { Card, CardContent, CardHeader, CardTitle, Button, cn } from '@autodj/ui';
import { projectsService, type Project } from '@/services/projects.service';
import { useProjectStore } from '@/stores/projectStore';

interface MixScoreCardProps {
  project: Project;
}

/**
 * Get score grade based on value
 */
function getScoreGrade(score: number): { grade: string; color: string; description: string } {
  if (score >= 85) return { grade: 'A', color: 'text-green-500', description: 'Excellent mix flow' };
  if (score >= 70) return { grade: 'B', color: 'text-green-400', description: 'Good mix flow' };
  if (score >= 55) return { grade: 'C', color: 'text-yellow-500', description: 'Decent mix flow' };
  if (score >= 40) return { grade: 'D', color: 'text-orange-500', description: 'Some rough transitions' };
  return { grade: 'F', color: 'text-red-500', description: 'Needs different tracks' };
}

/**
 * Mix score display card with global score and recalculate button
 */
export function MixScoreCard({ project }: MixScoreCardProps) {
  const [isRecalculating, setIsRecalculating] = useState(false);
  const { fetchProject } = useProjectStore();

  const score = project.averageMixScore ?? 0;
  const { grade, color, description } = getScoreGrade(score);
  const transitionCount = project.transitions?.length ?? 0;
  const analyzedCount = project.tracks.filter(t => t.analysis).length;

  const handleRecalculate = async () => {
    setIsRecalculating(true);
    try {
      await projectsService.calculateOrder(project.id);
      toast.success('Track order recalculated');
      await fetchProject(project.id);
    } catch {
      toast.error('Failed to recalculate order');
    } finally {
      setIsRecalculating(false);
    }
  };

  // Don't show if less than 2 analyzed tracks
  if (analyzedCount < 2) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Music className="h-4 w-4" />
            Mix Quality
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRecalculate}
            disabled={isRecalculating}
            className="h-8 px-2"
          >
            <RefreshCw className={cn('h-4 w-4 mr-1', isRecalculating && 'animate-spin')} />
            Recalculate
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Score circle */}
          <div className="relative w-16 h-16">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                className="text-muted"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeDasharray={`${score}, 100`}
                className={color}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={cn('text-xl font-bold', color)}>{grade}</span>
            </div>
          </div>

          {/* Score details */}
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className={cn('text-2xl font-bold', color)}>{score}</span>
              <span className="text-sm text-muted-foreground">/ 100</span>
            </div>
            <p className="text-sm text-muted-foreground">{description}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {transitionCount} transition{transitionCount !== 1 ? 's' : ''} analyzed
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
