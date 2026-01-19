/**
 * Draft types for 2-track transition proof of concept
 */

import type { Track } from './track';

// =============================================================================
// Enums
// =============================================================================

export type DraftStatus =
  | 'CREATED'
  | 'UPLOADING'
  | 'ANALYZING'
  | 'READY'
  | 'GENERATING'
  | 'COMPLETED'
  | 'FAILED';

export type DraftTransitionStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'ERROR';

export type TransitionMode = 'STEMS' | 'CROSSFADE';

// =============================================================================
// Draft Entity
// =============================================================================

export interface Draft {
  id: string;
  name: string;
  status: DraftStatus;
  userId: string;

  // Track references (using existing Track entity)
  trackAId: string | null;
  trackA: Track | null;
  trackBId: string | null;
  trackB: Track | null;

  // Compatibility scores
  compatibilityScore: number | null;
  harmonicScore: number | null;
  bpmScore: number | null;
  energyScore: number | null;
  bpmDifference: number | null;

  // Transition generation
  transitionStatus: DraftTransitionStatus;
  transitionFilePath: string | null;
  transitionDurationMs: number | null;
  transitionMode: TransitionMode;
  trackAOutroMs: number | null;
  trackBIntroMs: number | null;

  // Cut points for seamless playback (to avoid audio duplication)
  trackAPlayUntilMs: number | null;  // Stop playing Track A here (transition takes over)
  trackBStartFromMs: number | null;  // Start playing Track B here (after transition)

  transitionError: string | null;

  errorMessage: string | null;
  createdAt: Date | string;
  updatedAt: Date | string;
}

// =============================================================================
// API DTOs
// =============================================================================

export interface CreateDraftInput {
  name: string;
}

export interface DraftSummary {
  id: string;
  name: string;
  status: DraftStatus;
  trackA: {
    id: string;
    originalName: string;
    bpm: number | null;
    camelot: string | null;
  } | null;
  trackB: {
    id: string;
    originalName: string;
    bpm: number | null;
    camelot: string | null;
  } | null;
  compatibilityScore: number | null;
  transitionStatus: DraftTransitionStatus;
  createdAt: Date | string;
}

// =============================================================================
// WebSocket Events
// =============================================================================

export type DraftTransitionStep =
  | 'extraction'
  | 'stems'
  | 'time-stretch'
  | 'beatmatch'
  | 'mixing'
  | 'eq'
  | 'export';

export interface DraftProgress {
  draftId: string;
  step: DraftTransitionStep;
  progress: number; // 0-100
  status: DraftTransitionStatus;
  message?: string;
  error?: string;
}

export interface DraftTransitionCompleteEvent {
  draftId: string;
  transitionFilePath: string;
  transitionDurationMs: number;
  transitionMode: TransitionMode;
  trackAOutroMs: number;
  trackBIntroMs: number;
  // Cut points for seamless playback
  trackAPlayUntilMs?: number;
  trackBStartFromMs?: number;
}

// =============================================================================
// Job Payload
// =============================================================================

export interface DraftTransitionJobPayload {
  draftId: string;
  trackAPath: string;
  trackBPath: string;
  trackABpm: number;
  trackBBpm: number;
  trackABeats: number[];
  trackBBeats: number[];
  trackAOutroStartMs: number;
  trackBIntroEndMs: number;
  trackAEnergy: number;
  trackBEnergy: number;
  trackADurationMs: number;
  trackBDurationMs: number;
  outputPath: string;
  // Camelot keys for LLM-powered transition planning
  trackAKey?: string;
  trackBKey?: string;
}

export interface DraftTransitionJobResult {
  draftId: string;
  transitionFilePath: string;
  transitionDurationMs: number;
  transitionMode: TransitionMode;
  trackAOutroMs: number;
  trackBIntroMs: number;
  // Cut points for seamless playback (to avoid audio duplication)
  trackAPlayUntilMs?: number;  // Stop playing Track A here
  trackBStartFromMs?: number;  // Start playing Track B here
  error?: string;
}

// =============================================================================
// Player Types
// =============================================================================

export interface DraftPlayerSegment {
  type: 'trackA' | 'transition' | 'trackB';
  startMs: number; // Global start position in full mix
  endMs: number; // Global end position in full mix
  durationMs: number;
  // Source info for playback
  audioUrl: string;
  sourceStartMs: number; // Where to start in the source file
  sourceEndMs: number; // Where to end in the source file
}

export interface DraftPlaybackInfo {
  draftId: string;
  totalDurationMs: number;
  segments: DraftPlayerSegment[];
  trackAOutroMs: number;
  trackBIntroMs: number;
  transitionDurationMs: number;
  // Cut points for seamless playback
  trackAPlayUntilMs?: number;
  trackBStartFromMs?: number;
}
