import { create } from 'zustand';

import { projectsService, type Project } from '@/services/projects.service';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  isLoadingList: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (name: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  updateCurrentProject: (project: Partial<Project>) => void;
}

/**
 * Project management store using Zustand
 */
export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  isLoadingList: false,
  error: null,

  fetchProjects: async () => {
    // Prevent concurrent fetches
    if (get().isLoadingList) return;

    set({ isLoadingList: true, error: null });
    try {
      const projects = await projectsService.getAll();
      set({ projects, isLoadingList: false });
    } catch (error) {
      set({ error: 'Failed to fetch projects', isLoadingList: false });
    }
  },

  fetchProject: async (id: string) => {
    // Prevent concurrent fetches for the same project
    const state = get();
    if (state.isLoading && state.currentProject?.id === id) return;

    set({ isLoading: true, error: null });
    try {
      const project = await projectsService.getById(id);
      set({ currentProject: project, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch project', isLoading: false });
    }
  },

  createProject: async (name: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsService.create(name);
      set((state) => ({
        projects: [project, ...state.projects],
        isLoading: false,
      }));
      return project;
    } catch (error) {
      set({ error: 'Failed to create project', isLoading: false });
      throw error;
    }
  },

  deleteProject: async (id: string) => {
    try {
      await projectsService.delete(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
      }));
    } catch (error) {
      set({ error: 'Failed to delete project' });
      throw error;
    }
  },

  updateCurrentProject: (updates: Partial<Project>) => {
    set((state) => ({
      currentProject: state.currentProject
        ? { ...state.currentProject, ...updates }
        : null,
    }));
  },
}));
