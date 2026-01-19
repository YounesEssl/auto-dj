/**
 * Application constants
 */

export const APP_NAME = 'AutoDJ';

export const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
export const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:3001';

export const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
export const MAX_TRACKS_PER_PROJECT = 50;

export const ACCEPTED_AUDIO_TYPES = {
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
  'audio/x-wav': ['.wav'],
};

export const PROJECT_STATUSES = {
  CREATED: 'created',
  UPLOADING: 'uploading',
  ANALYZING: 'analyzing',
  ORDERING: 'ordering',
  MIXING: 'mixing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;
