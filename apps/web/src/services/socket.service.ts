import { io, Socket } from 'socket.io-client';
import type { JobProgress, MixOrderedEvent, DraftProgress, DraftTransitionCompleteEvent } from '@autodj/shared-types';

// Transition progress event for real-time generation tracking
export interface TransitionProgressEvent {
  projectId: string;
  transitionId: string;
  status: 'PROCESSING' | 'COMPLETED' | 'ERROR';
  progress?: number;
  completedCount?: number;
  totalCount?: number;
  error?: string;
  stage?: string;
  message?: string;
}

// In production (Docker), use same origin (nginx proxies /socket.io to API)
// In development, use VITE_WS_URL or localhost:3001
const SOCKET_URL = import.meta.env.VITE_WS_URL || (
  import.meta.env.PROD ? window.location.origin : 'http://localhost:3001'
);

let socket: Socket | null = null;

/**
 * Socket.io service for real-time communication
 */
export const socketService = {
  connect(): Socket {
    if (!socket) {
      console.log('[Socket] Connecting to:', SOCKET_URL);
      socket = io(SOCKET_URL, {
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        transports: ['websocket', 'polling'],
      });

      socket.on('connect', () => {
        console.log('[Socket] Connected:', socket?.id);
      });

      socket.on('connect_error', (err) => {
        console.error('[Socket] Connection error:', err.message);
      });

      socket.on('disconnect', (reason) => {
        console.log('[Socket] Disconnected:', reason);
      });
    }
    return socket;
  },

  disconnect() {
    if (socket) {
      socket.disconnect();
      socket = null;
    }
  },

  subscribeToProject(projectId: string) {
    if (socket) {
      socket.emit('subscribe', { projectId });
    }
  },

  unsubscribeFromProject(projectId: string) {
    if (socket) {
      socket.emit('unsubscribe', { projectId });
    }
  },

  onProgress(callback: (progress: JobProgress) => void) {
    if (socket) {
      socket.on('progress', callback);
    }
  },

  offProgress(callback: (progress: JobProgress) => void) {
    if (socket) {
      socket.off('progress', callback);
    }
  },

  onMixOrdered(callback: (data: MixOrderedEvent) => void) {
    if (socket) {
      socket.on('mix:ordered', callback);
    }
  },

  offMixOrdered(callback: (data: MixOrderedEvent) => void) {
    if (socket) {
      socket.off('mix:ordered', callback);
    }
  },

  // Transition progress (real-time generation updates)
  onTransitionProgress(callback: (data: TransitionProgressEvent) => void) {
    if (socket) {
      socket.on('transition:progress', callback);
    }
  },

  offTransitionProgress(callback: (data: TransitionProgressEvent) => void) {
    if (socket) {
      socket.off('transition:progress', callback);
    }
  },

  // Draft-specific methods
  subscribeToDraft(draftId: string) {
    if (socket) {
      socket.emit('draft:subscribe', { draftId });
    }
  },

  unsubscribeFromDraft(draftId: string) {
    if (socket) {
      socket.emit('draft:unsubscribe', { draftId });
    }
  },

  onDraftProgress(callback: (progress: DraftProgress) => void) {
    if (socket) {
      socket.on('draft:progress', callback);
    }
  },

  offDraftProgress(callback: (progress: DraftProgress) => void) {
    if (socket) {
      socket.off('draft:progress', callback);
    }
  },

  onDraftComplete(callback: (data: DraftTransitionCompleteEvent) => void) {
    if (socket) {
      socket.on('draft:complete', callback);
    }
  },

  offDraftComplete(callback: (data: DraftTransitionCompleteEvent) => void) {
    if (socket) {
      socket.off('draft:complete', callback);
    }
  },

  onDraftError(callback: (data: { draftId: string; error: string }) => void) {
    if (socket) {
      socket.on('draft:error', callback);
    }
  },

  offDraftError(callback: (data: { draftId: string; error: string }) => void) {
    if (socket) {
      socket.off('draft:error', callback);
    }
  },

  onDraftAnalysis(callback: (data: { draftId: string; slot: 'A' | 'B'; trackId: string; status: 'ANALYZING' | 'READY' }) => void) {
    if (socket) {
      socket.on('draft:analysis', callback);
    }
  },

  offDraftAnalysis(callback: (data: { draftId: string; slot: 'A' | 'B'; trackId: string; status: 'ANALYZING' | 'READY' }) => void) {
    if (socket) {
      socket.off('draft:analysis', callback);
    }
  },

  // Chat-specific methods
  onChatResponse(callback: (data: ChatResponseEvent) => void) {
    if (socket) {
      socket.on('chat:response', callback);
    }
  },

  offChatResponse(callback: (data: ChatResponseEvent) => void) {
    if (socket) {
      socket.off('chat:response', callback);
    }
  },

  getSocket(): Socket | null {
    return socket;
  },
};

// Chat response event type
export interface ChatResponseEvent {
  projectId: string;
  response: string;
  newOrder?: string[] | null;
  reasoning?: string | null;
  changesMade: string[];
  projectData?: {
    orderedTracks: string[];
    transitions: unknown[];
    averageMixScore: number | null;
  } | null;
}
