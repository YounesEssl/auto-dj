import { useEffect, useCallback } from 'react';
import { useStudioStore } from '@/stores/studioStore';

interface KeyboardShortcutsOptions {
  enabled?: boolean;
  onSkipBack?: () => void;
  onSkipForward?: () => void;
}

/**
 * Hook for handling keyboard shortcuts in the Studio
 *
 * Shortcuts:
 * - Space: Play/Pause
 * - Left Arrow: Skip back 10s
 * - Right Arrow: Skip forward 10s
 * - [ : Previous segment
 * - ] : Next segment
 * - B : Toggle sidebar
 * - I : Toggle inspector
 * - Escape: Clear selection
 */
export function useKeyboardShortcuts(options: KeyboardShortcutsOptions = {}) {
  const { enabled = true, onSkipBack, onSkipForward } = options;
  const {
    isPlaying,
    setIsPlaying,
    toggleSidebar,
    setIsInspectorOpen,
    isInspectorOpen,
    clearSelection,
  } = useStudioStore();

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore if typing in an input field
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      switch (event.code) {
        case 'Space':
          event.preventDefault();
          setIsPlaying(!isPlaying);
          break;

        case 'ArrowLeft':
          event.preventDefault();
          onSkipBack?.();
          break;

        case 'ArrowRight':
          event.preventDefault();
          onSkipForward?.();
          break;

        case 'BracketLeft': // [
          event.preventDefault();
          // Previous segment - handled by PlayerBar
          break;

        case 'BracketRight': // ]
          event.preventDefault();
          // Next segment - handled by PlayerBar
          break;

        case 'KeyB':
          if (!event.metaKey && !event.ctrlKey) {
            event.preventDefault();
            toggleSidebar();
          }
          break;

        case 'KeyI':
          if (!event.metaKey && !event.ctrlKey) {
            event.preventDefault();
            setIsInspectorOpen(!isInspectorOpen);
          }
          break;

        case 'Escape':
          event.preventDefault();
          clearSelection();
          break;
      }
    },
    [isPlaying, setIsPlaying, toggleSidebar, setIsInspectorOpen, isInspectorOpen, clearSelection, onSkipBack, onSkipForward]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);
}
