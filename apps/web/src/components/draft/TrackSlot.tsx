import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, Music2, X, Disc3, CheckCircle2, AlertTriangle, Mic2 } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, Button, cn, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@autodj/ui';
import type { Track } from '@/services/projects.service';

interface TrackSlotProps {
  slot: 'A' | 'B';
  track: Track | null;
  onUpload: (file: File) => void;
  onRemove: () => void;
  disabled?: boolean;
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
 * Track slot component for draft (A or B)
 */
export function TrackSlot({ slot, track, onUpload, onRemove, disabled }: TrackSlotProps) {
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      setIsUploading(true);
      try {
        await onUpload(acceptedFiles[0]!);
      } finally {
        setIsUploading(false);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    disabled: disabled || isUploading,
    maxSize: 100 * 1024 * 1024, // 100MB
    maxFiles: 1,
  });

  const isAnalyzing = track && !track.analysis;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
              slot === 'A' ? 'bg-blue-500/20 text-blue-500' : 'bg-purple-500/20 text-purple-500'
            )}>
              {slot}
            </div>
            Track {slot}
          </CardTitle>
          {track && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onRemove}
              disabled={disabled || isUploading}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {track ? (
          <div className="space-y-4">
            {/* Track Info */}
            <div className="flex items-start gap-3">
              <div className={cn(
                'w-12 h-12 rounded-lg flex items-center justify-center',
                slot === 'A' ? 'bg-blue-500/10' : 'bg-purple-500/10'
              )}>
                {isAnalyzing ? (
                  <Loader2 className={cn(
                    'h-6 w-6 animate-spin',
                    slot === 'A' ? 'text-blue-500' : 'text-purple-500'
                  )} />
                ) : (
                  <Disc3 className={cn(
                    'h-6 w-6',
                    slot === 'A' ? 'text-blue-500' : 'text-purple-500'
                  )} />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{track.originalName}</p>
                {isAnalyzing ? (
                  <p className="text-sm text-muted-foreground">Analyzing...</p>
                ) : track.analysis ? (
                  <p className="text-sm text-muted-foreground">
                    {track.analysis.bpm.toFixed(0)} BPM · {track.analysis.camelot} · Energy {Math.round(track.analysis.energy * 100)}%
                  </p>
                ) : null}
              </div>
            </div>

            {/* Analysis Details */}
            {track.analysis && (
              <div className="space-y-3">
                {/* Core metrics */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="bg-muted/50 rounded-lg p-2">
                    <p className="text-muted-foreground text-xs">BPM</p>
                    <p className="font-semibold">{track.analysis.bpm.toFixed(1)}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-2">
                    <p className="text-muted-foreground text-xs">Key</p>
                    <p className="font-semibold">{track.analysis.camelot}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-2">
                    <p className="text-muted-foreground text-xs">Energy</p>
                    <p className="font-semibold">{Math.round(track.analysis.energy * 100)}%</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-2">
                    <p className="text-muted-foreground text-xs">Duration</p>
                    <p className="font-semibold">{formatDuration(track.duration || 0)}</p>
                  </div>
                </div>

                {/* Mixability section */}
                {track.analysis.mixFriendly !== undefined && track.analysis.mixFriendly !== null && (
                  <div className="space-y-2">
                    {/* Mix-friendly badge and vocal info */}
                    <div className="flex items-center gap-2">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className={cn(
                              'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
                              track.analysis.mixFriendly
                                ? 'bg-green-500/10 text-green-500'
                                : 'bg-amber-500/10 text-amber-500'
                            )}>
                              {track.analysis.mixFriendly ? (
                                <CheckCircle2 className="h-3 w-3" />
                              ) : (
                                <AlertTriangle className="h-3 w-3" />
                              )}
                              {track.analysis.mixFriendly ? 'Mix Friendly' : 'Mix Difficult'}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{track.analysis.mixFriendly
                              ? 'Good intro/outro for mixing'
                              : 'May be harder to mix smoothly'}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      {track.analysis.vocalPercentage !== undefined && track.analysis.vocalPercentage !== null && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className={cn(
                                'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
                                track.analysis.vocalPercentage > 60
                                  ? 'bg-purple-500/10 text-purple-500'
                                  : track.analysis.vocalPercentage > 30
                                    ? 'bg-blue-500/10 text-blue-500'
                                    : 'bg-muted text-muted-foreground'
                              )}>
                                <Mic2 className="h-3 w-3" />
                                {Math.round(track.analysis.vocalPercentage)}% vocals
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Vocal intensity: {track.analysis.vocalIntensity || 'Unknown'}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>

                    {/* Mixability warnings */}
                    {track.analysis.mixabilityWarnings && track.analysis.mixabilityWarnings.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {track.analysis.mixabilityWarnings.map((warning, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          >
                            {warning}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
              isDragActive
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-primary/50',
              (disabled || isUploading) && 'pointer-events-none opacity-50'
            )}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center space-y-3">
              {isUploading ? (
                <>
                  <Loader2 className="h-10 w-10 text-primary animate-spin" />
                  <p className="text-muted-foreground">Uploading...</p>
                </>
              ) : (
                <>
                  <div className={cn(
                    'rounded-full p-3',
                    slot === 'A' ? 'bg-blue-500/10' : 'bg-purple-500/10'
                  )}>
                    {isDragActive ? (
                      <Music2 className={cn(
                        'h-6 w-6',
                        slot === 'A' ? 'text-blue-500' : 'text-purple-500'
                      )} />
                    ) : (
                      <Upload className={cn(
                        'h-6 w-6',
                        slot === 'A' ? 'text-blue-500' : 'text-purple-500'
                      )} />
                    )}
                  </div>
                  <div>
                    <p className="font-medium">
                      {isDragActive ? 'Drop track here' : 'Drop track or click to browse'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      MP3, WAV, M4A, FLAC (max 100MB)
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
