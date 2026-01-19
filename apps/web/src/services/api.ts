import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

import { useAuthStore } from '@/stores/authStore';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Axios instance configured for API calls
 */
export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, logout user
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

/**
 * Extract data from API response
 */
export function extractData<T>(response: { data: { success: boolean; data?: T } }): T {
  if (response.data.success && response.data.data !== undefined) {
    return response.data.data;
  }
  throw new Error('Invalid API response');
}
