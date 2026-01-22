import type { MixStatus } from './project';

/**
 * Types of jobs that can be queued
 */
export type JobType = 'ANALYZE' | 'ORDER' | 'TRANSITION_AUDIO' | 'MIX';

/**
 * Status of a queued job
 */
export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

/**
 * Transition type between tracks
 */
export type TransitionType = 'crossfade' | 'stems' | 'cut';

/**
 * Configuration for a transition between two tracks
 */
export interface TransitionConfig {
  /** Source track ID */
  fromTrackId: string;
  /** Destination track ID */
  toTrackId: string;
  /** Type of transition to apply */
  type: TransitionType;
  /** Duration of transition in musical bars */
  durationBars: number;
  /** Whether to use stem separation for smoother mixing */
  useStemSeparation: boolean;
}

/**
 * Payload for track analysis job
 */
export interface AnalyzeJobPayload {
  /** Project ID */
  projectId: string;
  /** Track ID to analyze */
  trackId: string;
  /** Path to the audio file */
  filePath: string;
}

/**
 * Payload for track ordering optimization job
 */
export interface OrderJobPayload {
  /** Project ID */
  projectId: string;
  /** Track IDs to order */
  trackIds: string[];
}

/**
 * Track data for mix generation (includes analysis)
 */
export interface MixTrackData {
  /** Track ID */
  id: string;
  /** Path to the audio file */
  filePath: string;
  /** Track duration in seconds */
  duration: number | null;
  /** Analysis data */
  analysis: {
    bpm: number;
    energy: number;
    beats?: number[];
    introEnd?: number | null;
    outroStart?: number | null;
  } | null;
}

/**
 * Payload for mix generation job
 */
export interface MixJobPayload {
  /** Project ID */
  projectId: string;
  /** Tracks in order with full data */
  tracks: MixTrackData[];
  /** Transition configurations */
  transitions: TransitionConfig[];
}

/**
 * Payload for transition audio generation job
 */
export interface TransitionAudioJobPayload {
  /** Project ID */
  projectId: string;
  /** Transition ID */
  transitionId: string;
  /** Source track ID (outgoing) */
  fromTrackId: string;
  /** Destination track ID (incoming) */
  toTrackId: string;
  /** Source track file path */
  fromTrackPath: string;
  /** Destination track file path */
  toTrackPath: string;
  /** Source track BPM */
  fromTrackBpm: number;
  /** Destination track BPM */
  toTrackBpm: number;
  /** Source track beats array */
  fromTrackBeats: number[];
  /** Destination track beats array */
  toTrackBeats: number[];
  /** Source track outro start time */
  fromTrackOutroStart: number;
  /** Destination track intro end time */
  toTrackIntroEnd: number;
}

/**
 * Result of transition audio generation job
 */
export interface TransitionAudioJobResult {
  /** Transition ID */
  transitionId: string;
  /** Path to generated audio file */
  audioFilePath: string;
  /** Duration in milliseconds */
  audioDurationMs: number;
  /** Where track A ends in the transition (ms) */
  trackACutMs: number;
  /** Where track B starts in the transition (ms) */
  trackBStartMs: number;
}

/**
 * Result of track analysis job
 */
export interface AnalyzeJobResult {
  trackId: string;
  /** Track duration in seconds */
  duration?: number;
  bpm: number;
  bpmConfidence: number;
  key: string;
  keyConfidence: number;
  camelot: string;
  energy: number;
  danceability: number;
  loudness: number;
  /** Beat timestamps in seconds for beat-matching */
  beats?: number[];
  introStart?: number;
  introEnd?: number;
  outroStart?: number;
  outroEnd?: number;
  structureJson?: Record<string, unknown>;

  // Mixability fields
  introInstrumentalMs?: number;
  outroInstrumentalMs?: number;
  vocalPercentage?: number;
  vocalIntensity?: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH';
  maxBlendInDurationMs?: number;
  maxBlendOutDurationMs?: number;
  bestMixInPointMs?: number;
  bestMixOutPointMs?: number;
  mixFriendly?: boolean;
  mixabilityWarnings?: string[];
}

/**
 * Result of ordering optimization job
 */
export interface OrderJobResult {
  orderedTrackIds: string[];
  averageScore: number;
  processingTimeMs: number;
  excludedTrackIds: string[];
}

/**
 * Segment type in the mix
 */
export type MixSegmentType = 'SOLO' | 'TRANSITION';

/**
 * A single segment in the generated mix
 */
export interface MixSegmentResult {
  /** Position in the mix (0, 1, 2, ...) */
  position: number;
  /** Type of segment */
  type: MixSegmentType;
  /** Track ID for SOLO segments */
  trackId: string | null;
  /** Transition ID for TRANSITION segments */
  transitionId: string | null;
  /** Start time in source file (ms) */
  startMs: number;
  /** End time in source file (ms) */
  endMs: number;
  /** Duration of segment (ms) */
  durationMs: number;
  /** Generated audio file path for TRANSITION segments */
  audioFilePath: string | null;
  /** Error if segment generation failed */
  audioError?: string;
}

/**
 * Result of mix generation job
 */
export interface MixJobResult {
  /** Mix segments in playback order */
  segments: MixSegmentResult[];
  /** Map of transition IDs to their audio file paths */
  transitionFiles: Record<string, string>;
  /** Path to the final concatenated mix file */
  outputFile?: string;
  /** Total duration of the mix in milliseconds */
  totalDurationMs?: number;
  /** Error during concatenation (segments still available) */
  concatenationError?: string;
}

/**
 * Progress update for a running job (sent via WebSocket)
 */
export interface JobProgress {
  /** Project ID */
  projectId: string;
  /** Current processing stage */
  stage: MixStatus;
  /** Progress percentage (0-100) */
  progress: number;
  /** Human-readable current step description */
  currentStep?: string;
  /** Error message if failed */
  error?: string;
}

/**
 * Job record as stored in database
 */
export interface Job {
  id: string;
  projectId: string;
  type: JobType;
  status: JobStatus;
  payload: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  progress: number;
  startedAt?: Date;
  completedAt?: Date;
  createdAt: Date;
}
