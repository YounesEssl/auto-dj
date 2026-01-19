import type { Track } from './track';
import type { Transition } from './transition';

/**
 * Status of a mix project throughout its lifecycle
 */
export type MixStatus =
  | 'created'
  | 'uploading'
  | 'analyzing'
  | 'ordering'
  | 'ready'
  | 'mixing'
  | 'completed'
  | 'failed';

/**
 * User subscription plan levels
 */
export type UserPlan = 'FREE' | 'PRO' | 'ENTERPRISE';

/**
 * Represents a mix project containing multiple tracks
 */
export interface MixProject {
  /** Unique identifier */
  id: string;
  /** Owner user ID */
  userId: string;
  /** Project display name */
  name: string;
  /** Current processing status */
  status: MixStatus;
  /** Tracks in the project */
  tracks: Track[];
  /** Optimized track order (array of track IDs) */
  orderedTrackIds?: string[];
  /** Transitions between consecutive tracks */
  transitions?: Transition[];
  /** Average mix score (0-100) */
  averageMixScore?: number;
  /** Timestamp of last ordering calculation */
  lastOrderedAt?: Date;
  /** Path to the final mixed audio file */
  outputFile?: string;
  /** Error message if status is 'failed' */
  errorMessage?: string;
  /** Creation timestamp */
  createdAt: Date;
  /** Last update timestamp */
  updatedAt: Date;
}

/**
 * Input for creating a new project
 */
export interface CreateProjectInput {
  name: string;
}

/**
 * Input for updating a project
 */
export interface UpdateProjectInput {
  name?: string;
  status?: MixStatus;
  orderedTrackIds?: string[];
  outputFile?: string;
  errorMessage?: string;
}

/**
 * Project summary for list views
 */
export interface ProjectSummary {
  id: string;
  name: string;
  status: MixStatus;
  trackCount: number;
  createdAt: Date;
  updatedAt: Date;
}
