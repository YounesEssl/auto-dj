import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Loader2, RefreshCw } from 'lucide-react';
import { Button, Slider, cn } from '@autodj/ui';
import { useAuthStore } from '@/stores/authStore';

interface MixSegment {
  id: string;
  position: number;
  type: 'SOLO' | 'TRANSITION';
  trackId: string | null;
  transitionId: string | null;
  startMs: number;
  endMs: number;
  durationMs: number;
  audioFilePath: string | null;
  audioStatus: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'ERROR';
  audioError: string | null;
  track?: {
    id: string;
    originalName: string;
    filePath: string;
    mimeType: string;
  } | null;
}

interface MixSegmentsResponse {
  projectId: string;
  status: string;
  segments: MixSegment[];
  totalDurationMs: number;
}

interface MixPlayerProps {
  projectId: string;
  onRefresh?: () => void;
}

/**
 * Format milliseconds to mm:ss
 */
function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get segment label for display
 */
function getSegmentLabel(segment: MixSegment): string {
  if (segment.type === 'SOLO' && segment.track) {
    return segment.track.originalName;
  }
  if (segment.type === 'TRANSITION') {
    return `Transition ${segment.position}`;
  }
  return `Segment ${segment.position + 1}`;
}

/**
 * MixPlayer component for segment-based playback
 *
 * Plays segments in order:
 * - SOLO segments: Original track audio from startMs to endMs
 * - TRANSITION segments: Generated transition audio file
 */
