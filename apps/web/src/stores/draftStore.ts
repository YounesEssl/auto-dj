import { create } from 'zustand';

import { draftsService, type Draft } from '@/services/drafts.service';

interface DraftState {
  drafts: Draft[];
  currentDraft: Draft | null;
  isLoading: boolean;
  error: string | null;
  fetchDrafts: () => Promise<void>;
  fetchDraft: (id: string) => Promise<void>;
  createDraft: (name?: string) => Promise<Draft>;
  deleteDraft: (id: string) => Promise<void>;
  updateCurrentDraft: (draft: Partial<Draft>) => void;
  setCurrentDraft: (draft: Draft | null) => void;
}

/**
 * Draft management store using Zustand
 */
export const useDraftStore = create<DraftState>((set) => ({
  drafts: [],
  currentDraft: null,
  isLoading: false,
  error: null,

  fetchDrafts: async () => {
    set({ isLoading: true, error: null });
    try {
      const drafts = await draftsService.getAll();
      set({ drafts, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch drafts', isLoading: false });
    }
  },

  fetchDraft: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const draft = await draftsService.getById(id);
      set({ currentDraft: draft, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch draft', isLoading: false });
    }
  },

  createDraft: async (name?: string) => {
    set({ isLoading: true, error: null });
    try {
      const draft = await draftsService.create(name);
      set((state) => ({
        drafts: [draft, ...state.drafts],
        isLoading: false,
      }));
      return draft;
    } catch (error) {
      set({ error: 'Failed to create draft', isLoading: false });
      throw error;
    }
  },

  deleteDraft: async (id: string) => {
    try {
      await draftsService.delete(id);
      set((state) => ({
        drafts: state.drafts.filter((d) => d.id !== id),
        currentDraft: state.currentDraft?.id === id ? null : state.currentDraft,
      }));
    } catch (error) {
      set({ error: 'Failed to delete draft' });
      throw error;
    }
  },

  updateCurrentDraft: (updates: Partial<Draft>) => {
    set((state) => ({
      currentDraft: state.currentDraft
        ? { ...state.currentDraft, ...updates }
        : null,
    }));
  },

  setCurrentDraft: (draft: Draft | null) => {
    set({ currentDraft: draft });
  },
}));
