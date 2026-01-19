import { api, extractData } from './api';
import type { Track } from './projects.service';

// =============================================================================
// Types
// =============================================================================

export type DraftStatus =
  | 'CREATED'
  | 'UPLOADING'
  | 'ANALYZING'
  | 'READY'
  | 'GENERATING'
  | 'COMPLETED'
  | 'FAILED';

export type DraftTransitionStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'ERROR';

export type TransitionMode = 'STEMS' | 'CROSSFADE';

export interface Draft {
  id: string;
  name: string;
  status: DraftStatus;
  userId: string;
  trackAId: string | null;
  trackA: Track | null;
  trackBId: string | null;
  trackB: Track | null;
  compatibilityScore: number | null;
  harmonicScore: number | null;
  bpmScore: number | null;
  energyScore: number | null;
  bpmDifference: number | null;
  transitionStatus: DraftTransitionStatus;
  transitionFilePath: string | null;
  transitionDurationMs: number | null;
  transitionMode: TransitionMode;
  trackAOutroMs: number | null;
  trackBIntroMs: number | null;
  transitionError: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DraftPlaybackInfo {
  draftId: string;
  totalDurationMs: number;
  segments: Array<{
    type: 'trackA' | 'transition' | 'trackB';
    startMs: number;
    endMs: number;
    durationMs: number;
    sourceStartMs: number;
    sourceEndMs: number;
  }>;
  trackAOutroMs: number;
  trackBIntroMs: number;
  transitionDurationMs: number;
}

// =============================================================================
// Service
// =============================================================================

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Draft management service
 */
export const draftsService = {
  /**
   * Get all drafts for the current user
   */
  async getAll(): Promise<Draft[]> {
    const response = await api.get('/drafts');
    return extractData<Draft[]>(response);
  },

  /**
   * Get a draft by ID
   */
  async getById(id: string): Promise<Draft> {
    const response = await api.get(`/drafts/${id}`);
    return extractData<Draft>(response);
  },

  /**
   * Create a new draft
   */
  async create(name?: string): Promise<Draft> {
    const response = await api.post('/drafts', { name });
    return extractData<Draft>(response);
  },

  /**
   * Delete a draft
   */
  async delete(id: string): Promise<void> {
    await api.delete(`/drafts/${id}`);
  },

  /**
   * Upload a track to slot A or B
   */
  async uploadTrack(
    draftId: string,
    slot: 'A' | 'B',
    file: File
  ): Promise<{ message: string; track: Track }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/drafts/${draftId}/tracks/${slot}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return extractData(response);
  },

  /**
   * Remove a track from slot A or B
   */
  async removeTrack(draftId: string, slot: 'A' | 'B'): Promise<void> {
    await api.delete(`/drafts/${draftId}/tracks/${slot}`);
  },

  /**
   * Swap tracks A and B
   */
  async swapTracks(draftId: string): Promise<Draft> {
    const response = await api.post(`/drafts/${draftId}/swap`);
    return extractData<{ draft: Draft }>(response).draft;
  },

  /**
   * Generate transition audio
   */
  async generateTransition(draftId: string): Promise<{ message: string; draftId: string }> {
    const response = await api.post(`/drafts/${draftId}/generate`);
    return extractData(response);
  },

  /**
   * Get playback info for the player
   */
  async getPlaybackInfo(draftId: string): Promise<DraftPlaybackInfo> {
    const response = await api.get(`/drafts/${draftId}/playback`);
    return extractData<DraftPlaybackInfo>(response);
  },

  /**
   * Get track audio URL
   */
  getTrackAudioUrl(draftId: string, slot: 'A' | 'B', token: string): string {
    return `${API_URL}/drafts/${draftId}/tracks/${slot}/audio?token=${token}`;
  },

  /**
   * Get transition audio URL
   * @param cacheBuster Optional cache-busting parameter (e.g., transitionDurationMs) to force re-fetch after regeneration
   */
  getTransitionAudioUrl(draftId: string, token: string, cacheBuster?: number): string {
    const base = `${API_URL}/drafts/${draftId}/transition/audio?token=${token}`;
    return cacheBuster ? `${base}&v=${cacheBuster}` : base;
  },
};
