import type { UserPlan } from './project';

/**
 * User information
 */
export interface User {
  /** Unique identifier */
  id: string;
  /** Email address */
  email: string;
  /** Display name */
  name?: string;
  /** Subscription plan */
  plan: UserPlan;
  /** Account creation timestamp */
  createdAt: Date;
  /** Last update timestamp */
  updatedAt: Date;
}

/**
 * Login request payload
 */
export interface LoginInput {
  /** User email */
  email: string;
  /** User password */
  password: string;
}

/**
 * Registration request payload
 */
export interface RegisterInput {
  /** User email */
  email: string;
  /** User password */
  password: string;
  /** Display name (optional) */
  name?: string;
}

/**
 * Authentication response with tokens
 */
export interface AuthResponse {
  /** JWT access token */
  accessToken: string;
  /** Token type (always "Bearer") */
  tokenType: 'Bearer';
  /** Token expiration in seconds */
  expiresIn: number;
  /** Authenticated user information */
  user: User;
}

/**
 * JWT payload structure
 */
export interface JwtPayload {
  /** User ID */
  sub: string;
  /** User email */
  email: string;
  /** Issued at timestamp */
  iat: number;
  /** Expiration timestamp */
  exp: number;
}
