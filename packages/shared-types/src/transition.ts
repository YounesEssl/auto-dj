/**
 * Harmonic compatibility types between tracks based on Camelot wheel
 */
export type HarmonicCompatibility =
  | 'PERFECT_MATCH'
  | 'ADJACENT'
  | 'RELATIVE'
  | 'DIAGONAL_ADJACENT'
  | 'ENERGY_BOOST'
  | 'COMPATIBLE'
  | 'RISKY';

/**
 * Status of transition audio generation
 */
export type TransitionAudioStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'ERROR';

/**
 * Transition data between two tracks in a mix
 */
export interface Transition {
  /** Unique identifier */
  id: string;
  /** Project ID */
  projectId: string;
  /** Source track ID */
  fromTrackId: string;
  /** Destination track ID */
  toTrackId: string;
  /** Position in the transition sequence (0-indexed) */
  position: number;
  /** Total transition score (0-100) */
  score: number;
  /** Harmonic component score (0-100) */
  harmonicScore: number;
  /** BPM component score (0-100) */
  bpmScore: number;
  /** Energy component score (0-100) */
  energyScore: number;
  /** Type of harmonic compatibility */
  compatibilityType: HarmonicCompatibility;
  /** BPM difference as percentage */
  bpmDifference: number;
  /** Energy difference (can be negative) */
  energyDifference: number;
  /** Audio generation status */
  audioStatus: TransitionAudioStatus;
  /** Path to generated audio file */
  audioFilePath?: string;
  /** Duration of the transition audio in milliseconds */
  audioDurationMs?: number;
  /** Where track A ends in the transition (ms) */
  trackACutMs?: number;
  /** Where track B starts in the transition (ms) */
  trackBStartMs?: number;
  /** Error message if audio generation failed */
  audioError?: string;
  /** Creation timestamp */
  createdAt: Date;
}

/**
 * Result of the track ordering algorithm
 */
export interface OrderingResult {
  /** Project ID */
  projectId: string;
  /** Track IDs in optimal order */
  orderedTrackIds: string[];
  /** Transitions between consecutive tracks */
  transitions: Transition[];
  /** Average score across all transitions */
  averageScore: number;
  /** Processing time in milliseconds */
  processingTimeMs: number;
  /** Track IDs excluded from ordering (missing analysis) */
  excludedTrackIds: string[];
}

/**
 * Payload for mix:ordered WebSocket event
 */
export interface MixOrderedEvent {
  /** Project ID */
  projectId: string;
  /** Track IDs in optimal order */
  orderedTrackIds: string[];
  /** Transitions with scores and metadata */
  transitions: Transition[];
  /** Average score of the mix */
  averageScore: number;
  /** Processing time in milliseconds */
  processingTimeMs: number;
}
