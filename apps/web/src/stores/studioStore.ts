import { create } from 'zustand';

import type { Track, Transition } from '@/services/projects.service';

export type SelectionType = 'track' | 'transition' | null;

export interface Selection {
  type: SelectionType;
  id: string | null;
  data: Track | Transition | null;
}

interface StudioState {
  // Current selection in the studio
  selection: Selection;

  // Timeline state
  timelineTracks: string[]; // Track IDs in order

  // UI state
  isInspectorOpen: boolean;
  isSidebarCollapsed: boolean;
  isPlaying: boolean;
  currentTime: number;
  trackPoolHeight: number; // Height in pixels

  // Actions
  setSelection: (type: SelectionType, id: string | null, data: Track | Transition | null) => void;
  clearSelection: () => void;
  setTimelineTracks: (trackIds: string[]) => void;
  moveTrackInTimeline: (fromIndex: number, toIndex: number) => void;
  addTrackToTimeline: (trackId: string, index?: number) => void;
  removeTrackFromTimeline: (trackId: string) => void;
  setIsInspectorOpen: (open: boolean) => void;
  setIsSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setIsPlaying: (playing: boolean) => void;
  setCurrentTime: (time: number) => void;
  setTrackPoolHeight: (height: number) => void;
  reset: () => void;
}

const initialState = {
  selection: { type: null as SelectionType, id: null, data: null },
  timelineTracks: [] as string[],
  isInspectorOpen: true,
  isSidebarCollapsed: false,
  isPlaying: false,
  currentTime: 0,
  trackPoolHeight: 280, // Default height in pixels
};

/**
 * Studio state management store
 * Manages the Mix Studio UI state including selections, timeline, and playback
 */
export const useStudioStore = create<StudioState>((set) => ({
  ...initialState,

  setSelection: (type, id, data) => {
    set({ selection: { type, id, data }, isInspectorOpen: true });
  },

  clearSelection: () => {
    set({ selection: { type: null, id: null, data: null } });
  },

  setTimelineTracks: (trackIds) => {
    set({ timelineTracks: trackIds });
  },

  moveTrackInTimeline: (fromIndex, toIndex) => {
    set((state) => {
      const newTracks = [...state.timelineTracks];
      const [removed] = newTracks.splice(fromIndex, 1);
      if (removed !== undefined) {
        newTracks.splice(toIndex, 0, removed);
      }
      return { timelineTracks: newTracks };
    });
  },

  addTrackToTimeline: (trackId, index) => {
    set((state) => {
      // Don't add if already in timeline
      if (state.timelineTracks.includes(trackId)) return state;

      const newTracks = [...state.timelineTracks];
      if (index !== undefined) {
        newTracks.splice(index, 0, trackId);
      } else {
        newTracks.push(trackId);
      }
      return { timelineTracks: newTracks };
    });
  },

  removeTrackFromTimeline: (trackId) => {
    set((state) => ({
      timelineTracks: state.timelineTracks.filter((id) => id !== trackId),
    }));
  },

  setIsInspectorOpen: (open) => {
    set({ isInspectorOpen: open });
  },

  setIsSidebarCollapsed: (collapsed) => {
    set({ isSidebarCollapsed: collapsed });
  },

  toggleSidebar: () => {
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed }));
  },

  setIsPlaying: (playing) => {
    set({ isPlaying: playing });
  },

  setCurrentTime: (time) => {
    set({ currentTime: time });
  },

  setTrackPoolHeight: (height) => {
    set({ trackPoolHeight: Math.max(150, Math.min(500, height)) });
  },

  reset: () => {
    set(initialState);
  },
}));
