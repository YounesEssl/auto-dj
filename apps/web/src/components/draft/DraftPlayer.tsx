import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, SkipBack, SkipForward, Loader2, Disc3 } from 'lucide-react';

import { Button, Slider, Card, CardHeader, CardTitle, CardContent, cn } from '@autodj/ui';
import { useAuthStore } from '@/stores/authStore';
import { draftsService } from '@/services/drafts.service';
import type { Track } from '@/services/projects.service';
import type { TransitionMode } from '@autodj/shared-types';

interface DraftPlayerProps {
  draftId: string;
  trackA: Track;
  trackB: Track;
  transitionDurationMs: number;
  trackAOutroMs: number;
  trackBIntroMs: number;
  transitionMode?: TransitionMode | null;
}

type SegmentType = 'trackA' | 'transition' | 'trackB';

interface SegmentInfo {
  type: SegmentType;
  label: string;
  url: string;
  startTime: number;
  endTime: number;
  globalStart: number;
  globalEnd: number;
  buffer?: AudioBuffer;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * DraftPlayer - Gapless player using Web Audio API
 * Uses AudioBufferSourceNode for precise, gapless segment transitions
 */
export function DraftPlayer({
  draftId,
  trackA,
  trackB,
  transitionDurationMs,
  trackAOutroMs,
  trackBIntroMs,
  transitionMode,
}: DraftPlayerProps) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const startTimeRef = useRef<number>(0);
  const pausedAtRef = useRef<number>(0);
  const accessToken = useAuthStore((state) => state.accessToken);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [buffers, setBuffers] = useState<(AudioBuffer | null)[]>([null, null, null]);
  const [allLoaded, setAllLoaded] = useState(false);

  const trackBDurationMs = (trackB.duration || 0) * 1000;

  const segments: SegmentInfo[] = accessToken ? [
    {
      type: 'trackA',
      label: trackA.originalName,
      url: draftsService.getTrackAudioUrl(draftId, 'A', accessToken),
      startTime: 0,
      endTime: trackAOutroMs / 1000,
      globalStart: 0,
      globalEnd: trackAOutroMs,
    },
    {
      type: 'transition',
      label: 'Transition',
      url: draftsService.getTransitionAudioUrl(draftId, accessToken, transitionDurationMs),
      startTime: 0,
      endTime: transitionDurationMs / 1000,
      globalStart: trackAOutroMs,
      globalEnd: trackAOutroMs + transitionDurationMs,
    },
    {
      type: 'trackB',
      label: trackB.originalName,
      url: draftsService.getTrackAudioUrl(draftId, 'B', accessToken),
      startTime: trackBIntroMs / 1000,
      endTime: trackBDurationMs / 1000,
      globalStart: trackAOutroMs + transitionDurationMs,
      globalEnd: trackAOutroMs + transitionDurationMs + (trackBDurationMs - trackBIntroMs),
    },
  ] : [];

  const lastSegment = segments[segments.length - 1];
  const totalDurationMs = lastSegment ? lastSegment.globalEnd : 0;
  const currentSegment = segments[currentSegmentIndex] as SegmentInfo | undefined;

