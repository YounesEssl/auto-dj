/**
 * Application configuration factory
 * Loads and transforms environment variables into typed configuration
 */
export const configuration = () => ({
  // API Configuration
  api: {
    port: parseInt(process.env.API_PORT || '3001', 10),
    host: process.env.API_HOST || '0.0.0.0',
    prefix: process.env.API_PREFIX || 'api/v1',
    nodeEnv: process.env.NODE_ENV || 'development',
  },

  // Database Configuration
  database: {
    url: process.env.DATABASE_URL,
  },

  // Redis Configuration
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379', 10),
    password: process.env.REDIS_PASSWORD || undefined,
  },

  // JWT Configuration
  jwt: {
    secret: process.env.JWT_SECRET,
    expiration: process.env.JWT_EXPIRATION || '7d',
  },

  // Storage Configuration
  storage: {
    type: process.env.STORAGE_TYPE || 'local',
    path: process.env.STORAGE_PATH || './storage',
    aws: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      bucketName: process.env.AWS_BUCKET_NAME,
      region: process.env.AWS_REGION || 'eu-west-1',
    },
  },

  // CORS Configuration
  cors: {
    origins: (process.env.CORS_ORIGINS || 'http://localhost:5173').split(','),
  },

  // Queue Configuration
  queue: {
    analyzeConcurrency: parseInt(process.env.QUEUE_ANALYZE_CONCURRENCY || '2', 10),
    mixConcurrency: parseInt(process.env.QUEUE_MIX_CONCURRENCY || '1', 10),
  },

  // Audio Processing Limits
  limits: {
    maxTrackDurationMinutes: parseInt(process.env.MAX_TRACK_DURATION_MINUTES || '15', 10),
    maxTracksPerProject: parseInt(process.env.MAX_TRACKS_PER_PROJECT || '50', 10),
  },
});

export type AppConfiguration = ReturnType<typeof configuration>;
