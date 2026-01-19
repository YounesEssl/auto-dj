import { Link } from 'react-router-dom';
import { Music, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, cn } from '@autodj/ui';
import type { Project } from '@/services/projects.service';

interface ProjectCardProps {
  project: Project;
}

const statusConfig: Record<
  string,
  { icon: typeof Music; label: string; color: string }
> = {
  CREATED: { icon: Clock, label: 'Created', color: 'text-muted-foreground' },
  UPLOADING: { icon: Loader2, label: 'Uploading', color: 'text-blue-500' },
  ANALYZING: { icon: Loader2, label: 'Analyzing', color: 'text-blue-500' },
  ORDERING: { icon: Loader2, label: 'Ordering', color: 'text-blue-500' },
  MIXING: { icon: Loader2, label: 'Mixing', color: 'text-purple-500' },
  COMPLETED: { icon: CheckCircle2, label: 'Completed', color: 'text-green-500' },
  FAILED: { icon: XCircle, label: 'Failed', color: 'text-destructive' },
};

/**
 * Project card component for dashboard grid
 */
export function ProjectCard({ project }: ProjectCardProps) {
  const config = statusConfig[project.status] ?? statusConfig.CREATED!;
  const StatusIcon = config.icon;
  const isLoading = ['UPLOADING', 'ANALYZING', 'ORDERING', 'MIXING'].includes(
    project.status
  );

  return (
    <Link to={`/projects/${project.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg truncate">{project.name}</CardTitle>
            <StatusIcon
              className={cn(
                'h-5 w-5 flex-shrink-0',
                config.color,
                isLoading && 'animate-spin'
              )}
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Music className="h-4 w-4" />
              <span>{project._count?.tracks || project.tracks?.length || 0} tracks</span>
            </div>
            <span className={cn('font-medium', config.color)}>{config.label}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {new Date(project.createdAt).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
