import { useState } from 'react';
import { Music, ArrowRight, RefreshCw, Loader2, AlertCircle, Check, X, Trash2, Calendar, Disc, Play } from 'lucide-react';
import { toast } from 'sonner';

import { cn } from '@autodj/ui';
import { Button } from '@autodj/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@autodj/ui';
import type { Track, Transition } from '@/services/projects.service';
import { projectsService } from '@/services/projects.service';
import { useStudioStore } from '@/stores/studioStore';
import { useProjectStore } from '@/stores/projectStore';

interface InspectorProps {
  projectId: string;
}

function getEnergyLabel(energy: number): string {
  if (energy >= 0.8) return 'Very High';
  if (energy >= 0.6) return 'High';
  if (energy >= 0.4) return 'Medium';
  if (energy >= 0.2) return 'Low';
  return 'Very Low';
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-success';
  if (score >= 60) return 'text-primary';
  if (score >= 40) return 'text-warning';
  return 'text-destructive';
}

function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-success';
  if (score >= 60) return 'bg-primary';
  if (score >= 40) return 'bg-warning';
  return 'bg-destructive';
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn('font-medium', getScoreColor(score))}>{Math.round(score)}%</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', getScoreBg(score))}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function TrackInspector({ track, projectId }: { track: Track; projectId: string }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { fetchProject } = useProjectStore();
  const { setSelection, removeTrackFromTimeline, setIsPlaying, isPlaying } = useStudioStore();
  const analysis = track.analysis;
  const metadata = track.metadata;

  // Display info
  const displayTitle = metadata?.title || track.originalName.replace(/\.[^/.]+$/, '');
  const displayArtist = metadata?.artist;
  const coverUrl = metadata?.coverUrl;

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await projectsService.deleteTrack(projectId, track.id);
      removeTrackFromTimeline(track.id);
      setSelection(null, null, null);
      await fetchProject(projectId);
      toast.success('Track deleted');
    } catch {
      toast.error('Failed to delete track');
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handlePlayTrack = () => {
    // Toggle playback - the PlayerBar will handle the actual audio
    setIsPlaying(!isPlaying);
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Cover Art with Play overlay */}
        <div className="relative aspect-square rounded-lg overflow-hidden bg-muted/50 group">
          {coverUrl ? (
            <img
              src={coverUrl}
              alt={displayTitle}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-accent/5">
              <Music className="w-12 h-12 text-muted-foreground/30" />
            </div>
          )}
          {/* Play overlay */}
          <button
            onClick={handlePlayTrack}
            className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center btn-glow">
              <Play className="w-5 h-5 text-primary-foreground ml-0.5" />
            </div>
          </button>
        </div>

        {/* Track Info */}
        <div className="space-y-1">
          <h3 className="font-semibold text-sm truncate" title={displayTitle}>
            {displayTitle}
          </h3>
          {displayArtist && (
            <p className="text-sm text-muted-foreground truncate" title={displayArtist}>
              {displayArtist}
            </p>
          )}
        </div>

        {/* Metadata Details */}
        {(metadata?.album || metadata?.genre || metadata?.year) && (
          <div className="studio-panel rounded-lg p-3 space-y-2">
            {metadata?.album && (
              <div className="flex items-center gap-2 text-xs">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Disc className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  </TooltipTrigger>
                  <TooltipContent>Album</TooltipContent>
                </Tooltip>
                <span className="truncate text-muted-foreground" title={metadata.album}>
                  {metadata.album}
                </span>
              </div>
            )}
            {metadata?.genre && (
              <div className="flex items-center gap-2 text-xs">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Music className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  </TooltipTrigger>
                  <TooltipContent>Genre</TooltipContent>
                </Tooltip>
                <span className="truncate text-muted-foreground">{metadata.genre}</span>
              </div>
            )}
            {metadata?.year && (
              <div className="flex items-center gap-2 text-xs">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Calendar className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  </TooltipTrigger>
                  <TooltipContent>Year</TooltipContent>
                </Tooltip>
                <span className="text-muted-foreground">{metadata.year}</span>
              </div>
            )}
          </div>
        )}

        {/* Duration & File Info */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{track.duration ? formatDuration(track.duration) : 'Duration unknown'}</span>
          <span className="font-mono">{formatFileSize(track.fileSize)}</span>
        </div>

      {analysis ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="studio-panel rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">BPM</p>
              <p className="text-xl font-bold font-mono">{Math.round(analysis.bpm)}</p>
            </div>
            <div className="studio-panel rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">Key</p>
              <p className="text-xl font-bold font-mono text-accent">{analysis.camelot}</p>
              <p className="text-xs text-muted-foreground">{analysis.key}</p>
            </div>
          </div>

          {/* Analysis Bars */}
          <div className="space-y-3">
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Energy</span>
                <span className="font-medium">{getEnergyLabel(analysis.energy)}</span>
              </div>
              <div className="h-1.5 vu-meter rounded-full overflow-hidden">
                <div
                  className="h-full bg-background"
                  style={{ width: `${100 - analysis.energy * 100}%`, marginLeft: 'auto' }}
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Danceability</span>
                <span className="font-medium">{Math.round(analysis.danceability * 100)}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full"
                  style={{ width: `${analysis.danceability * 100}%` }}
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Loudness</span>
              <span className="font-mono font-medium">{analysis.loudness.toFixed(1)} dB</span>
            </div>

            {analysis.vocalIntensity && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Vocals</span>
                <span className="font-medium capitalize">{analysis.vocalIntensity.toLowerCase()}</span>
              </div>
            )}
          </div>

          {/* Warnings */}
          {analysis.mixabilityWarnings && analysis.mixabilityWarnings.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Warnings</p>
              {analysis.mixabilityWarnings.map((warning, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs text-destructive/80 bg-destructive/10 rounded-lg p-2"
                >
                  <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Analyzing track...</span>
        </div>
      )}

      {/* Delete Button with Confirmation */}
      <div className="pt-2 border-t border-border">
        {showDeleteConfirm ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground text-center">Delete this track?</p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="flex-1"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Delete'}
              </Button>
            </div>
          </div>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 className="w-4 h-4" />
                Delete Track
              </Button>
            </TooltipTrigger>
            <TooltipContent>Remove this track from the project</TooltipContent>
          </Tooltip>
        )}
      </div>
    </div>
    </TooltipProvider>
  );
}

function TransitionInspector({ transition, projectId }: { transition: Transition; projectId: string }) {
  const { fetchProject } = useProjectStore();
  const { currentProject } = useProjectStore();
  const [isRegenerating, setIsRegenerating] = useState(false);

  const fromTrack = currentProject?.tracks.find((t) => t.id === transition.fromTrackId);
  const toTrack = currentProject?.tracks.find((t) => t.id === transition.toTrackId);

  const fromName = fromTrack?.metadata?.title || fromTrack?.originalName.replace(/\.[^/.]+$/, '') || 'Track A';
  const toName = toTrack?.metadata?.title || toTrack?.originalName.replace(/\.[^/.]+$/, '') || 'Track B';

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await projectsService.generateTransitions(projectId);
      toast.success('Regenerating transitions...');
      fetchProject(projectId);
    } catch {
      toast.error('Failed to regenerate');
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex-1 min-w-0 text-center">
                <p className="text-xs text-muted-foreground truncate">{fromName}</p>
              </div>
            </TooltipTrigger>
            <TooltipContent>{fromName}</TooltipContent>
          </Tooltip>
          <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex-1 min-w-0 text-center">
                <p className="text-xs text-muted-foreground truncate">{toName}</p>
              </div>
            </TooltipTrigger>
            <TooltipContent>{toName}</TooltipContent>
          </Tooltip>
        </div>

        {/* Overall Score */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="studio-panel rounded-lg p-4 text-center cursor-help">
              <p className="text-xs text-muted-foreground mb-2">Compatibility Score</p>
              <p className={cn('text-4xl font-bold', getScoreColor(transition.score))}>
                {Math.round(transition.score)}
              </p>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            Combined score based on harmonic, BPM, and energy compatibility
          </TooltipContent>
        </Tooltip>

        {/* Individual Scores */}
        <div className="space-y-3">
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <ScoreBar label="Harmonic" score={transition.harmonicScore} />
              </div>
            </TooltipTrigger>
            <TooltipContent>Key compatibility using Camelot wheel</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <ScoreBar label="BPM Match" score={transition.bpmScore} />
              </div>
            </TooltipTrigger>
            <TooltipContent>Tempo similarity between tracks</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <ScoreBar label="Energy Flow" score={transition.energyScore} />
              </div>
            </TooltipTrigger>
            <TooltipContent>Energy level transition smoothness</TooltipContent>
          </Tooltip>
        </div>

        {/* BPM Difference */}
        {transition.bpmDifference > 3 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 text-xs text-warning bg-warning/10 rounded-lg p-2 cursor-help">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>BPM difference: {transition.bpmDifference.toFixed(1)}%</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>Large BPM differences may require tempo adjustment</TooltipContent>
          </Tooltip>
        )}

        {/* Transition Duration */}
        {transition.audioDurationMs && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Duration</span>
            <span className="font-mono">{formatDuration(transition.audioDurationMs / 1000)}</span>
          </div>
        )}

        {/* Audio Status */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Audio Status</span>
          <div className="flex items-center gap-2">
            {transition.audioStatus === 'COMPLETED' ? (
              <>
                <Check className="w-4 h-4 text-success" />
                <span className="text-success">Ready</span>
              </>
            ) : transition.audioStatus === 'PROCESSING' ? (
              <>
                <Loader2 className="w-4 h-4 text-accent animate-spin" />
                <span className="text-accent">Processing</span>
              </>
            ) : transition.audioStatus === 'ERROR' ? (
              <>
                <X className="w-4 h-4 text-destructive" />
                <span className="text-destructive">Error</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 rounded-full bg-muted-foreground" />
                <span className="text-muted-foreground">Pending</span>
              </>
            )}
          </div>
        </div>

        {/* Generate/Regenerate Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2"
              onClick={handleRegenerate}
              disabled={transition.audioStatus === 'PROCESSING' || isRegenerating}
            >
              {isRegenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {transition.audioStatus === 'PENDING' ? 'Generate Transition' : 'Regenerate Transition'}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {transition.audioStatus === 'PENDING'
              ? 'Create the transition audio between these tracks'
              : 'Recreate the transition with fresh processing'}
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}

/**
 * Inspector panel showing details of selected track or transition
 */
export function Inspector({ projectId }: InspectorProps) {
  const { selection, isInspectorOpen, setIsInspectorOpen } = useStudioStore();

  if (!isInspectorOpen) {
    return null;
  }

  return (
    <aside className="w-64 h-full border-l border-border bg-card/30 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-sm font-medium">Inspector</span>
        <button
          onClick={() => setIsInspectorOpen(false)}
          className="p-1 hover:bg-muted rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 scrollbar-studio">
        {selection.type === 'track' && selection.data ? (
          <TrackInspector track={selection.data as Track} projectId={projectId} />
        ) : selection.type === 'transition' && selection.data ? (
          <TransitionInspector
            transition={selection.data as Transition}
            projectId={projectId}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="rounded-full bg-muted/50 p-3 mb-3">
              <Music className="w-6 h-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              Select a track or transition to view details
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
