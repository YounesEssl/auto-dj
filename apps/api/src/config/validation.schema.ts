import * as Joi from 'joi';

/**
 * Joi validation schema for environment variables
 * Ensures all required configuration is present and valid
 */
export const validationSchema = Joi.object({
  // Node environment
  NODE_ENV: Joi.string()
    .valid('development', 'production', 'test')
    .default('development'),

  // API
  API_PORT: Joi.number().default(3001),
  API_HOST: Joi.string().default('0.0.0.0'),
  API_PREFIX: Joi.string().default('api/v1'),

  // Database
  DATABASE_URL: Joi.string().required(),

  // Redis
  REDIS_HOST: Joi.string().default('localhost'),
  REDIS_PORT: Joi.number().default(6379),
  REDIS_PASSWORD: Joi.string().allow('').optional(),

  // JWT
  JWT_SECRET: Joi.string().min(32).required(),
  JWT_EXPIRATION: Joi.string().default('7d'),

  // Storage
  STORAGE_TYPE: Joi.string().valid('local', 's3').default('local'),
  STORAGE_PATH: Joi.string().default('./storage'),

  // AWS (required only if STORAGE_TYPE is 's3')
  AWS_ACCESS_KEY_ID: Joi.string().when('STORAGE_TYPE', {
    is: 's3',
    then: Joi.required(),
    otherwise: Joi.optional(),
  }),
  AWS_SECRET_ACCESS_KEY: Joi.string().when('STORAGE_TYPE', {
    is: 's3',
    then: Joi.required(),
    otherwise: Joi.optional(),
  }),
  AWS_BUCKET_NAME: Joi.string().when('STORAGE_TYPE', {
    is: 's3',
    then: Joi.required(),
    otherwise: Joi.optional(),
  }),
  AWS_REGION: Joi.string().default('eu-west-1'),

  // CORS
  CORS_ORIGINS: Joi.string().default('http://localhost:5173'),

  // Queue
  QUEUE_ANALYZE_CONCURRENCY: Joi.number().default(2),
  QUEUE_MIX_CONCURRENCY: Joi.number().default(1),

  // Limits
  MAX_TRACK_DURATION_MINUTES: Joi.number().default(15),
  MAX_TRACKS_PER_PROJECT: Joi.number().default(50),

  // Logging
  LOG_LEVEL: Joi.string()
    .valid('fatal', 'error', 'warn', 'info', 'debug', 'trace')
    .default('info'),
});
