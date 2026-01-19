import { useState, useCallback, useEffect, useRef } from 'react';
import type { JobProgress, MixOrderedEvent } from '@autodj/shared-types';

import { socketService } from '@/services/socket.service';
import { useProjectStore } from '@/stores/projectStore';

/**
 * Hook for subscribing to job progress updates via WebSocket
 */
export function useJobProgress(projectId: string) {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [mixOrdered, setMixOrdered] = useState<MixOrderedEvent | null>(null);
  const { fetchProject } = useProjectStore();
  const lastProgressRef = useRef<number>(0);
  const lastStageRef = useRef<string>('');

  const handleProgress = useCallback(
    (data: JobProgress) => {
      console.log('[useJobProgress] Received progress:', data);

      if (data.projectId === projectId) {
        setProgress(data);

        // Refresh project data when:
        // 1. Stage changes to completed/failed/ready
        // 2. Progress increases during analyzing (means a track was analyzed)
        // 3. Stage changes
        const shouldRefresh =
          data.stage === 'completed' ||
          data.stage === 'failed' ||
          data.stage === 'ready' ||
          (data.stage === 'analyzing' && data.progress > lastProgressRef.current) ||
          data.stage !== lastStageRef.current;

        if (shouldRefresh) {
          console.log('[useJobProgress] Refreshing project data');
          fetchProject(projectId);
        }

        lastProgressRef.current = data.progress;
        lastStageRef.current = data.stage;
      }
    },
    [projectId, fetchProject]
  );

  const handleMixOrdered = useCallback(
    (data: MixOrderedEvent) => {
      console.log('[useJobProgress] Received mix:ordered:', data);

      if (data.projectId === projectId) {
        setMixOrdered(data);
        // Always refresh project when ordering is complete to get updated transitions
        console.log('[useJobProgress] Refreshing project after ordering');
        fetchProject(projectId);
      }
    },
    [projectId, fetchProject]
  );

  const connect = useCallback(() => {
    console.log('[useJobProgress] Connecting to project:', projectId);
    socketService.connect();
    socketService.subscribeToProject(projectId);
    socketService.onProgress(handleProgress);
    socketService.onMixOrdered(handleMixOrdered);
  }, [projectId, handleProgress, handleMixOrdered]);

  const disconnect = useCallback(() => {
    console.log('[useJobProgress] Disconnecting from project:', projectId);
    socketService.offProgress(handleProgress);
    socketService.offMixOrdered(handleMixOrdered);
    socketService.unsubscribeFromProject(projectId);
  }, [projectId, handleProgress, handleMixOrdered]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    progress,
    mixOrdered,
    connect,
    disconnect,
  };
}
