import React, { useEffect, useState } from 'react';
import { SearchBox } from '../../components/SearchBox/SearchBox';
import { SearchOptionsModal } from '../../components/SearchOptionsModal/SearchOptionsModal';
import { PixelButton } from '../../components/PixelButton/PixelButton';
import { StatusIndicator } from '../../components/StatusIndicator/StatusIndicator';
import { LogStream } from '../../components/LogStream/LogStream';
import { ResultList } from '../../components/ResultList/ResultList';
import { DetailModal } from '../../components/DetailModal/DetailModal';
import { AnalysisModal } from '../../components/AnalysisModal/AnalysisModal';
import { LlmAnalysisModal } from '../../components/LlmAnalysisModal/LlmAnalysisModal';
import { NotificationModal } from '../../components/NotificationModal/NotificationModal';
import { ExportMenu } from '../../components/ExportMenu/ExportMenu';
import { BatchActions } from '../../components/BatchActions/BatchActions';
import { useSearchStore } from '../../stores/searchStore';
import { useResultStore } from '../../stores/resultStore';
import { useHistoryStore } from '../../stores/historyStore';
import { searchApi } from '../../services/api';
import type { UnifiedComment } from '../../types';
import type { Platform, UnifiedPost } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import './HomePage.css';

export const HomePage: React.FC = () => {
  const {
    keyword,
    selectedPlatforms,
    searchOptions,
    isSearching,
    status,
    taskId,
    stats,
    setKeyword,
    setSelectedPlatforms,
    setSearchOptions,
    startSearch,
    updateStatus,
    updateStats,
    reset: resetSearch,
  } = useSearchStore();

  const { setResults, clearResults, results, filteredResults, selectedPosts, clearSelection } = useResultStore();
  const { addRecord, records: historyRecords } = useHistoryStore();
  const [statusCheckInterval, setStatusCheckInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const [selectedPost, setSelectedPost] = useState<UnifiedPost | null>(null);
  const [selectedPostComments, setSelectedPostComments] = useState<UnifiedComment[]>([]);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isLoadingComments, setIsLoadingComments] = useState(false);

  // 处理查看详情：优先用帖子内嵌评论，没有再请求接口
  const handleViewDetail = async (post: UnifiedPost) => {
    setSelectedPost(post);
    setIsDetailModalOpen(true);
    const embedded = (post.platform_data?.comments ?? []) as UnifiedComment[];
    if (embedded.length > 0) {
      setSelectedPostComments(embedded);
      setIsLoadingComments(false);
      return;
    }
    setSelectedPostComments([]);
    setIsLoadingComments(true);
    try {
      const comments = await searchApi.getPostComments(post.platform, post.post_id, taskId || undefined);
      setSelectedPostComments(comments);
    } catch {
      setSelectedPostComments([]);
    } finally {
      setIsLoadingComments(false);
    }
  };
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [isLlmModalOpen, setIsLlmModalOpen] = useState(false);
  const [notification, setNotification] = useState<{
    isOpen: boolean;
    message: string;
    type?: 'info' | 'warning' | 'error' | 'success';
  }>({
    isOpen: false,
    message: '',
    type: 'info',
  });
  const [isSearchOptionsModalOpen, setIsSearchOptionsModalOpen] = useState(false);
  /** 每次新搜索或点击刷新时递增，用于清空实时日志 */
  const [logClearTrigger, setLogClearTrigger] = useState(0);

  useEffect(() => {
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, [statusCheckInterval]);

  const handleSearch = async () => {
    if (!keyword.trim()) {
      setNotification({
        isOpen: true,
        message: '请输入关键词',
        type: 'warning',
      });
      return;
    }

    if (selectedPlatforms.length === 0) {
      setNotification({
        isOpen: true,
        message: '请至少选择一个平台',
        type: 'warning',
      });
      return;
    }

    try {
      clearResults();
      setLogClearTrigger((k) => k + 1);
      // 不重置搜索设置，保留用户的选择
      // reset();  // 注释掉，保留搜索设置

      const response = await searchApi.startSearch({
        keywords: keyword,
        platforms: selectedPlatforms,
        max_count: searchOptions.maxCount,
        enable_comments: searchOptions.enableComments,
        enable_sub_comments: searchOptions.enableSubComments,
        time_range: searchOptions.timeRange,
        content_types: searchOptions.contentTypes || ['video', 'image_text', 'link'],
      });
      startSearch(response.task_id);
      updateStatus('searching', response.progress || 0);
      updateStats({
        totalFound: response.total_found,
        byPlatform: response.by_platform as Record<Platform, number>,
      });

      // 开始轮询状态和结果（更频繁地获取结果以实现实时显示）
      let lastResultCount = 0;
      const interval = setInterval(async () => {
        try {
          // 并行获取状态和结果
          const [statusResponse, resultsResponse] = await Promise.all([
            searchApi.getSearchStatus(response.task_id),
            searchApi.getSearchResults(response.task_id).catch(() => []), // 如果失败返回空数组
          ]);

          // 更新状态和进度
          // 将后端的 'running' 状态映射为前端的 'searching' 状态
          const frontendStatus = statusResponse.status === 'running' ? 'searching' : statusResponse.status as any;
          const progressValue = statusResponse.progress !== undefined 
            ? statusResponse.progress 
            : (statusResponse.status === 'completed' ? 100 : 0);
          updateStatus(frontendStatus, progressValue);
          updateStats({
            totalFound: statusResponse.total_found,
            byPlatform: statusResponse.by_platform as Record<Platform, number>,
          });

          // 实时更新结果（setResults 会自动去重和保留已有结果）
          if (resultsResponse && Array.isArray(resultsResponse)) {
            // 只在结果数量变化时更新，避免不必要的更新导致循环
            if (resultsResponse.length > 0 && resultsResponse.length !== lastResultCount) {
              setResults(resultsResponse);
              lastResultCount = resultsResponse.length;
            }
            // 注意：即使 resultsResponse.length === 0，也不清空已有结果
            // 因为可能是轮询时的临时状态
          }

          if (statusResponse.status === 'completed' || statusResponse.status === 'failed') {
            clearInterval(interval);
            const finalProgress = statusResponse.status === 'completed' ? 100 : progressValue;
            updateStatus(statusResponse.status as any, finalProgress);
            if (statusResponse.status === 'failed' && statusResponse.message) {
              setNotification({
                isOpen: true,
                message: statusResponse.message,
                type: 'error',
              });
            }
            // 最后一次获取完整结果
            try {
              const finalResults = await searchApi.getSearchResults(response.task_id);
              if (finalResults && Array.isArray(finalResults)) {
                setResults(finalResults);
                // 仅在有结果时保存到历史爬取
                if (statusResponse.total_found > 0) {
                  addRecord({
                    id: response.task_id,
                    taskId: response.task_id,
                    keyword: keyword,
                    platforms: selectedPlatforms,
                    createdAt: new Date().toISOString(),
                    completedAt: new Date().toISOString(),
                    status: statusResponse.status === 'completed' ? 'completed' : 'failed',
                    totalFound: statusResponse.total_found,
                    byPlatform: statusResponse.by_platform as Record<Platform, number>,
                    results: finalResults,
                    searchOptions: {
                      maxCount: searchOptions.maxCount,
                      enableComments: searchOptions.enableComments,
                      enableSubComments: searchOptions.enableSubComments,
                      timeRange: searchOptions.timeRange,
                      contentTypes: searchOptions.contentTypes,
                    },
                  });
                }
              }
            } catch (error) {
              console.warn('Failed to get final results:', error);
            }
          }
        } catch (error) {
          console.error('Failed to check status:', error);
        }
      }, 1000); // 缩短轮询间隔到1秒，实现更实时的更新

      setStatusCheckInterval(interval);
    } catch (error: unknown) {
      console.error('Failed to start search:', error);
      updateStatus('error');
      const err = error as { response?: { data?: { detail?: string | unknown[] }; status?: number }; message?: string };
      let msg = err?.message || '启动搜索失败，请检查后端是否运行（如 http://127.0.0.1:8000）';
      if (err?.response?.data?.detail) {
        const d = err.response.data.detail;
        msg = Array.isArray(d) ? d.map((x: any) => x?.msg || JSON.stringify(x)).join('; ') : String(d);
      }
      setNotification({
        isOpen: true,
        message: msg,
        type: 'error',
      });
    }
  };

  const handleStop = async () => {
    if (taskId) {
      try {
        // 停止搜索任务
        await searchApi.stopSearch(taskId);
        
        // 清除轮询间隔
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          setStatusCheckInterval(null);
        }
        
        // 获取已爬取的数据
        try {
          // 获取最终状态和统计信息
          const statusResponse = await searchApi.getSearchStatus(taskId);
          updateStatus('stopped', statusResponse.progress || 0);
          updateStats({
            totalFound: statusResponse.total_found,
            byPlatform: statusResponse.by_platform as Record<Platform, number>,
          });
          
          // 获取已爬取的结果（即使为空也要获取，确保显示最新数据）
          const stoppedResults = await searchApi.getSearchResults(taskId);
          if (stoppedResults && Array.isArray(stoppedResults)) {
            setResults(stoppedResults);
            // 仅在有结果时保存到历史爬取
            if (statusResponse.total_found > 0) {
              addRecord({
                id: taskId,
                taskId: taskId,
                keyword: keyword,
                platforms: selectedPlatforms,
                createdAt: new Date().toISOString(),
                completedAt: new Date().toISOString(),
                status: 'stopped',
                totalFound: statusResponse.total_found,
                byPlatform: statusResponse.by_platform as Record<Platform, number>,
                results: stoppedResults,
                searchOptions: {
                  maxCount: searchOptions.maxCount,
                  enableComments: searchOptions.enableComments,
                  enableSubComments: searchOptions.enableSubComments,
                  timeRange: searchOptions.timeRange,
                  contentTypes: searchOptions.contentTypes,
                },
              });
            }
          }
        } catch (error) {
          console.warn('Failed to get stopped results:', error);
          // 即使获取失败，也要更新状态为停止
          updateStatus('stopped', 0);
        }
      } catch (error) {
        console.error('Failed to stop search:', error);
        // 如果停止请求失败，仍然尝试更新状态
        updateStatus('stopped', 0);
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          setStatusCheckInterval(null);
        }
      }
    }
  };

  // 判断是否已经开始搜索（有任务ID或正在搜索）
  const hasStartedSearch = taskId !== null || isSearching || results.length > 0;

  // 格式化时间范围显示文本
  const getTimeRangeText = (timeRange: string) => {
    const timeRangeMap: Record<string, string> = {
      'all': '全部时间',
      '1day': '一天内',
      '1week': '一周内',
      '1month': '一个月内',
      '3months': '三个月内',
      '6months': '六个月内',
    };
    return timeRangeMap[timeRange] || '全部时间';
  };

  // 格式化平台显示文本
  const getPlatformsText = () => {
    if (selectedPlatforms.length === 0) return '';
    if (selectedPlatforms.length <= 2) {
      return selectedPlatforms.map(p => {
        const platformInfo = PLATFORMS.find(pl => pl.value === p);
        return platformInfo ? platformInfo.label : p;
      }).join('、');
    }
    return `${selectedPlatforms.length}个平台`;
  };

  // 格式化内容类型显示文本
  const getContentTypesText = () => {
    const contentTypes = searchOptions.contentTypes || [];
    if (contentTypes.length === 0) return '全部类型';
    if (contentTypes.length === 3) return '全部类型';
    
    const typeMap: Record<string, string> = {
      'video': '视频',
      'image_text': '图文',
      'link': '链接',
    };
    return contentTypes.map(t => typeMap[t] || t).join('、');
  };

  // 获取设置按钮显示文本
  const getSettingsButtonText = () => {
    if (selectedPlatforms.length === 0) {
      return '搜索设置';
    }
    const platformsText = getPlatformsText();
    const timeRangeText = getTimeRangeText(searchOptions.timeRange);
    const maxCountText = searchOptions.maxCount.toString();
    const contentTypesText = getContentTypesText();
    return `搜索设置｜平台：${platformsText} 时间范围：${timeRangeText} 内容类型：${contentTypesText} 最大数量：${maxCountText}`;
  };

  return (
    <div className="home-page">
      <div className="home-page-header">
        <div className="home-page-header-title-row">
          <img src="/logo.png" alt="GetSomeHints" className="home-page-logo" />
          <h1>GetSomeHints</h1>
        </div>
        <div className="home-page-header-text">
          <p className="home-page-subtitle">多平台搜索工具</p>
          <p className="home-page-notice">本工具仅供学习与研究使用，请遵守各平台使用条款及相关法律法规，勿用于商业或违规用途。</p>
        </div>
      </div>

      <div className="home-page-content">
        <div className="search-section">
          <div className="search-box-wrapper">
            <SearchBox
              value={keyword}
              onChange={setKeyword}
              onSearch={handleSearch}
              disabled={isSearching}
              placeholder="输入关键词搜索多平台内容..."
            />
          </div>
          <div className="search-controls-row">
            <div className="search-controls-left">
              <button
                className="search-control-btn search-settings-btn"
                onClick={() => setIsSearchOptionsModalOpen(true)}
                disabled={isSearching}
                type="button"
                title={getSettingsButtonText()}
              >
                <span className="platform-icon-small">⚙️</span>
                <span className="platform-label-small">{getSettingsButtonText()}</span>
              </button>
              {isSearching && (
                <button
                  className="search-control-btn stop-btn"
                  onClick={handleStop}
                  type="button"
                >
                  <span className="platform-icon-small">⏹️</span>
                  <span className="platform-label-small">停止</span>
                </button>
              )}
            </div>
            <div className="search-controls-right">
              <button
                className="search-submit-icon-btn search-refresh-btn"
                onClick={() => {
                  if (statusCheckInterval) {
                    clearInterval(statusCheckInterval);
                    setStatusCheckInterval(null);
                  }
                  resetSearch();
                  clearResults();
                  clearSelection();
                  setLogClearTrigger((k) => k + 1);
                }}
                disabled={isSearching}
                type="button"
                title="重置并开始新搜索"
              >
                <svg className="search-refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M21 12a9 9 0 1 0-2.2 5.8L21 21" />
                  <path d="M21 3v6h-6" />
                </svg>
              </button>
              <button
                className="search-submit-icon-btn"
                onClick={handleSearch}
                disabled={isSearching || !keyword.trim() || selectedPlatforms.length === 0}
                title="搜索"
              >
                {isSearching ? '⏳' : '↑'}
              </button>
            </div>
          </div>
        </div>

        {/* 有搜索状态或历史记录时显示：状态、日志、结果、数据分析入口 */}
        {(hasStartedSearch || historyRecords.length > 0) && (
          <>
            <div className="status-section">
              <StatusIndicator 
                status={status} 
                message={
                  status === 'stopped' 
                    ? (stats.totalFound > 0 ? `已停止，已找到 ${stats.totalFound} 条` : '已停止')
                    : (stats.totalFound > 0 ? `已找到 ${stats.totalFound} 条` : '等待搜索')
                } 
              />
              {stats.totalFound > 0 && (
                <div className="stats-info">
                  {Object.entries(stats.byPlatform).map(([platform, count]) => {
                    const platformInfo = PLATFORMS.find(p => p.value === platform);
                    return (
                      <span key={platform} className="stat-item">
                        {platformInfo?.icon} {platformInfo?.label}: {count}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {hasStartedSearch && <LogStream clearTrigger={logClearTrigger} />}

            {/* 只在有结果时才显示结果列表 */}
            {results.length > 0 && (
              <>
                <div className="results-section">
                  <BatchActions
                    posts={results}
                    selectedPosts={selectedPosts}
                    onClearSelection={clearSelection}
                  />
                  <ResultList
                    posts={results}
                    availablePlatforms={selectedPlatforms}
                    onViewDetail={handleViewDetail}
                  />
                </div>

                <div className="result-actions-bar">
                  <ExportMenu 
                    posts={filteredResults.length > 0 ? filteredResults : results} 
                    totalCount={results.length}
                    filteredCount={filteredResults.length}
                  />
                  <PixelButton
                    onClick={() => setIsAnalysisModalOpen(true)}
                    variant="primary"
                  >
                    📊 数据分析
                  </PixelButton>
                  <PixelButton
                    onClick={() => setIsLlmModalOpen(true)}
                    variant="primary"
                  >
                    🤖 大模型分析
                  </PixelButton>
                </div>
              </>
            )}

            {/* 无本次结果但有历史且用户已实际搜索过时，显示数据分析入口（弹窗内可选历史记录） */}
            {results.length === 0 && historyRecords.length > 0 && hasStartedSearch && (
              <div className="result-actions-bar">
                <PixelButton
                  onClick={() => setIsAnalysisModalOpen(true)}
                  variant="primary"
                >
                  📊 数据分析（基于当前结果或历史记录）
                </PixelButton>
                <PixelButton
                  onClick={() => setIsLlmModalOpen(true)}
                  variant="primary"
                >
                  🤖 大模型分析
                </PixelButton>
              </div>
            )}
          </>
        )}
      </div>

      <DetailModal
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedPostComments([]);
        }}
        post={selectedPost}
        comments={selectedPostComments}
        isLoadingComments={isLoadingComments}
      />

      <AnalysisModal
        isOpen={isAnalysisModalOpen}
        onClose={() => setIsAnalysisModalOpen(false)}
        taskId={taskId}
        posts={results}
        historyRecords={historyRecords}
      />

      <LlmAnalysisModal
        isOpen={isLlmModalOpen}
        onClose={() => setIsLlmModalOpen(false)}
        initialPosts={results}
        initialTaskId={taskId}
      />

      <NotificationModal
        isOpen={notification.isOpen}
        onClose={() => setNotification({ ...notification, isOpen: false })}
        message={notification.message}
        type={notification.type}
      />

      <SearchOptionsModal
        isOpen={isSearchOptionsModalOpen}
        onClose={() => setIsSearchOptionsModalOpen(false)}
        config={searchOptions}
        onChange={setSearchOptions}
        selectedPlatforms={selectedPlatforms}
        onPlatformsChange={setSelectedPlatforms}
        disabled={isSearching}
      />
    </div>
  );
};
