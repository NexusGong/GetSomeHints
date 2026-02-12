import { create } from 'zustand';
import type { Platform } from '../types';
import type { SearchOptionsConfig, ContentType } from '../components/SearchOptions/SearchOptions';

interface SearchState {
  keyword: string;
  selectedPlatforms: Platform[];
  searchOptions: SearchOptionsConfig;
  isSearching: boolean;
  status: 'idle' | 'searching' | 'running' | 'completed' | 'stopped' | 'error';
  progress: number;
  taskId: string | null;
  stats: {
    totalFound: number;
    byPlatform: Record<Platform, number>;
  };
  setKeyword: (keyword: string) => void;
  setSelectedPlatforms: (platforms: Platform[]) => void;
  setSearchOptions: (options: SearchOptionsConfig) => void;
  startSearch: (taskId: string) => void;
  stopSearch: () => void;
  updateStatus: (status: SearchState['status'], progress?: number) => void;
  updateStats: (stats: SearchState['stats']) => void;
  reset: () => void;
}

const initialState = {
  keyword: '',
  selectedPlatforms: [],
  searchOptions: {
    maxCount: 50,
    enableComments: true,
    enableSubComments: false,
    timeRange: 'all' as const,
    contentTypes: ['video', 'image_text', 'link'] as ContentType[],
  },
  isSearching: false,
  status: 'idle' as const,
  progress: 0,
  taskId: null,
  stats: {
    totalFound: 0,
    byPlatform: {} as Record<Platform, number>,
  },
};

export const useSearchStore = create<SearchState>((set) => ({
  ...initialState,
  setKeyword: (keyword) => set({ keyword }),
  setSelectedPlatforms: (platforms) => set({ selectedPlatforms: platforms }),
  setSearchOptions: (searchOptions) => set({ searchOptions }),
  startSearch: (taskId) =>
    set({
      isSearching: true,
      status: 'searching',
      progress: 0,
      taskId,
      stats: initialState.stats,
    }),
  stopSearch: () =>
    set({
      isSearching: false,
      status: 'stopped',
    }),
  updateStatus: (status, progress) =>
    set((state) => ({
      status,
      progress: progress !== undefined ? progress : state.progress,
      isSearching: status === 'searching' || status === 'running',
    })),
  updateStats: (stats) => set({ stats }),
  reset: () => set(initialState),
}));
