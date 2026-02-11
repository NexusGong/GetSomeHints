import React, { useEffect, useMemo } from 'react';
import type { UnifiedPost, Platform } from '../../types';
import { ResultCard } from '../ResultCard/ResultCard';
import { PixelInput } from '../PixelInput/PixelInput';
import { PLATFORMS } from '../../utils/constants';
import { useResultStore } from '../../stores/resultStore';

// 扩展 store 类型以包含 applyFilters 方法
declare module '../../stores/resultStore' {
  interface ResultState {
    applyFilters: () => void;
  }
}
import './ResultList.css';

/** 嵌入模式：用于历史详情等场景，直接显示传入的 posts 并使用本地选中状态，不依赖 store */
export interface EmbeddedSelection {
  selectedPosts: Set<string>;
  onToggle: (postKey: string) => void;
  onSelectAll: (postKeys: string[]) => void;
  onClear: () => void;
}

interface ResultListProps {
  posts: UnifiedPost[];
  onViewDetail?: (post: UnifiedPost) => void;
  availablePlatforms?: Platform[];
  /** 嵌入模式：显示 props.posts 并使用本地选中状态（如历史详情弹窗） */
  embeddedSelection?: EmbeddedSelection;
  /** 嵌入模式下的标题，如 "本页结果" */
  embeddedTitle?: string;
}

