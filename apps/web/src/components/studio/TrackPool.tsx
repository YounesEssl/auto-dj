import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, Music, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

import { cn } from '@autodj/ui';
import { Button } from '@autodj/ui';
import { projectsService, type Track } from '@/services/projects.service';
import { useProjectStore } from '@/stores/projectStore';
import { useStudioStore } from '@/stores/studioStore';
import { TrackMiniCard } from './TrackMiniCard';

const handleDeleteTrack = async (
  projectId: string,
  trackId: string,
  fetchProject: (id: string) => Promise<void>,
  removeTrackFromTimeline: (id: string) => void
) => {
  if (!confirm('Are you sure you want to delete this track?')) return;

  try {
    await projectsService.deleteTrack(projectId, trackId);
    removeTrackFromTimeline(trackId);
    await fetchProject(projectId);
    toast.success('Track deleted');
  } catch {
    toast.error('Failed to delete track');
  }
};

const ACCEPTED_TYPES = {
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
  'audio/x-wav': ['.wav'],
  'audio/mp4': ['.m4a'],
  'audio/x-m4a': ['.m4a'],
  'audio/aac': ['.aac', '.m4a'],
  'audio/flac': ['.flac'],
  'audio/ogg': ['.ogg'],
};

interface TrackPoolProps {
  projectId: string;
  tracks: Track[];
}

/**
 * Track pool component with drag-drop upload zone and horizontal scrolling track list
 */
export function TrackPool({ projectId, tracks }: TrackPoolProps) {
  const [isUploading, setIsUploading] = useState(false);
  const { fetchProject } = useProjectStore();
  const { selection, setSelection, timelineTracks, removeTrackFromTimeline } = useStudioStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      setIsUploading(true);
      try {
        await projectsService.uploadTracks(projectId, acceptedFiles);
        toast.success(`${acceptedFiles.length} track(s) uploaded`);
        fetchProject(projectId);
      } catch {
        toast.error('Failed to upload tracks');
      } finally {
        setIsUploading(false);
      }
    },
    [projectId, fetchProject]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    disabled: isUploading,
    maxSize: 100 * 1024 * 1024,
    noClick: tracks.length > 0,
    noKeyboard: tracks.length > 0,
  });

  const handleTrackClick = (track: Track) => {
    if (selection.type === 'track' && selection.id === track.id) {
      setSelection(null, null, null);
    } else {
      setSelection('track', track.id, track);
    }
  };

  const scrollContainer = (direction: 'left' | 'right') => {
    const container = document.getElementById('track-pool-scroll');
    if (container) {
      const scrollAmount = 200;
      container.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  // Show upload zone if no tracks
  if (tracks.length === 0) {
    return (
      <div
        {...getRootProps()}
        className={cn(
          'h-full border-2 border-dashed rounded-lg flex items-center justify-center cursor-pointer transition-all',
          isDragActive
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-primary/50'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center space-y-3 p-6 text-center">
          {isUploading ? (
            <>
              <Loader2 className="h-10 w-10 text-primary animate-spin" />
              <p className="text-muted-foreground">Uploading tracks...</p>
            </>
          ) : (
            <>
              <div className="rounded-full bg-primary/10 p-4">
                {isDragActive ? (
                  <Music className="h-6 w-6 text-primary" />
                ) : (
                  <Upload className="h-6 w-6 text-primary" />
                )}
              </div>
              <div>
                <p className="font-semibold text-sm">
                  {isDragActive ? 'Drop your tracks here' : 'Drag & drop tracks to start'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  MP3, WAV, M4A, FLAC, OGG up to 100MB each
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div {...getRootProps()} className="h-full flex flex-col">
      <input {...getInputProps()} />

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Music className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">
            Track Pool ({tracks.length})
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={(e) => {
              e.stopPropagation();
              scrollContainer('left');
            }}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={(e) => {
              e.stopPropagation();
              scrollContainer('right');
            }}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 ml-2"
            onClick={(e) => {
              e.stopPropagation();
              open();
            }}
            disabled={isUploading}
          >
            {isUploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            <span className="ml-1.5">Add</span>
          </Button>
        </div>
      </div>

      {/* Drop overlay */}
      <AnimatePresence>
        {isDragActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-lg z-10 flex items-center justify-center"
          >
            <div className="text-center">
              <Music className="w-8 h-8 text-primary mx-auto mb-2" />
              <p className="text-sm font-medium text-primary">Drop to add tracks</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scrollable track list */}
      <div
        id="track-pool-scroll"
        className="flex-1 overflow-x-auto overflow-y-auto scrollbar-studio"
      >
        <div className="flex gap-3 p-3 items-start">
          <AnimatePresence mode="popLayout">
            {tracks.map((track) => (
              <motion.div
                key={track.id}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                <TrackMiniCard
                  track={track}
                  isSelected={selection.type === 'track' && selection.id === track.id}
                  isInTimeline={timelineTracks.includes(track.id)}
                  onClick={() => handleTrackClick(track)}
                  onDelete={() => handleDeleteTrack(projectId, track.id, fetchProject, removeTrackFromTimeline)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
