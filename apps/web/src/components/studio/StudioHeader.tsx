import { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Download,
  Loader2,
  Check,
  Pencil,
  Music2,
  Keyboard
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@autodj/ui';
import { cn } from '@autodj/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@autodj/ui';
import { projectsService, type Project } from '@/services/projects.service';
import { useProjectStore } from '@/stores/projectStore';

interface StudioHeaderProps {
  project: Project | null;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; pulse?: boolean }> = {
  CREATED: { label: 'New', color: 'bg-muted-foreground' },
  UPLOADING: { label: 'Uploading', color: 'bg-primary', pulse: true },
  ANALYZING: { label: 'Analyzing', color: 'bg-accent', pulse: true },
  READY: { label: 'Ready', color: 'bg-success' },
  ORDERING: { label: 'Ordering', color: 'bg-accent', pulse: true },
  MIXING: { label: 'Mixing', color: 'bg-primary', pulse: true },
  COMPLETED: { label: 'Completed', color: 'bg-success' },
  FAILED: { label: 'Failed', color: 'bg-destructive' },
};

/**
 * Studio header with mix name, status, and action buttons
 */
export function StudioHeader({ project }: StudioHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [isOrdering, setIsOrdering] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { fetchProject } = useProjectStore();

  useEffect(() => {
    if (project) {
      setEditName(project.name);
    }
  }, [project?.name]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSaveName = async () => {
    if (!project || editName.trim() === project.name) {
      setIsEditing(false);
      return;
    }

    try {
      await projectsService.update(project.id, { name: editName.trim() });
      await fetchProject(project.id);
      setIsEditing(false);
      toast.success('Mix name updated');
    } catch {
      toast.error('Failed to update name');
      setEditName(project.name);
    }
  };

  const handleAutoArrange = async () => {
    if (!project) return;

    setIsOrdering(true);
    try {
      await projectsService.calculateOrder(project.id);
      await fetchProject(project.id);
      toast.success('Tracks arranged optimally');
    } catch {
      toast.error('Failed to arrange tracks');
    } finally {
      setIsOrdering(false);
    }
  };

  const handleGenerateMix = async () => {
    if (!project) return;

    setIsGenerating(true);
    try {
      await projectsService.generateMix(project.id);
      toast.success('Mix generation started');
      // Note: isGenerating will be reset when project status changes via WebSocket
      // or when component re-renders with updated project
    } catch {
      toast.error('Failed to start mix generation');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!project?.outputFile) return;
    window.open(`/api/v1/projects/${project.id}/download`, '_blank');
  };

  const statusConfig = project ? STATUS_CONFIG[project.status] : null;

  const canArrange = Boolean(project && project.tracks.length >= 2 &&
    ['READY', 'CREATED'].includes(project.status) &&
    project.tracks.every(t => t.analysis));

  const canGenerate = Boolean(project && project.orderedTracks.length >= 2 &&
    project.status === 'READY');

  const canDownload = Boolean(project?.status === 'COMPLETED' && project.outputFile);

  const isProcessing = Boolean(project && ['UPLOADING', 'ANALYZING', 'ORDERING', 'MIXING'].includes(project.status));

  const [showShortcuts, setShowShortcuts] = useState(false);

  return (
    <TooltipProvider>
      <header className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center px-4 gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2 text-primary">
          <Music2 className="w-5 h-5" />
          <span className="font-semibold text-sm hidden sm:inline">Mix Studio</span>
        </div>

        <div className="w-px h-6 bg-border" />

        {/* Mix Name */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {project ? (
            isEditing ? (
              <input
                ref={inputRef}
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={handleSaveName}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveName();
                  if (e.key === 'Escape') {
                    setEditName(project.name);
                    setIsEditing(false);
                  }
                }}
                className="bg-transparent border-b border-primary text-foreground font-medium px-1 py-0.5 outline-none min-w-0 w-48"
              />
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-2 hover:text-primary transition-colors group truncate"
                  >
                    <span className="font-medium truncate">{project.name}</span>
                    <Pencil className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Click to edit mix name</TooltipContent>
              </Tooltip>
            )
          ) : (
            <span className="text-muted-foreground">No mix selected</span>
          )}
        </div>

        {/* Status Badge */}
        {statusConfig && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 cursor-help">
                <div
                  className={cn(
                    'w-2 h-2 rounded-full',
                    statusConfig.color,
                    statusConfig.pulse && 'animate-pulse'
                  )}
                />
                <span className="text-sm text-muted-foreground">{statusConfig.label}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>Current mix status</TooltipContent>
          </Tooltip>
        )}

        <div className="w-px h-6 bg-border" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAutoArrange}
                disabled={!canArrange || isOrdering || isProcessing}
                className="gap-2"
              >
                {isOrdering ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span className="hidden md:inline">Auto-arrange</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              Automatically arrange tracks for optimal transitions
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                onClick={handleGenerateMix}
                disabled={!canGenerate || isGenerating || isProcessing}
                className="gap-2 btn-glow"
              >
                {isGenerating || project?.status === 'MIXING' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : project?.status === 'COMPLETED' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Music2 className="w-4 h-4" />
                )}
                <span className="hidden md:inline">
                  {project?.status === 'COMPLETED' ? 'Regenerate' : 'Generate Mix'}
                </span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              Generate seamless transitions between tracks
            </TooltipContent>
          </Tooltip>

          {canDownload && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="gap-2"
                >
                  <Download className="w-4 h-4" />
                  <span className="hidden md:inline">Export</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download the final mix</TooltipContent>
            </Tooltip>
          )}

          <div className="w-px h-6 bg-border" />

          {/* Keyboard Shortcuts */}
          <Tooltip open={showShortcuts} onOpenChange={setShowShortcuts}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="w-8 h-8"
                onClick={() => setShowShortcuts(!showShortcuts)}
              >
                <Keyboard className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="w-64">
              <div className="text-xs space-y-2">
                <p className="font-medium mb-2">Keyboard Shortcuts</p>
                <div className="grid grid-cols-2 gap-1">
                  <span className="text-muted-foreground">Play/Pause</span>
                  <kbd className="bg-muted px-1 rounded text-right">Space</kbd>
                  <span className="text-muted-foreground">Skip back</span>
                  <kbd className="bg-muted px-1 rounded text-right">←</kbd>
                  <span className="text-muted-foreground">Skip forward</span>
                  <kbd className="bg-muted px-1 rounded text-right">→</kbd>
                  <span className="text-muted-foreground">Toggle sidebar</span>
                  <kbd className="bg-muted px-1 rounded text-right">B</kbd>
                  <span className="text-muted-foreground">Toggle inspector</span>
                  <kbd className="bg-muted px-1 rounded text-right">I</kbd>
                  <span className="text-muted-foreground">Clear selection</span>
                  <kbd className="bg-muted px-1 rounded text-right">Esc</kbd>
                </div>
              </div>
            </TooltipContent>
          </Tooltip>
        </div>
      </header>
    </TooltipProvider>
  );
}
