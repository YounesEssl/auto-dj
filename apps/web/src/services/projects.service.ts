import { api, extractData } from './api';

export interface TrackSection {
  start: number;
  end: number;
  type: 'drop' | 'breakdown' | 'buildup' | 'main';
}

export interface TrackStructure {
  intro: { start: number; end: number };
  outro: { start: number; end: number };
  sections: TrackSection[];
}

export type VocalIntensity = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH';

export interface TrackAnalysis {
  bpm: number;
  key: string;
  camelot: string;
  energy: number;
  danceability: number;
  loudness: number;
  bpmConfidence: number;
  keyConfidence: number;
  introStart: number | null;
  introEnd: number | null;
  outroStart: number | null;
  outroEnd: number | null;
  structureJson: TrackStructure | null;
  // Mixability fields
  introInstrumentalMs?: number | null;
  outroInstrumentalMs?: number | null;
  vocalPercentage?: number | null;
  vocalIntensity?: VocalIntensity | null;
  maxBlendInDurationMs?: number | null;
  maxBlendOutDurationMs?: number | null;
  bestMixInPointMs?: number | null;
  bestMixOutPointMs?: number | null;
  mixFriendly?: boolean | null;
  mixabilityWarnings?: string[] | null;
}

export interface Track {
  id: string;
  filename: string;
  originalName: string;
  duration: number | null;
  fileSize: number;
  mimeType: string;
  createdAt: string;
  analysis?: TrackAnalysis | null;
}

/**
 * Harmonic compatibility types based on Camelot wheel
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
 * Transition between two tracks
 */
export interface Transition {
  id: string;
  projectId: string;
  fromTrackId: string;
  toTrackId: string;
  position: number;
  score: number;
  harmonicScore: number;
  bpmScore: number;
  energyScore: number;
  compatibilityType: HarmonicCompatibility;
  bpmDifference: number;
  energyDifference: number;
  audioStatus: TransitionAudioStatus;
  audioFilePath?: string;
  audioDurationMs?: number;
  trackACutMs?: number;
  trackBStartMs?: number;
  audioError?: string;
  createdAt: string;
}

export interface Project {
  id: string;
  name: string;
  status: string;
  tracks: Track[];
  orderedTracks: string[];
  transitions: Transition[];
  averageMixScore: number | null;
  lastOrderedAt: string | null;
  outputFile: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
  _count?: {
    tracks: number;
  };
}

/**
 * Project management service
 */
export const projectsService = {
  async getAll(): Promise<Project[]> {
    const response = await api.get('/projects');
    return extractData<Project[]>(response);
  },

  async getById(id: string): Promise<Project> {
    const response = await api.get(`/projects/${id}`);
    return extractData<Project>(response);
  },

  async create(name: string): Promise<Project> {
    const response = await api.post('/projects', { name });
    return extractData<Project>(response);
  },

  async update(id: string, data: { name?: string }): Promise<Project> {
    const response = await api.patch(`/projects/${id}`, data);
    return extractData<Project>(response);
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/projects/${id}`);
  },

  async generateMix(id: string): Promise<void> {
    await api.post(`/projects/${id}/generate`);
  },

  async generateTransitions(id: string): Promise<{
    message: string;
    projectId: string;
    transitionCount: number;
  }> {
    const response = await api.post(`/projects/${id}/transitions/generate`);
    return extractData(response);
  },

  async calculateOrder(id: string): Promise<{
    orderedTrackIds: string[];
    averageScore: number;
    processingTimeMs: number;
    excludedTrackIds: string[];
  }> {
    const response = await api.post(`/projects/${id}/mix/order`);
    return extractData(response);
  },

  async uploadTracks(id: string, files: File[]): Promise<Track[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post(`/projects/${id}/tracks`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return extractData<{ tracks: Track[] }>(response).tracks;
  },

  async deleteTrack(projectId: string, trackId: string): Promise<void> {
    await api.delete(`/projects/${projectId}/tracks/${trackId}`);
  },
};
