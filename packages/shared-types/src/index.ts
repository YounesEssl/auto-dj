/**
 * @packageDocumentation
 * Shared TypeScript types for the AutoDJ monorepo.
 * These types are used across the frontend, backend, and worker services.
 */

// Track types
export type {
  SectionType,
  TrackSection,
  TrackStructure,
  AnalysisConfidence,
  TrackAnalysis,
  Track,
  CreateTrackInput,
} from './track';

// Project types
export type {
  MixStatus,
  UserPlan,
  MixProject,
  CreateProjectInput,
  UpdateProjectInput,
  ProjectSummary,
} from './project';

// Job types
export type {
  JobType,
  JobStatus,
  TransitionType,
  TransitionConfig,
  AnalyzeJobPayload,
  OrderJobPayload,
  MixTrackData,
  MixJobPayload,
  TransitionAudioJobPayload,
  AnalyzeJobResult,
  OrderJobResult,
  MixSegmentType,
  MixSegmentResult,
  MixJobResult,
  TransitionAudioJobResult,
  JobProgress,
  Job,
} from './job';

// Transition types
export type {
  HarmonicCompatibility,
  TransitionAudioStatus,
  Transition,
  OrderingResult,
  MixOrderedEvent,
} from './transition';

// API types
export type {
  ApiErrorCode,
  ApiError,
  ApiResponse,
  PaginatedResponse,
  PaginationParams,
} from './api';

// Auth types
export type {
  User,
  LoginInput,
  RegisterInput,
  AuthResponse,
  JwtPayload,
} from './auth';

// Draft types
export type {
  DraftStatus,
  DraftTransitionStatus,
  TransitionMode,
  Draft,
  CreateDraftInput,
  DraftSummary,
  DraftTransitionStep,
  DraftProgress,
  DraftTransitionCompleteEvent,
  DraftTransitionJobPayload,
  DraftTransitionJobResult,
  DraftPlayerSegment,
  DraftPlaybackInfo,
} from './draft';
