import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { UnifiedPost, Platform } from '../types';
import { getPublishTimeMs } from '../utils/sortUtils';

interface ResultState {
  results: UnifiedPost[];
  filteredResults: UnifiedPost[];
  filters: {
    platforms: Platform[];
    keyword: string;
  };
  sortBy: 'time' | 'hot' | 'comments';
  selectedPosts: Set<string>; // 存储选中的 post key (platform-post_id)
  setResults: (results: UnifiedPost[]) => void;
  addResult: (result: UnifiedPost) => void;
  setPlatformFilter: (platforms: Platform[]) => void;
  setKeywordFilter: (keyword: string) => void;
  setSortBy: (sortBy: ResultState['sortBy']) => void;
  clearResults: () => void;
  applyFilters: () => void;
  togglePostSelection: (postKey: string) => void;
  selectAllPosts: (postKeys: string[]) => void;
  clearSelection: () => void;
}

// 存储接口，用于处理 Set 类型的序列化
interface StoredState {
  results: UnifiedPost[];
  filters: {
    platforms: Platform[];
    keyword: string;
  };
  sortBy: 'time' | 'hot' | 'comments';
  selectedPosts: string[]; // 存储为数组，恢复时转换为 Set
}

export const useResultStore = create<ResultState>()(
  persist(
    (set, get) => ({
      results: [],
      filteredResults: [],
      filters: {
        platforms: [],
        keyword: '',
      },
      sortBy: 'time',
      selectedPosts: new Set<string>(),
      setResults: (results) => {
        // 去重：根据 platform 和 post_id 去重
        // 保留已有结果，只添加新的或更新已存在的
        if (!results || !Array.isArray(results)) {
          return; // 无效数据，不更新
        }
        
        const existingResults = get().results;
        const resultMap = new Map<string, UnifiedPost>();
        
        // 先添加现有结果（保留已有数据）
        existingResults.forEach(result => {
          const key = `${result.platform}-${result.post_id}`;
          resultMap.set(key, result);
        });
        
        // 添加新结果（如果有重复则更新为新数据）
        results.forEach(result => {
          const key = `${result.platform}-${result.post_id}`;
          // 更新为新数据（如果有的话）
          resultMap.set(key, result);
        });
        
        const uniqueResults = Array.from(resultMap.values());
        
        // 检查是否有实际变化，避免不必要的更新
        const currentResults = get().results;
        if (currentResults.length === uniqueResults.length) {
          // 长度相同，检查内容是否相同
          const currentKeys = new Set(currentResults.map(r => `${r.platform}-${r.post_id}`));
          const newKeys = new Set(uniqueResults.map(r => `${r.platform}-${r.post_id}`));
          if (currentKeys.size === newKeys.size && 
              Array.from(currentKeys).every(k => newKeys.has(k))) {
            // 内容相同，不更新
            return;
          }
        }
        
        // 有变化，更新结果
        set({ results: uniqueResults });
        get().applyFilters();
      },
      addResult: (result) => {
        const results = [...get().results, result];
        set({ results });
        get().applyFilters();
      },
      setPlatformFilter: (platforms) => {
        set((state) => ({
          filters: { ...state.filters, platforms },
        }));
        get().applyFilters();
      },
      setKeywordFilter: (keyword) => {
        set((state) => ({
          filters: { ...state.filters, keyword },
        }));
        get().applyFilters();
      },
      setSortBy: (sortBy) => {
        set({ sortBy });
        // 确保立即应用排序
        get().applyFilters();
      },
      applyFilters: () => {
        const { results, filters, sortBy } = get();
        let filtered = [...results];

        // 平台筛选：只有在设置了平台筛选时才过滤
        if (filters.platforms.length > 0) {
          filtered = filtered.filter((r) => filters.platforms.includes(r.platform));
        }
        // 如果没有设置平台筛选，显示所有平台的结果

        // 关键词筛选：只有在输入了关键词时才过滤
        if (filters.keyword && filters.keyword.trim()) {
          const keyword = filters.keyword.toLowerCase().trim();
          filtered = filtered.filter(
            (r) =>
              r.title.toLowerCase().includes(keyword) ||
              r.content.toLowerCase().includes(keyword) ||
              r.author.author_name.toLowerCase().includes(keyword)
          );
        }
        // 如果没有输入关键词，显示所有结果

        // 排序：时间 = 最新在最上（b 时间大则 b 排前），热度/评论 = 多的在前；时间相同时按 post_id 稳定顺序
        filtered.sort((a, b) => {
          switch (sortBy) {
            case 'time': {
              const msA = getPublishTimeMs(a.publish_time);
              const msB = getPublishTimeMs(b.publish_time);
              const diff = msB - msA;
              if (diff !== 0 && Number.isFinite(diff)) return diff;
              // 时间相同或无效时按 post_id 稳定排序
              return String(a.platform + a.post_id).localeCompare(String(b.platform + b.post_id));
            }
            case 'hot':
              // 按点赞数排序（最多的在前）
              return (b.like_count || 0) - (a.like_count || 0);
            case 'comments':
              // 按评论数排序（最多的在前）
              return (b.comment_count || 0) - (a.comment_count || 0);
            default:
              return 0;
          }
        });

        set({ filteredResults: filtered });
      },
      clearResults: () => {
        set({
          results: [],
          filteredResults: [],
          filters: {
            platforms: [],
            keyword: '',
          },
          selectedPosts: new Set<string>(),
        });
      },
      togglePostSelection: (postKey: string) => {
        const { selectedPosts } = get();
        const newSelection = new Set(selectedPosts);
        if (newSelection.has(postKey)) {
          newSelection.delete(postKey);
        } else {
          newSelection.add(postKey);
        }
        set({ selectedPosts: newSelection });
      },
      selectAllPosts: (postKeys: string[]) => {
        set({ selectedPosts: new Set(postKeys) });
      },
      clearSelection: () => {
        set({ selectedPosts: new Set<string>() });
      },
    }),
    {
      name: 'getsomehints-results',
      storage: createJSONStorage(() => localStorage),
      // 只持久化需要的数据，不持久化 filteredResults（每次重新计算）
      partialize: (state): StoredState => ({
        results: state.results,
        filters: state.filters,
        sortBy: state.sortBy,
        selectedPosts: Array.from(state.selectedPosts), // Set 转为数组存储
      }),
      // 恢复时转换数组为 Set，并重新应用筛选
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error('Failed to rehydrate result store:', error);
          return;
        }
        if (state) {
          // 将 selectedPosts 从数组恢复为 Set
          // persist 中间件会将 partialize 返回的数据合并到 state
          // 但 selectedPosts 需要手动转换
          const stored = state as any;
          if (stored.selectedPosts) {
            if (Array.isArray(stored.selectedPosts)) {
              state.selectedPosts = new Set(stored.selectedPosts);
            } else if (!(stored.selectedPosts instanceof Set)) {
              state.selectedPosts = new Set<string>();
            }
          }
          // 恢复后重新应用筛选
          setTimeout(() => {
            state.applyFilters();
          }, 0);
        }
      },
    }
  )
);
