/**
 * Error codes for API responses
 */
export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'INTERNAL_ERROR'
  | 'BAD_REQUEST'
  | 'RATE_LIMITED'
  | 'FILE_TOO_LARGE'
  | 'INVALID_FILE_TYPE'
  | 'PROJECT_LIMIT_EXCEEDED'
  | 'TRACK_LIMIT_EXCEEDED';

/**
 * API error structure
 */
export interface ApiError {
  /** Error code for programmatic handling */
  code: ApiErrorCode;
  /** Human-readable error message */
  message: string;
  /** Additional error details (e.g., validation errors) */
  details?: Record<string, string[]>;
}

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T = unknown> {
  /** Whether the request succeeded */
  success: boolean;
  /** Response data (present on success) */
  data?: T;
  /** Error information (present on failure) */
  error?: ApiError;
}

/**
 * Paginated list response
 */
export interface PaginatedResponse<T> {
  /** Items in current page */
  items: T[];
  /** Total number of items across all pages */
  total: number;
  /** Current page number (1-indexed) */
  page: number;
  /** Number of items per page */
  pageSize: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether there's a next page */
  hasNext: boolean;
  /** Whether there's a previous page */
  hasPrevious: boolean;
}

/**
 * Pagination query parameters
 */
export interface PaginationParams {
  /** Page number (1-indexed) */
  page?: number;
  /** Items per page */
  pageSize?: number;
  /** Sort field */
  sortBy?: string;
  /** Sort direction */
  sortOrder?: 'asc' | 'desc';
}
