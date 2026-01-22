import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  RotateCcw,
  RotateCw,
  Music,
} from 'lucide-react';

import { cn } from '@autodj/ui';
import { Button } from '@autodj/ui';
import { Slider } from '@autodj/ui';
import type { Project, Track, Transition } from '@/services/projects.service';
import { useStudioStore } from '@/stores/studioStore';

interface PlayerBarProps {
  project: Project | null;
}

/**
 * A segment in the playback sequence
 */
interface PlaybackSegment {
  id: string;
  type: 'track' | 'transition';
  /** For track: the track object. For transition: the transition object */
  source: Track | Transition;
  /** Audio URL to play */
  audioUrl: string;
  /** Start time within the audio file (seconds) */
  startTime: number;
  /** End time within the audio file (seconds), null = play to end */
  endTime: number | null;
  /** Duration of this segment in seconds */
  duration: number;
  /** Display name */
  name: string;
}

/**
 * Build playback segments from ordered tracks and transitions
 */
function buildPlaybackSegments(project: Project): PlaybackSegment[] {
  const segments: PlaybackSegment[] = [];
  const trackMap = new Map(project.tracks.map(t => [t.id, t]));
  const transitionMap = new Map(project.transitions.map(t => [`${t.fromTrackId}-${t.toTrackId}`, t]));

  for (let i = 0; i < project.orderedTracks.length; i++) {
    const trackId = project.orderedTracks[i];
    if (!trackId) continue;
    const track = trackMap.get(trackId);
    if (!track) continue;

    const nextTrackId = project.orderedTracks[i + 1];
    const transition = nextTrackId ? transitionMap.get(`${trackId}-${nextTrackId}`) : null;

    // Determine track segment boundaries
    let trackStart = 0;
    
    // Check if there's a previous transition that defines a start time (Smart Start)
    if (i > 0) {
      const prevTrackId = project.orderedTracks[i - 1];
      const prevTransition = prevTrackId ? transitionMap.get(`${prevTrackId}-${trackId}`) : null;
      if (prevTransition?.audioStatus === 'COMPLETED' && prevTransition.trackBStartMs) {
        trackStart = prevTransition.trackBStartMs / 1000;
      }
    }

    let trackEnd: number | null = track.duration;

    // If there's a transition with audio, adjust the track end point
    if (transition?.audioStatus === 'COMPLETED' && transition.trackACutMs) {
      // Track ends where transition begins (trackACutMs is where track A gets cut)
      trackEnd = transition.trackACutMs / 1000;
    } else if (track.analysis?.outroStart && nextTrackId) {
      // No transition audio yet, but we have analysis - play until outro start
      trackEnd = track.analysis.outroStart;
    }

    // Add track segment
    const trackDuration = (trackEnd ?? track.duration ?? 0) - trackStart;
    if (trackDuration > 0) {
      segments.push({
        id: `track-${track.id}`,
        type: 'track',
        source: track,
        audioUrl: `/api/v1/projects/${project.id}/tracks/${track.id}/audio`,
        startTime: trackStart,
        endTime: trackEnd,
        duration: trackDuration,
        name: track.metadata?.title || track.originalName.replace(/\.[^/.]+$/, ''),
      });
    }

    // Add transition segment if audio is ready
    if (transition?.audioStatus === 'COMPLETED' && transition.audioDurationMs && nextTrackId) {
      const nextTrack = trackMap.get(nextTrackId);
      segments.push({
        id: `transition-${transition.id}`,
        type: 'transition',
        source: transition,
        audioUrl: `/api/v1/projects/${project.id}/transitions/${transition.id}/audio`,
        startTime: 0,
        endTime: null,
        duration: transition.audioDurationMs / 1000,
        name: `→ ${nextTrack?.metadata?.title || nextTrack?.originalName.replace(/\.[^/.]+$/, '') || 'Next'}`,
      });
    }
  }

  return segments;
}

/**
 * Fixed player bar at the bottom of the studio with segment-based playback
 */