export function MixPlayer({ projectId, onRefresh }: MixPlayerProps) {
  console.log('[MixPlayer] Rendering, projectId:', projectId);

  const audioRef = useRef<HTMLAudioElement>(null);
  const nextAudioRef = useRef<HTMLAudioElement>(null); // For preloading
  const accessToken = useAuthStore((state) => state.accessToken);

  const [segments, setSegments] = useState<MixSegment[]>([]);
  const [totalDurationMs, setTotalDurationMs] = useState(0);
  const [isLoadingSegments, setIsLoadingSegments] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0); // Current time within segment (ms)
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  console.log('[MixPlayer] State:', { segments, segmentsType: typeof segments, segmentsLength: segments?.length, currentIndex, isLoadingSegments });

  const currentSegment = segments?.[currentIndex];
  const tokenParam = accessToken ? `?token=${encodeURIComponent(accessToken)}` : '';

  // Fetch mix segments from API
  const fetchSegments = useCallback(async () => {
    try {
      setIsLoadingSegments(true);
      setLoadError(null);

      const response = await fetch(`/api/v1/projects/${projectId}/mix/segments`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch mix segments');
      }

      const response_data = await response.json();
      // API returns { success, data: { segments, totalDurationMs, ... } }
      const data: MixSegmentsResponse = response_data.data;
      setSegments(data.segments || []);
      setTotalDurationMs(data.totalDurationMs || 0);
    } catch (error) {
      console.error('Error fetching segments:', error);
      setLoadError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoadingSegments(false);
    }
  }, [projectId, accessToken]);

  // Load segments on mount
  useEffect(() => {
    fetchSegments();
  }, [fetchSegments]);

  // Get audio URL for a segment
  const getSegmentAudioUrl = useCallback((segment: MixSegment): string => {
    if (segment.type === 'SOLO' && segment.trackId) {
      return `/api/v1/projects/${projectId}/tracks/${segment.trackId}/audio${tokenParam}`;
    }
    if (segment.type === 'TRANSITION') {
      return `/api/v1/projects/${projectId}/mix/segments/${segment.id}/audio${tokenParam}`;
    }
    return '';
  }, [projectId, tokenParam]);

  // Load and prepare current segment
  const loadSegment = useCallback((segment: MixSegment, audio: HTMLAudioElement) => {
    const url = getSegmentAudioUrl(segment);
    if (!url) return;

    setIsLoading(true);
    audio.src = url;

    // For SOLO segments, set start time
    if (segment.type === 'SOLO') {
      audio.currentTime = segment.startMs / 1000;
    } else {
      audio.currentTime = 0;
    }

    audio.load();
  }, [getSegmentAudioUrl]);

  // Preload next segment
  const preloadNext = useCallback(() => {
    const nextIndex = currentIndex + 1;
    if (segments && nextIndex < segments.length && nextAudioRef.current) {
      const nextSegment = segments[nextIndex];
      if (nextSegment) {
        const url = getSegmentAudioUrl(nextSegment);
        nextAudioRef.current.src = url;
        nextAudioRef.current.load();
      }
    }
  }, [currentIndex, segments, getSegmentAudioUrl]);

  // Play next segment
  const playNext = useCallback(() => {
    console.log('[MixPlayer] playNext called, segments:', segments?.length, 'currentIndex:', currentIndex);
    if (!segments || segments.length === 0) return;
    if (currentIndex < segments.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setCurrentTime(0);
    } else {
      // End of mix
      setIsPlaying(false);
      setCurrentIndex(0);
      setCurrentTime(0);
    }
  }, [currentIndex, segments]);

  // Play previous segment
  const playPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      setCurrentTime(0);
    }
  }, [currentIndex]);

  // Handle audio events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleCanPlay = () => {
      setIsLoading(false);
      preloadNext();
      if (isPlaying) {
        audio.play().catch(console.error);
      }
    };

    const handleTimeUpdate = () => {
      if (!currentSegment) return;

      if (currentSegment.type === 'SOLO') {
        // Calculate time within the segment
        const absoluteTime = audio.currentTime * 1000;
        const segmentTime = absoluteTime - currentSegment.startMs;
        setCurrentTime(Math.max(0, Math.min(segmentTime, currentSegment.durationMs)));

        // Check if we've reached the end of this segment
        if (absoluteTime >= currentSegment.endMs) {
          playNext();
        }
      } else {
        // For transitions, time is from 0
        setCurrentTime(audio.currentTime * 1000);
      }
    };

    const handleEnded = () => {
      playNext();
    };

    const handleError = (e: Event) => {
      console.error('Audio playback error:', e);
      setIsLoading(false);
    };

    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [currentSegment, isPlaying, playNext, preloadNext]);

  // Load segment when index changes
  useEffect(() => {
    if (currentSegment && audioRef.current) {
      loadSegment(currentSegment, audioRef.current);
    }
  }, [currentSegment, loadSegment]);

  // Handle play/pause
  const togglePlay = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(console.error);
      setIsPlaying(true);
    }
  };

  // Handle volume change
  const handleVolumeChange = (value: number[]) => {
    console.log('[MixPlayer] handleVolumeChange called with:', value);
    const newVolume = value?.[0] ?? 1;
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
    if (newVolume > 0) {
      setIsMuted(false);
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  // Handle seek within segment
  const handleSeek = (value: number[]) => {
    console.log('[MixPlayer] handleSeek called with:', value);
    const seekTimeMs = value?.[0] ?? 0;
    if (!audioRef.current || !currentSegment) return;

    if (currentSegment.type === 'SOLO') {
      // Seek to absolute position in track
      audioRef.current.currentTime = (currentSegment.startMs + seekTimeMs) / 1000;
    } else {
      // Seek within transition
      audioRef.current.currentTime = seekTimeMs / 1000;
    }
    setCurrentTime(seekTimeMs);
  };

  // Loading state - must be BEFORE any segments access
  if (isLoadingSegments) {
    return (
      <div className="bg-card border rounded-lg p-4 flex items-center justify-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading mix...</span>
      </div>
    );
  }

  // Error state
  if (loadError) {
    return (
      <div className="bg-card border rounded-lg p-4 flex flex-col items-center gap-2">
        <p className="text-destructive text-sm">{loadError}</p>
        <Button variant="outline" size="sm" onClick={fetchSegments}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  // No segments
  if (!segments || segments.length === 0) {
    return (
      <div className="bg-card border rounded-lg p-4 text-center text-muted-foreground">
        <p>No mix segments available.</p>
        <p className="text-sm mt-1">Generate the mix to enable playback.</p>
      </div>
    );
  }

  // Calculate cumulative time before current segment (AFTER early returns)
  const cumulativeTime = segments.slice(0, currentIndex).reduce((sum, s) => sum + s.durationMs, 0);
  const globalCurrentTime = cumulativeTime + currentTime;

  // Count completed transition segments
  const transitionSegments = segments.filter(s => s.type === 'TRANSITION');
  const completedTransitions = transitionSegments.filter(s => s.audioStatus === 'COMPLETED').length;

  return (
    <div className="bg-card border rounded-lg p-4 space-y-4">
      {/* Hidden audio elements */}
      <audio ref={audioRef} preload="auto" />
      <audio ref={nextAudioRef} preload="auto" className="hidden" />

      {/* Now playing */}
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {currentSegment?.type === 'TRANSITION' && (
              <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                Transition
              </span>
            )}
            <span className="font-medium truncate">
              {currentSegment ? getSegmentLabel(currentSegment) : 'Ready to play'}
            </span>
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Segment {currentIndex + 1} / {segments.length}
            {transitionSegments.length > 0 && completedTransitions < transitionSegments.length && (
              <span className="text-yellow-500 ml-2">
                ({completedTransitions}/{transitionSegments.length} transitions ready)
              </span>
            )}
          </div>
        </div>
        {onRefresh && (
          <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Segment progress bar */}
      <div className="space-y-2">
        <Slider
          value={[currentTime]}
          max={currentSegment?.durationMs || 1000}
          step={100}
          onValueChange={handleSeek}
          className="cursor-pointer"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(currentSegment?.durationMs || 0)}</span>
        </div>
      </div>

      {/* Global progress (optional) */}
      <div className="text-xs text-center text-muted-foreground">
        Total: {formatTime(globalCurrentTime)} / {formatTime(totalDurationMs)}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={playPrevious}
          disabled={currentIndex === 0}
        >
          <SkipBack className="h-5 w-5" />
        </Button>

        <Button
          variant="default"
          size="icon"
          className="h-12 w-12"
          onClick={togglePlay}
          disabled={isLoading || !currentSegment}
        >
          {isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-6 w-6" />
          ) : (
            <Play className="h-6 w-6 ml-0.5" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={playNext}
          disabled={currentIndex >= segments.length - 1}
        >
          <SkipForward className="h-5 w-5" />
        </Button>
      </div>

      {/* Volume */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleMute}>
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
          onValueChange={handleVolumeChange}
          className="w-24"
        />
      </div>

      {/* Segment list */}
      <div className="border-t pt-4 mt-4">
        <div className="text-xs font-medium text-muted-foreground mb-2">Segments</div>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {segments.map((segment, idx) => (
            <button
              key={segment.id}
              onClick={() => {
                setCurrentIndex(idx);
                setCurrentTime(0);
              }}
              className={cn(
                'w-full text-left px-2 py-1 rounded text-sm truncate flex items-center gap-2',
                idx === currentIndex
                  ? 'bg-primary/20 text-primary'
                  : 'hover:bg-muted',
                segment.type === 'TRANSITION' && segment.audioStatus !== 'COMPLETED' && 'opacity-50'
              )}
              disabled={segment.type === 'TRANSITION' && segment.audioStatus !== 'COMPLETED'}
            >
              <span className="w-4 text-xs text-muted-foreground">{idx + 1}</span>
              <span className="flex-1 truncate">
                {segment.type === 'TRANSITION' ? '↔ ' : '♪ '}
                {getSegmentLabel(segment)}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatTime(segment.durationMs)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
