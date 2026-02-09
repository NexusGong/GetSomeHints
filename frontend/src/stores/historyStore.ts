import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { UnifiedPost, Platform } from '../types';

export interface HistoryRecord {
  id: string;
  taskId: string;
  keyword: string;
  platforms: Platform[];
  createdAt: string;
  completedAt?: string;
  status: 'completed' | 'stopped' | 'failed';
  totalFound: number;
  byPlatform: Record<Platform, number>;
  results: UnifiedPost[];
  searchOptions?: {
    maxCount?: number;
    enableComments?: boolean;
    enableSubComments?: boolean;
    timeRange?: string;
    contentTypes?: string[];
  };
}

interface HistoryState {
  records: HistoryRecord[];
  addRecord: (record: HistoryRecord) => void;
  deleteRecord: (id: string) => void;
  deleteRecords: (ids: string[]) => void;
  getRecord: (id: string) => HistoryRecord | undefined;
  clearAll: () => void;
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      records: [],
      addRecord: (record) => {
        set((state) => ({
          records: [record, ...state.records], // 最新的在前面
        }));
      },
      deleteRecord: (id) => {
        set((state) => ({
          records: state.records.filter((r) => r.id !== id),
        }));
      },
      deleteRecords: (ids) => {
        set((state) => ({
          records: state.records.filter((r) => !ids.includes(r.id)),
        }));
      },
      getRecord: (id) => {
        return get().records.find((r) => r.id === id);
      },
      /** 清空全部历史；会同步持久化到 localStorage，即删除保存的相关内容 */
      clearAll: () => {
        set({ records: [] });
      },
    }),
    {
      name: 'getsomehints-history',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