export function PlayerBar({ project }: PlayerBarProps) {
  // Double-buffer audio elements for gapless playback
  const audioARef = useRef<HTMLAudioElement>(null);
  const audioBRef = useRef<HTMLAudioElement>(null);
  // Track which audio element is currently active (0 = A, 1 = B)
  const [activeBuffer, setActiveBuffer] = useState<0 | 1>(0);
  
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [segments, setSegments] = useState<PlaybackSegment[]>([]);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [segmentTime, setSegmentTime] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const { isPlaying, setIsPlaying, currentTime, setCurrentTime } = useStudioStore();

  // Get active and inactive audio refs
  const activeAudioRef = activeBuffer === 0 ? audioARef : audioBRef;
  const inactiveAudioRef = activeBuffer === 0 ? audioBRef : audioARef;

  // Build segments when project changes
  useEffect(() => {
    if (project && project.orderedTracks.length > 0) {
      const newSegments = buildPlaybackSegments(project);
      setSegments(newSegments);
      // Reset playback position
      setCurrentSegmentIndex(0);
      setSegmentTime(0);
      setCurrentTime(0);
      setActiveBuffer(0);
    } else {
      setSegments([]);
    }
  }, [project, project?.orderedTracks, project?.transitions, setCurrentTime]);

  const hasAudio = segments.length > 0;
  const currentSegment = segments[currentSegmentIndex];
  const nextSegment = segments[currentSegmentIndex + 1];
  const totalDuration = segments.reduce((acc, s) => acc + s.duration, 0);

  // Calculate cumulative time before current segment
  const timeBeforeCurrentSegment = segments
    .slice(0, currentSegmentIndex)
    .reduce((acc, s) => acc + s.duration, 0);

  // Update global current time
  useEffect(() => {
    setCurrentTime(timeBeforeCurrentSegment + segmentTime);
  }, [timeBeforeCurrentSegment, segmentTime, setCurrentTime]);

  // Load current segment into active audio element
  useEffect(() => {
    const audio = activeAudioRef.current;
    if (!audio || !currentSegment) return;

    const currentUrl = window.location.origin + currentSegment.audioUrl;
    if (audio.src !== currentUrl) {
      setIsLoading(true);
      audio.src = currentSegment.audioUrl;
      audio.load();
    }
  }, [currentSegment, activeBuffer]);

  // Preload next segment into inactive audio element
  useEffect(() => {
    const preloadAudio = inactiveAudioRef.current;
    if (!preloadAudio || !nextSegment) return;

    const nextUrl = window.location.origin + nextSegment.audioUrl;
    if (preloadAudio.src !== nextUrl) {
      preloadAudio.src = nextSegment.audioUrl;
      preloadAudio.load();
    }
  }, [nextSegment, activeBuffer]);

  // Handle loaded metadata for active audio - seek to start time
  const handleLoadedMetadataA = useCallback(() => {
    if (!audioARef.current || !currentSegment) return;
    if (activeBuffer !== 0) return; // Only handle if this is the active buffer
    setIsLoading(false);
    audioARef.current.currentTime = currentSegment.startTime;
    if (isPlaying) {
      audioARef.current.play().catch(() => setIsPlaying(false));
    }
  }, [currentSegment, isPlaying, setIsPlaying, activeBuffer]);

  const handleLoadedMetadataB = useCallback(() => {
    if (!audioBRef.current || !currentSegment) return;
    if (activeBuffer !== 1) return; // Only handle if this is the active buffer
    setIsLoading(false);
    audioBRef.current.currentTime = currentSegment.startTime;
    if (isPlaying) {
      audioBRef.current.play().catch(() => setIsPlaying(false));
    }
  }, [currentSegment, isPlaying, setIsPlaying, activeBuffer]);

  // Preload audio elements get their start time set when loading next segment
  // This is handled in the useEffect that loads the segment

  // Handle time update - check for segment end
  const handleTimeUpdate = useCallback(() => {
    const audio = activeAudioRef.current;
    if (!audio || !currentSegment) return;

    const relativeTime = audio.currentTime - currentSegment.startTime;
    setSegmentTime(Math.max(0, relativeTime));

    // Check if we've reached the end of this segment
    if (currentSegment.endTime !== null && audio.currentTime >= currentSegment.endTime) {
      // Move to next segment
      if (currentSegmentIndex < segments.length - 1) {
        // GAPLESS: Switch to the preloaded buffer immediately
        const preloadAudio = inactiveAudioRef.current;
        if (preloadAudio && preloadAudio.readyState >= 3) { // HAVE_FUTURE_DATA
          audio.pause();
          preloadAudio.play().catch(() => setIsPlaying(false));
          // Swap active buffer
          setActiveBuffer(prev => prev === 0 ? 1 : 0);
        }
        setCurrentSegmentIndex(currentSegmentIndex + 1);
        setSegmentTime(0);
      } else {
        // End of playlist
        setIsPlaying(false);
        audio.pause();
      }
    }
  }, [currentSegment, currentSegmentIndex, segments.length, setIsPlaying, activeBuffer]);

  // Handle natural end of audio
  const handleEnded = useCallback(() => {
    if (currentSegmentIndex < segments.length - 1) {
      // GAPLESS: Switch to the preloaded buffer
      const preloadAudio = inactiveAudioRef.current;
      if (preloadAudio && preloadAudio.readyState >= 3) {
        preloadAudio.play().catch(() => setIsPlaying(false));
        setActiveBuffer(prev => prev === 0 ? 1 : 0);
      }
      setCurrentSegmentIndex(currentSegmentIndex + 1);
      setSegmentTime(0);
    } else {
      setIsPlaying(false);
      setCurrentSegmentIndex(0);
      setSegmentTime(0);
    }
  }, [currentSegmentIndex, segments.length, setIsPlaying, activeBuffer]);

  // Play/pause control
  useEffect(() => {
    const audio = activeAudioRef.current;
    if (!audio || !hasAudio) return;

    if (isPlaying && !isLoading) {
      audio.play().catch(() => setIsPlaying(false));
    } else {
      audio.pause();
    }
  }, [isPlaying, hasAudio, isLoading, setIsPlaying, activeBuffer]);

  // Update volume on both audio elements
  useEffect(() => {
    const vol = isMuted ? 0 : volume;
    if (audioARef.current) audioARef.current.volume = vol;
    if (audioBRef.current) audioBRef.current.volume = vol;
  }, [volume, isMuted]);

  const handlePlayPause = () => {
    if (!hasAudio) return;
    setIsPlaying(!isPlaying);
  };

  const handlePrevSegment = () => {
    if (currentSegmentIndex > 0) {
      setCurrentSegmentIndex(currentSegmentIndex - 1);
      setSegmentTime(0);
    } else {
      const audio = activeAudioRef.current;
      if (audio) {
        audio.currentTime = currentSegment?.startTime ?? 0;
        setSegmentTime(0);
      }
    }
  };

  const handleNextSegment = () => {
    if (currentSegmentIndex < segments.length - 1) {
      setCurrentSegmentIndex(currentSegmentIndex + 1);
      setSegmentTime(0);
    }
  };

  const handleSkipBack = () => {
    const audio = activeAudioRef.current;
    if (audio && currentSegment) {
      const newTime = Math.max(currentSegment.startTime, audio.currentTime - 10);
      audio.currentTime = newTime;
    }
  };

  const handleSkipForward = () => {
    const audio = activeAudioRef.current;
    if (audio && currentSegment) {
      const maxTime = currentSegment.endTime ?? audio.duration;
      const newTime = Math.min(maxTime, audio.currentTime + 10);
      audio.currentTime = newTime;
    }
  };

  // Seek within the global timeline
  const handleSeek = (value: number[]) => {
    const targetTime = value[0] ?? 0;

    // Find which segment this time falls into
    let accumulated = 0;
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      if (!segment) continue;
      if (targetTime < accumulated + segment.duration) {
        // This is the target segment
        const timeInSegment = targetTime - accumulated;
        setCurrentSegmentIndex(i);
        setSegmentTime(timeInSegment);

        const audio = activeAudioRef.current;
        if (audio && i === currentSegmentIndex) {
          audio.currentTime = segment.startTime + timeInSegment;
        }
        break;
      }
      accumulated += segment.duration;
    }
  };

  // Get BPM from current track if available
  const currentTrackBpm = currentSegment?.type === 'track'
    ? (currentSegment.source as Track).analysis?.bpm
    : null;

  return (
    <footer className="h-20 border-t border-border/50 bg-card/95 backdrop-blur-xl flex items-center">
      {/* Double-Buffer Audio Elements for Gapless Playback */}
      <audio
        ref={audioARef}
        onTimeUpdate={activeBuffer === 0 ? handleTimeUpdate : undefined}
        onLoadedMetadata={handleLoadedMetadataA}
        onEnded={activeBuffer === 0 ? handleEnded : undefined}
        preload="auto"
      />
      <audio
        ref={audioBRef}
        onTimeUpdate={activeBuffer === 1 ? handleTimeUpdate : undefined}
        onLoadedMetadata={handleLoadedMetadataB}
        onEnded={activeBuffer === 1 ? handleEnded : undefined}
        preload="auto"
      />

      {/* Left: Track Info */}
      <div className="flex items-center gap-3 px-4 w-64 flex-shrink-0">
        {/* Cover Art */}
        <div className="w-12 h-12 rounded bg-black/30 border border-border/30 flex-shrink-0 overflow-hidden">
          {currentSegment?.type === 'track' && (currentSegment.source as Track).metadata?.coverUrl ? (
            <img
              src={(currentSegment.source as Track).metadata?.coverUrl}
              alt=""
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-primary/10 to-accent/5 flex items-center justify-center">
              <Music className="w-5 h-5 text-muted-foreground/30" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">
            {currentSegment ? currentSegment.name : project?.name || 'No Track'}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {currentSegment && (
              <span className={cn(
                'text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase',
                currentSegment.type === 'transition'
                  ? 'bg-accent/20 text-accent'
                  : 'bg-primary/15 text-primary/80'
              )}>
                {currentSegment.type === 'transition' ? 'Transition' : 'Track'}
              </span>
            )}
            {segments.length > 0 && (
              <span className="text-[10px] text-muted-foreground">
                {currentSegmentIndex + 1} / {segments.length}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Center: Timeline & Controls */}
      <div className="flex-1 flex flex-col justify-center px-4 gap-1.5">
        {/* Progress Timeline */}
        <div
          className="h-8 w-full relative rounded bg-black/40 border border-border/20 overflow-hidden cursor-pointer"
          onClick={(e) => {
            if (!hasAudio) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const percent = x / rect.width;
            handleSeek([percent * totalDuration]);
          }}
        >
          {/* Segment Blocks */}
          {segments.map((segment, i) => {
            const segmentStart = segments.slice(0, i).reduce((a, s) => a + s.duration, 0);
            const widthPercent = (segment.duration / totalDuration) * 100;
            const leftPercent = (segmentStart / totalDuration) * 100;
            const isActive = i === currentSegmentIndex;

            return (
              <div
                key={segment.id}
                className={cn(
                  'absolute top-0 bottom-0 transition-opacity',
                  segment.type === 'transition'
                    ? 'bg-gradient-to-t from-accent/40 to-accent/10'
                    : 'bg-gradient-to-t from-primary/30 to-primary/5',
                  isActive ? 'opacity-100' : 'opacity-70',
                  i > 0 && 'border-l border-border/30'
                )}
                style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
              />
            );
          })}

          {/* Played overlay */}
          <div
            className="absolute top-0 bottom-0 left-0 bg-white/5 pointer-events-none"
            style={{ width: `${(currentTime / (totalDuration || 1)) * 100}%` }}
          />

          {/* Playhead */}
          {hasAudio && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_rgba(255,255,255,0.8)] pointer-events-none"
              style={{ left: `${(currentTime / (totalDuration || 1)) * 100}%` }}
            />
          )}
        </div>

        {/* Transport */}
        <div className="flex items-center justify-center gap-1">
          <span className="text-[10px] text-muted-foreground font-mono w-10 text-right tabular-nums">
            {formatTime(currentTime)}
          </span>

          <div className="flex items-center gap-0.5 mx-2">
            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={handlePrevSegment} disabled={!hasAudio}>
              <SkipBack className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={handleSkipBack} disabled={!hasAudio}>
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="default"
              size="icon"
              className={cn('w-9 h-9 rounded-full mx-1', hasAudio && 'btn-glow', isLoading && 'opacity-50')}
              onClick={handlePlayPause}
              disabled={!hasAudio || isLoading}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </Button>
            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={handleSkipForward} disabled={!hasAudio}>
              <RotateCw className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={handleNextSegment} disabled={!hasAudio || currentSegmentIndex >= segments.length - 1}>
              <SkipForward className="w-3.5 h-3.5" />
            </Button>
          </div>

          <span className="text-[10px] text-muted-foreground font-mono w-10 tabular-nums">
            {formatTime(totalDuration)}
          </span>
        </div>
      </div>

      {/* Right: BPM & Volume */}
      <div className="flex items-center gap-4 px-4 flex-shrink-0">
        {/* BPM */}
        {currentTrackBpm && (
          <div className="text-center">
            <div className="flex items-center gap-1">
              <div className={cn('w-1.5 h-1.5 rounded-full', isPlaying ? 'led-on' : 'led-off')} />
              <span className="text-sm font-mono font-bold text-primary tabular-nums">{currentTrackBpm.toFixed(0)}</span>
            </div>
            <span className="text-[8px] text-muted-foreground uppercase tracking-wider">BPM</span>
          </div>
        )}

        {/* Volume */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => setIsMuted(!isMuted)}>
            {isMuted || volume === 0 ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </Button>
          <Slider
            value={[isMuted ? 0 : volume]}
            max={1}
            step={0.01}
            onValueChange={(v) => {
              const newVolume = v[0] ?? 0;
              setVolume(newVolume);
              if (newVolume > 0) setIsMuted(false);
            }}
            className="w-20"
          />
        </div>
      </div>
    </footer>
  );
}

function formatTime(seconds: number): string {
  if (!seconds || !isFinite(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