  // Initialize AudioContext and load all buffers
  useEffect(() => {
    if (!accessToken || segments.length === 0) return;

    const loadAudio = async () => {
      setIsLoading(true);

      // Create AudioContext
      const ctx = new AudioContext();
      audioContextRef.current = ctx;

      // Create gain node for volume control
      const gainNode = ctx.createGain();
      gainNode.connect(ctx.destination);
      gainNodeRef.current = gainNode;

      // Load all audio buffers in parallel
      const loadedBuffers = await Promise.all(
        segments.map(async (seg) => {
          try {
            const response = await fetch(seg.url);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
            return audioBuffer;
          } catch (e) {
            console.error(`Failed to load ${seg.type}:`, e);
            return null;
          }
        })
      );

      setBuffers(loadedBuffers);
      setAllLoaded(loadedBuffers.every(b => b !== null));
      setIsLoading(false);
    };

    loadAudio();

    return () => {
      if (sourceNodeRef.current) {
        try { sourceNodeRef.current.stop(); } catch {}
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [accessToken, draftId]);

  // Update volume
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Time update interval
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const ctx = audioContextRef.current;
      if (!ctx) return;

      const elapsed = ctx.currentTime - startTimeRef.current;
      const segment = segments[currentSegmentIndex];
      if (!segment) return;

      const segmentElapsed = pausedAtRef.current + elapsed;
      const globalTime = segment.globalStart + (segmentElapsed * 1000);

      // Check if we need to move to next segment
      if (segmentElapsed >= (segment.endTime - segment.startTime)) {
        if (currentSegmentIndex < segments.length - 1) {
          // Auto-advance to next segment (gapless)
          playSegment(currentSegmentIndex + 1, 0);
        } else {
          // End of playback
          stopPlayback();
          setCurrentTimeMs(0);
          setCurrentSegmentIndex(0);
          pausedAtRef.current = 0;
        }
      } else {
        setCurrentTimeMs(Math.min(globalTime, totalDurationMs));
      }
    }, 50);

    return () => clearInterval(interval);
  }, [isPlaying, currentSegmentIndex, segments, totalDurationMs]);

  const playSegment = useCallback((segmentIndex: number, offsetInSegment: number) => {
    const ctx = audioContextRef.current;
    const gainNode = gainNodeRef.current;
    const buffer = buffers[segmentIndex];
    const segment = segments[segmentIndex];

    if (!ctx || !gainNode || !buffer || !segment) return;

    // Stop current source if any
    if (sourceNodeRef.current) {
      try { sourceNodeRef.current.stop(); } catch {}
    }

    // Create new source
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(gainNode);

    // Calculate where to start in the buffer
    const bufferOffset = segment.startTime + offsetInSegment;

    // Start playback
    source.start(0, bufferOffset);
    sourceNodeRef.current = source;
    startTimeRef.current = ctx.currentTime;
    pausedAtRef.current = offsetInSegment;
    setCurrentSegmentIndex(segmentIndex);
    setIsPlaying(true);

    // Handle natural end of buffer
    source.onended = () => {
      if (sourceNodeRef.current === source) {
        // Only handle if this is still the active source
        // The time update interval will handle segment transitions
      }
    };
  }, [buffers, segments]);

  const stopPlayback = useCallback(() => {
    const ctx = audioContextRef.current;
    if (!ctx) return;

    if (sourceNodeRef.current) {
      try { sourceNodeRef.current.stop(); } catch {}
      sourceNodeRef.current = null;
    }

    // Save current position within segment
    const elapsed = ctx.currentTime - startTimeRef.current;
    pausedAtRef.current = pausedAtRef.current + elapsed;
    setIsPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (!allLoaded) return;

    if (isPlaying) {
      stopPlayback();
    } else {
      playSegment(currentSegmentIndex, pausedAtRef.current);
    }
  }, [isPlaying, allLoaded, currentSegmentIndex, playSegment, stopPlayback]);

  const handleSeek = useCallback((value: number[]) => {
    if (!allLoaded || segments.length === 0) return;

    const seekMs = value[0] ?? 0;

    // Find target segment
    let targetIndex = 0;
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      if (seg && seekMs >= seg.globalStart && seekMs < seg.globalEnd) {
        targetIndex = i;
        break;
      }
      if (i === segments.length - 1) targetIndex = i;
    }

    const targetSeg = segments[targetIndex];
    if (!targetSeg) return;

    const offsetInSegment = (seekMs - targetSeg.globalStart) / 1000;
    setCurrentTimeMs(seekMs);

    if (isPlaying) {
      playSegment(targetIndex, offsetInSegment);
    } else {
      setCurrentSegmentIndex(targetIndex);
      pausedAtRef.current = offsetInSegment;
    }
  }, [segments, isPlaying, allLoaded, playSegment]);

  const skipToSegment = useCallback((index: number) => {
    if (!allLoaded || index < 0 || index >= segments.length) return;

    const seg = segments[index];
    if (!seg) return;

    setCurrentTimeMs(seg.globalStart);

    if (isPlaying) {
      playSegment(index, 0);
    } else {
      setCurrentSegmentIndex(index);
      pausedAtRef.current = 0;
    }
  }, [segments, isPlaying, allLoaded, playSegment]);

  if (!accessToken) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2 py-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Authenticating...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Disc3 className="h-5 w-5" />
          Draft Player
          {transitionMode === 'CROSSFADE' && (
            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded">
              Crossfade Mode
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-4 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Loading audio buffers...</span>
          </div>
        )}

        {currentSegment && (
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-12 h-12 rounded-lg flex items-center justify-center',
                currentSegment.type === 'trackA' && 'bg-blue-500/20 text-blue-500',
                currentSegment.type === 'transition' && 'bg-purple-500/20 text-purple-500',
                currentSegment.type === 'trackB' && 'bg-green-500/20 text-green-500'
              )}
            >
              <Disc3 className={cn('h-6 w-6', isPlaying && 'animate-spin')} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{currentSegment.label}</p>
              <p className="text-sm text-muted-foreground">
                {currentSegment.type === 'trackA' && 'Playing until transition point'}
                {currentSegment.type === 'transition' && 'Transition mix'}
                {currentSegment.type === 'trackB' && 'Playing from transition point'}
              </p>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Slider
            value={[currentTimeMs]}
            max={totalDurationMs}
            step={100}
            onValueChange={handleSeek}
            disabled={isLoading || !allLoaded}
            className="cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(currentTimeMs)}</span>
            <span>{formatTime(totalDurationMs)}</span>
          </div>
        </div>

        <div className="flex gap-1 h-2 rounded-full overflow-hidden">
          {segments.map((segment, index) => {
            const widthPercent = ((segment.globalEnd - segment.globalStart) / totalDurationMs) * 100;
            const isActive = index === currentSegmentIndex;

            return (
              <div
                key={segment.type}
                className={cn(
                  'transition-opacity cursor-pointer',
                  segment.type === 'trackA' && 'bg-blue-500',
                  segment.type === 'transition' && 'bg-purple-500',
                  segment.type === 'trackB' && 'bg-green-500',
                  !isActive && 'opacity-30 hover:opacity-50'
                )}
                style={{ width: `${widthPercent}%` }}
                onClick={() => skipToSegment(index)}
                title={`${segment.label} (${formatTime(segment.globalEnd - segment.globalStart)})`}
              />
            );
          })}
        </div>

        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipToSegment(Math.max(0, currentSegmentIndex - 1))}
            disabled={isLoading || !allLoaded || currentSegmentIndex === 0}
          >
            <SkipBack className="h-5 w-5" />
          </Button>

          <Button
            variant="default"
            size="lg"
            className="h-14 w-14 rounded-full"
            onClick={togglePlay}
            disabled={isLoading || !allLoaded}
          >
            {isPlaying ? (
              <Pause className="h-7 w-7" />
            ) : (
              <Play className="h-7 w-7 ml-1" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => skipToSegment(Math.min(segments.length - 1, currentSegmentIndex + 1))}
            disabled={isLoading || !allLoaded || currentSegmentIndex === segments.length - 1}
          >
            <SkipForward className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex items-center justify-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => setIsMuted(!isMuted)}>
            {isMuted || volume === 0 ? (
              <VolumeX className="h-4 w-4" />
            ) : (
              <Volume2 className="h-4 w-4" />
            )}
          </Button>
          <Slider
            value={[isMuted ? 0 : volume]}
            max={1}
            step={0.01}
            onValueChange={(v) => {
              setVolume(v[0] ?? 1);
              if ((v[0] ?? 0) > 0) setIsMuted(false);
            }}
            className="w-28"
          />
        </div>

        <div className="border-t pt-4 space-y-1">
          <p className="text-xs text-muted-foreground mb-2">Segments</p>
          {segments.map((segment, index) => (
            <button
              key={segment.type}
              onClick={() => skipToSegment(index)}
              className={cn(
                'w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-3 transition-colors',
                index === currentSegmentIndex
                  ? 'bg-primary/10 text-primary'
                  : 'hover:bg-muted'
              )}
            >
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold',
                  segment.type === 'trackA' && 'bg-blue-500/20 text-blue-500',
                  segment.type === 'transition' && 'bg-purple-500/20 text-purple-500',
                  segment.type === 'trackB' && 'bg-green-500/20 text-green-500'
                )}
              >
                {segment.type === 'trackA' ? 'A' : segment.type === 'transition' ? 'T' : 'B'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium">{segment.label}</p>
                <p className="text-xs text-muted-foreground">
                  {formatTime(segment.globalStart)} - {formatTime(segment.globalEnd)}
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {formatTime(segment.globalEnd - segment.globalStart)}
              </span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
