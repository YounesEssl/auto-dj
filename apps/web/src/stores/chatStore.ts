import { create } from 'zustand';

import { chatService, type ChatMessage } from '@/services/chat.service';
import type { ChatResponseEvent } from '@/services/socket.service';

// Simple unique ID generator
let idCounter = 0;
const generateId = () => `chat-${Date.now()}-${++idCounter}`;

interface ChatState {
  // State
  messages: ChatMessage[];
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  currentProjectId: string | null;

  // Actions
  openChat: () => void;
  closeChat: () => void;
  toggleChat: () => void;
  setProjectId: (projectId: string | null) => void;
  sendMessage: (projectId: string, message: string) => Promise<void>;
  handleChatResponse: (response: ChatResponseEvent) => void;
  loadHistory: (projectId: string) => Promise<void>;
  clearHistory: (projectId: string) => Promise<void>;
  clearMessages: () => void;
}

/**
 * Chat store for AI-assisted track reordering
 */
export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isOpen: false,
  isLoading: false,
  error: null,
  currentProjectId: null,

  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),
  toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),

  setProjectId: (projectId) => {
    const { currentProjectId, clearMessages } = get();
    if (projectId !== currentProjectId) {
      clearMessages();
      set({ currentProjectId: projectId });
    }
  },

  sendMessage: async (projectId, message) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmedMessage,
      timestamp: new Date(),
    };

    // Add loading message for assistant
    const loadingMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    set((state) => ({
      messages: [...state.messages, userMessage, loadingMessage],
      isLoading: true,
      error: null,
    }));

    try {
      await chatService.sendMessage(projectId, trimmedMessage);
      // Response will come via WebSocket
    } catch (err) {
      // Remove loading message and add error
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== loadingMessage.id),
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to send message',
      }));
    }
  },

  handleChatResponse: (response) => {
    const { currentProjectId } = get();

    // Ignore responses for other projects
    if (response.projectId !== currentProjectId) return;

    // Create assistant message
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: response.response,
      timestamp: new Date(),
      newOrder: response.newOrder,
      changesMade: response.changesMade,
    };

    set((state) => ({
      // Replace loading message with actual response
      messages: state.messages
        .filter((m) => !m.isLoading)
        .concat(assistantMessage),
      isLoading: false,
    }));
  },

  loadHistory: async (projectId) => {
    try {
      const { history } = await chatService.getHistory(projectId);

      const messages: ChatMessage[] = history.map((msg) => ({
        id: generateId(),
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        newOrder: msg.newOrder,
        changesMade: msg.changesMade,
      }));

      set({ messages, currentProjectId: projectId });
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  },

  clearHistory: async (projectId) => {
    try {
      await chatService.clearHistory(projectId);
      set({ messages: [] });
    } catch (err) {
      console.error('Failed to clear chat history:', err);
    }
  },

  clearMessages: () => set({ messages: [], error: null }),
}));
