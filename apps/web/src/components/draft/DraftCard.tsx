import { Link } from 'react-router-dom';
import { Music2, Clock, CheckCircle2, XCircle, Loader2, ArrowRight } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, cn } from '@autodj/ui';
import type { Draft } from '@/services/drafts.service';

interface DraftCardProps {
  draft: Draft;
}

const statusConfig: Record<
  string,
  { icon: typeof Music2; label: string; color: string }
> = {
  CREATED: { icon: Clock, label: 'Created', color: 'text-muted-foreground' },
  UPLOADING: { icon: Loader2, label: 'Uploading', color: 'text-blue-500' },
  ANALYZING: { icon: Loader2, label: 'Analyzing', color: 'text-blue-500' },
  READY: { icon: CheckCircle2, label: 'Ready', color: 'text-green-500' },
  GENERATING: { icon: Loader2, label: 'Generating', color: 'text-purple-500' },
  COMPLETED: { icon: CheckCircle2, label: 'Completed', color: 'text-green-500' },
  FAILED: { icon: XCircle, label: 'Failed', color: 'text-destructive' },
};

/**
 * Draft card component for drafts list grid
 */
export function DraftCard({ draft }: DraftCardProps) {
  const config = statusConfig[draft.status] ?? statusConfig.CREATED!;
  const StatusIcon = config.icon;
  const isLoading = ['UPLOADING', 'ANALYZING', 'GENERATING'].includes(draft.status);

  const trackAName = draft.trackA?.originalName || 'Track A';
  const trackBName = draft.trackB?.originalName || 'Track B';
  const hasTracksInfo = draft.trackA || draft.trackB;

  return (
    <Link to={`/drafts/${draft.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg truncate">{draft.name}</CardTitle>
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
          {hasTracksInfo ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="truncate max-w-[100px]">
                {draft.trackA ? trackAName.slice(0, 15) + (trackAName.length > 15 ? '...' : '') : '---'}
              </span>
              <ArrowRight className="h-3 w-3 flex-shrink-0" />
              <span className="truncate max-w-[100px]">
                {draft.trackB ? trackBName.slice(0, 15) + (trackBName.length > 15 ? '...' : '') : '---'}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Music2 className="h-4 w-4" />
              <span>No tracks uploaded</span>
            </div>
          )}

          <div className="flex items-center justify-between mt-2">
            <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
            {draft.compatibilityScore !== null && (
              <span className="text-sm text-muted-foreground">
                Score: {draft.compatibilityScore}%
              </span>
            )}
          </div>

          <p className="text-xs text-muted-foreground mt-2">
            {new Date(draft.createdAt).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
