import type { AuthResponse, LoginInput, RegisterInput } from '@autodj/shared-types';

import { api, extractData } from './api';

/**
 * Authentication service for login, register, and profile operations
 */
export const authService = {
  async login(data: LoginInput): Promise<AuthResponse> {
    const response = await api.post('/auth/login', data);
    return extractData<AuthResponse>(response);
  },

  async register(data: RegisterInput): Promise<AuthResponse> {
    const response = await api.post('/auth/register', data);
    return extractData<AuthResponse>(response);
  },

  async getProfile() {
    const response = await api.get('/auth/me');
    return extractData(response);
  },
};