export const ResultList: React.FC<ResultListProps> = ({
  posts,
  onViewDetail,
  availablePlatforms,
  embeddedSelection,
  embeddedTitle,
}) => {
  const isEmbedded = Boolean(embeddedSelection);
  const store = useResultStore();
  const {
    filteredResults,
    filters,
    sortBy,
    selectedPosts: storeSelectedPosts,
    setKeywordFilter,
    setPlatformFilter,
    setSortBy,
    togglePostSelection,
    selectAllPosts,
    clearSelection,
  } = store;

  // 嵌入模式下不同步 store 的筛选，也不使用 store 的列表
  useEffect(() => {
    if (isEmbedded || !availablePlatforms || availablePlatforms.length === 0) return;
    const currentFilterSet = new Set(filters.platforms);
    const availableSet = new Set(availablePlatforms);
    const isDifferent =
      filters.platforms.length !== availablePlatforms.length ||
      filters.platforms.some((p) => !availableSet.has(p)) ||
      availablePlatforms.some((p) => !currentFilterSet.has(p));
    if (isDifferent) setPlatformFilter(availablePlatforms);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEmbedded, availablePlatforms?.join(',')]);

  // 确保排序/筛选在展示列表时已应用（解决 persist 恢复后或仅改排序时列表未刷新的问题）
  useEffect(() => {
    if (isEmbedded) return;
    const state = useResultStore.getState();
    if (state.results.length > 0) state.applyFilters();
  }, [isEmbedded, sortBy, store.results.length]);

  const displayPosts = useMemo(() => {
    if (isEmbedded) return posts;
    return filteredResults;
  }, [isEmbedded, posts, filteredResults]);

  const selectedPosts = isEmbedded && embeddedSelection ? embeddedSelection.selectedPosts : storeSelectedPosts;
  const handleToggle = isEmbedded && embeddedSelection ? embeddedSelection.onToggle : togglePostSelection;
  const handleSelectAll = isEmbedded && embeddedSelection
    ? () => {
        const allKeys = displayPosts.map((p) => `${p.platform}-${p.post_id}`);
        if (embeddedSelection.selectedPosts.size === displayPosts.length) {
          embeddedSelection.onClear();
        } else {
          embeddedSelection.onSelectAll(allKeys);
        }
      }
    : () => {
        const allKeys = displayPosts.map((p) => `${p.platform}-${p.post_id}`);
        if (storeSelectedPosts.size === allKeys.length) clearSelection();
        else selectAllPosts(allKeys);
      };
  const showSelectAll = isEmbedded
    ? embeddedSelection!.selectedPosts.size > 0 || displayPosts.length > 0
    : displayPosts.length > 0;
  const selectAllLabel =
    isEmbedded && embeddedSelection
      ? (embeddedSelection.selectedPosts.size === displayPosts.length ? '☑️ 取消全选' : '☐ 全选')
      : (storeSelectedPosts.size === displayPosts.length ? '☑️ 取消全选' : '☐ 全选');
  const listTitle = embeddedTitle ?? `搜索结果 (共 ${displayPosts.length} 条)`;

  return (
    <div className="result-list">
      <div className="result-list-header">
        <div className="result-list-header-left">
          <h2>{listTitle}</h2>
          {showSelectAll && (
            <div className="result-list-batch-controls">
              <button
                className="pixel-button-small"
                onClick={handleSelectAll}
                title="全选/取消全选"
              >
                {selectAllLabel}
              </button>
            </div>
          )}
        </div>
        {!isEmbedded && displayPosts.length > 0 && availablePlatforms && availablePlatforms.length > 0 && (
          <div className="result-list-actions">
            <button
              className="pixel-button-small"
              onClick={() => {
                // 切换筛选显示：在用户选择的平台和所有平台之间切换
                const currentFilterSet = new Set(filters.platforms);
                const isShowingSelected = 
                  filters.platforms.length === availablePlatforms.length &&
                  availablePlatforms.every(p => currentFilterSet.has(p));
                
                if (isShowingSelected) {
                  // 如果当前显示的是用户选择的平台，则显示所有平台
                  const allPlatforms = [...new Set(displayPosts.map(p => p.platform))] as Platform[];
                  setPlatformFilter(allPlatforms);
                } else {
                  // 否则恢复为用户选择的平台
                  setPlatformFilter(availablePlatforms);
                }
              }}
              title={filters.platforms.length === availablePlatforms.length && 
                     availablePlatforms.every(p => filters.platforms.includes(p))
                     ? '显示所有平台' 
                     : '恢复为搜索时选择的平台'}
            >
              {filters.platforms.length === availablePlatforms.length && 
               availablePlatforms.every(p => filters.platforms.includes(p))
               ? '👁️ 显示全部' 
               : '🔍 恢复筛选'}
            </button>
          </div>
        )}
      </div>

      {!isEmbedded && (
      <div className="result-list-filters">
        <div className="filter-group">
          <label>筛选平台:</label>
          <div className="platform-filter-info">
            {filters.platforms.length > 0 ? (
              <div className="platform-filter-selected">
                {filters.platforms.map(platformValue => {
                  const platformInfo = PLATFORMS.find(p => p.value === platformValue);
                  return platformInfo ? (
                    <span key={platformValue} className="platform-filter-badge">
                      {platformInfo.icon} {platformInfo.label}
                    </span>
                  ) : null;
                }).filter(Boolean)}
              </div>
            ) : (
              <div className="platform-filter-empty">
                <span className="platform-filter-hint">未设置筛选平台，显示所有平台</span>
              </div>
            )}
          </div>
        </div>

        <div className="filter-group">
          <label>搜索关键词:</label>
          <PixelInput
            value={filters.keyword}
            onChange={setKeywordFilter}
            placeholder="在结果中搜索..."
            className="filter-input"
          />
        </div>

        <div className="filter-group">
          <label>排序:</label>
          <select
            className="pixel-select"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as 'time' | 'hot' | 'comments');
            }}
          >
            <option value="time">最新</option>
            <option value="hot">最热</option>
            <option value="comments">最多评论</option>
          </select>
        </div>
      </div>
      )}

      <div className="result-list-content">
        {displayPosts.length === 0 ? (
          <div className="result-empty">
            {isEmbedded
              ? '📭 该次爬取暂无结果'
              : (() => {
                  const { results } = useResultStore.getState();
                  if (results.length === 0) return '📭 暂无搜索结果，请等待搜索完成...';
                  if (filters.platforms.length > 0 || (filters.keyword && filters.keyword.trim())) {
                    return '📭 没有找到匹配的结果，请尝试调整筛选条件';
                  }
                  return '📭 暂无搜索结果，请等待搜索完成...';
                })()}
          </div>
        ) : (
          displayPosts.map((post, index) => {
            const uniqueKey = `${post.platform}-${post.post_id}-${index}`;
            const postKey = `${post.platform}-${post.post_id}`;
            return (
              <ResultCard
                key={uniqueKey}
                post={post}
                onViewDetail={onViewDetail}
                isSelected={selectedPosts.has(postKey)}
                onToggleSelect={handleToggle}
              />
            );
          })
        )}
      </div>
    </div>
  );
};
