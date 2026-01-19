import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, Music } from 'lucide-react';
import { toast } from 'sonner';

import { cn } from '@autodj/ui';
import { projectsService } from '@/services/projects.service';
import { useProjectStore } from '@/stores/projectStore';

interface TrackUploaderProps {
  projectId: string;
}

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

/**
 * Drag and drop track uploader component
 */
export function TrackUploader({ projectId }: TrackUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const { fetchProject } = useProjectStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      setIsUploading(true);
      try {
        await projectsService.uploadTracks(projectId, acceptedFiles);
        toast.success(`${acceptedFiles.length} track(s) uploaded successfully`);
        fetchProject(projectId);
      } catch {
        toast.error('Failed to upload tracks');
      } finally {
        setIsUploading(false);
      }
    },
    [projectId, fetchProject]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    disabled: isUploading,
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragActive
          ? 'border-primary bg-primary/5'
          : 'border-muted-foreground/25 hover:border-primary/50',
        isUploading && 'pointer-events-none opacity-50'
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center space-y-4">
        {isUploading ? (
          <>
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
            <p className="text-muted-foreground">Uploading tracks...</p>
          </>
        ) : (
          <>
            <div className="rounded-full bg-primary/10 p-4">
              {isDragActive ? (
                <Music className="h-8 w-8 text-primary" />
              ) : (
                <Upload className="h-8 w-8 text-primary" />
              )}
            </div>
            <div>
              <p className="font-semibold">
                {isDragActive ? 'Drop your tracks here' : 'Drag & drop your tracks'}
              </p>
              <p className="text-sm text-muted-foreground">
                or click to browse (MP3, WAV, M4A, FLAC, OGG up to 100MB each)
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
