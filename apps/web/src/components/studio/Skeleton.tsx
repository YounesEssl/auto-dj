import { cn } from '@autodj/ui';

interface SkeletonProps {
  className?: string;
}

function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded bg-muted/50',
        className
      )}
    />
  );
}

/**
 * Skeleton for a track mini card in the track pool
 */
export function TrackMiniCardSkeleton() {
  return (
    <div className="w-28 h-36 flex-shrink-0 rounded-lg bg-card/50 border border-border/30 p-2">
      {/* Cover art */}
      <Skeleton className="aspect-square w-full rounded-md mb-2" />
      {/* Title */}
      <Skeleton className="h-3 w-full mb-1" />
      {/* BPM / Key */}
      <div className="flex gap-1">
        <Skeleton className="h-2.5 w-8" />
        <Skeleton className="h-2.5 w-8" />
      </div>
    </div>
  );
}

/**
 * Skeleton for the track pool area
 */
export function TrackPoolSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-8 w-28" />
      </div>
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 6 }).map((_, i) => (
          <TrackMiniCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for a timeline track
 */
export function TimelineTrackSkeleton() {
  return (
    <div className="h-20 flex-1 min-w-48 rounded-lg bg-card/30 border border-border/30 p-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded" />
        <div className="flex-1">
          <Skeleton className="h-4 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

/**
 * Skeleton for the timeline area
 */
export function TimelineSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <Skeleton className="h-5 w-20" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-24" />
        </div>
      </div>
      <div className="flex-1 flex items-center gap-4 overflow-hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <TimelineTrackSkeleton />
            {i < 3 && <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for the inspector panel
 */
export function InspectorSkeleton() {
  return (
    <div className="p-3 space-y-4">
      {/* Cover art */}
      <Skeleton className="aspect-square w-full rounded-lg" />
      {/* Title */}
      <div className="space-y-1">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-16 rounded-lg" />
        <Skeleton className="h-16 rounded-lg" />
      </div>
      {/* Bars */}
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-8" />
            </div>
            <Skeleton className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for mix list items
 */
export function MixListSkeleton() {
  return (
    <div className="space-y-1 p-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg"
        >
          <Skeleton className="w-2.5 h-2.5 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-4 w-24 mb-1" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Full studio loading skeleton
 */
export function StudioSkeleton() {
  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden animate-in fade-in duration-300">
      {/* Header Skeleton */}
      <header className="h-14 border-b border-border bg-card/50 flex items-center px-4 gap-4">
        <Skeleton className="w-5 h-5" />
        <Skeleton className="w-20 h-4" />
        <div className="w-px h-6 bg-border" />
        <Skeleton className="h-4 w-32" />
        <div className="flex-1" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-28" />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 h-full border-r border-border bg-card/30 p-2">
          <Skeleton className="h-8 w-full mb-3" />
          <MixListSkeleton />
        </aside>

        {/* Main Workspace */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Track Pool */}
          <div className="h-72 border-b border-border p-3">
            <TrackPoolSkeleton />
          </div>

          {/* Timeline */}
          <div className="flex-1 p-3">
            <TimelineSkeleton />
          </div>
        </main>

        {/* Inspector */}
        <aside className="w-64 h-full border-l border-border bg-card/30">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-4" />
          </div>
          <InspectorSkeleton />
        </aside>
      </div>

      {/* Player Bar Skeleton */}
      <footer className="h-20 border-t border-border/50 bg-card/95 flex items-center px-4 gap-4">
        <Skeleton className="w-12 h-12 rounded" />
        <div className="w-48">
          <Skeleton className="h-4 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </div>
        <div className="flex-1 flex flex-col gap-1.5">
          <Skeleton className="h-8 w-full rounded" />
          <div className="flex items-center justify-center gap-2">
            <Skeleton className="w-7 h-7 rounded" />
            <Skeleton className="w-7 h-7 rounded" />
            <Skeleton className="w-9 h-9 rounded-full" />
            <Skeleton className="w-7 h-7 rounded" />
            <Skeleton className="w-7 h-7 rounded" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-7 h-7 rounded" />
          <Skeleton className="w-20 h-2 rounded-full" />
        </div>
      </footer>
    </div>
  );
}

export { Skeleton };
