import { useState, useCallback, useEffect } from 'react';
import type { DraftProgress, DraftTransitionCompleteEvent } from '@autodj/shared-types';

import { socketService } from '@/services/socket.service';
import { useDraftStore } from '@/stores/draftStore';

interface DraftAnalysisEvent {
  draftId: string;
  slot: 'A' | 'B';
  trackId: string;
  status: 'ANALYZING' | 'READY';
}

interface DraftErrorEvent {
  draftId: string;
  error: string;
}

/**
 * Hook for subscribing to draft progress updates via WebSocket
 */
export function useDraftProgress(draftId: string) {
  const [progress, setProgress] = useState<DraftProgress | null>(null);
  const [complete, setComplete] = useState<DraftTransitionCompleteEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { fetchDraft } = useDraftStore();

  const handleProgress = useCallback(
    (data: DraftProgress) => {
      console.log('[useDraftProgress] Received progress:', data);
      if (data.draftId === draftId) {
        setProgress(data);
      }
    },
    [draftId]
  );

  const handleComplete = useCallback(
    (data: DraftTransitionCompleteEvent) => {
      console.log('[useDraftProgress] Received complete:', data);
      if (data.draftId === draftId) {
        setComplete(data);
        setProgress(null);
        // Refresh draft data when transition is complete
        fetchDraft(draftId);
      }
    },
    [draftId, fetchDraft]
  );

  const handleError = useCallback(
    (data: DraftErrorEvent) => {
      console.log('[useDraftProgress] Received error:', data);
      if (data.draftId === draftId) {
        setError(data.error);
        setProgress(null);
        // Refresh draft data to get error state
        fetchDraft(draftId);
      }
    },
    [draftId, fetchDraft]
  );

  const handleAnalysis = useCallback(
    (data: DraftAnalysisEvent) => {
      console.log('[useDraftProgress] Received analysis:', data);
      if (data.draftId === draftId) {
        // Refresh draft data when analysis status changes
        fetchDraft(draftId);
      }
    },
    [draftId, fetchDraft]
  );

  const connect = useCallback(() => {
    console.log('[useDraftProgress] Connecting to draft:', draftId);
    socketService.connect();
    socketService.subscribeToDraft(draftId);
    socketService.onDraftProgress(handleProgress);
    socketService.onDraftComplete(handleComplete);
    socketService.onDraftError(handleError);
    socketService.onDraftAnalysis(handleAnalysis);
  }, [draftId, handleProgress, handleComplete, handleError, handleAnalysis]);

  const disconnect = useCallback(() => {
    console.log('[useDraftProgress] Disconnecting from draft:', draftId);
    socketService.offDraftProgress(handleProgress);
    socketService.offDraftComplete(handleComplete);
    socketService.offDraftError(handleError);
    socketService.offDraftAnalysis(handleAnalysis);
    socketService.unsubscribeFromDraft(draftId);
  }, [draftId, handleProgress, handleComplete, handleError, handleAnalysis]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const reset = useCallback(() => {
    setProgress(null);
    setComplete(null);
    setError(null);
  }, []);

  return {
    progress,
    complete,
    error,
    connect,
    disconnect,
    reset,
  };
}
