import { api, extractData } from './api';
import type { Transition } from './projects.service';

/**
 * Chat message in conversation history
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  newOrder?: string[] | null;
  changesMade?: string[];
  isLoading?: boolean;
}

/**
 * Response from chat API
 */
export interface ChatApiResponse {
  jobId: string;
  message: string;
}

/**
 * Chat response from WebSocket
 */
export interface ChatResponseEvent {
  projectId: string;
  response: string;
  newOrder?: string[] | null;
  reasoning?: string | null;
  changesMade: string[];
  projectData?: {
    orderedTracks: string[];
    transitions: Transition[];
    averageMixScore: number | null;
  } | null;
}

/**
 * Conversation history from API
 */
export interface ConversationHistory {
  history: Array<{
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    newOrder?: string[] | null;
    changesMade?: string[];
  }>;
}

/**
 * Chat service for AI-assisted track reordering
 */
export const chatService = {
  /**
   * Send a chat message for track reordering
   */
  async sendMessage(projectId: string, message: string): Promise<ChatApiResponse> {
    const response = await api.post(`/projects/${projectId}/chat`, { message });
    return extractData<ChatApiResponse>(response);
  },

  /**
   * Get conversation history for a project
   */
  async getHistory(projectId: string): Promise<ConversationHistory> {
    const response = await api.get(`/projects/${projectId}/chat/history`);
    return extractData<ConversationHistory>(response);
  },

  /**
   * Clear conversation history for a project
   */
  async clearHistory(projectId: string): Promise<void> {
    await api.delete(`/projects/${projectId}/chat/history`);
  },
};
