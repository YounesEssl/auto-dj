import { PrismaClient } from '@prisma/client';

/**
 * Global Prisma client instance.
 * Uses a singleton pattern to prevent multiple instances during development hot-reloading.
 */

// Extend global type to include prisma
declare global {
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

/**
 * Creates or returns existing Prisma client instance.
 * In development, the client is cached on the global object to prevent
 * too many database connections during hot module replacement.
 */
function createPrismaClient(): PrismaClient {
  return new PrismaClient({
    log:
      process.env.NODE_ENV === 'development'
        ? ['query', 'error', 'warn']
        : ['error'],
  });
}

/**
 * Singleton Prisma client instance
 */
export const prisma = global.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== 'production') {
  global.prisma = prisma;
}

// Re-export Prisma types for convenience
export { PrismaClient, Prisma } from '@prisma/client';
export type {
  User,
  Project,
  Track,
  TrackAnalysis,
  Transition,
  MixSegment,
  Job,
  Draft,
  Plan,
  ProjectStatus,
  JobType,
  JobStatus,
  HarmonicCompatibility,
  TransitionAudioStatus,
  MixSegmentType,
  MixSegmentStatus,
  DraftStatus,
  DraftTransitionStatus,
  TransitionMode,
} from '@prisma/client';
