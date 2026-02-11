import React, { useMemo, useState } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { ResultList } from '../ResultList/ResultList';
import { ExportMenu } from '../ExportMenu/ExportMenu';
import { PixelButton } from '../PixelButton/PixelButton';
import { AnalysisModal } from '../AnalysisModal/AnalysisModal';
import { DetailModal } from '../DetailModal/DetailModal';
import { BatchActions } from '../BatchActions/BatchActions';
import type { HistoryRecord } from '../../stores/historyStore';
import type { UnifiedPost, UnifiedComment, Platform } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import { searchApi } from '../../services/api';
import { sortPosts, type ResultSortBy } from '../../utils/sortUtils';
import './HistoryDetailModal.css';

interface HistoryDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  record: HistoryRecord | null;
}

export const HistoryDetailModal: React.FC<HistoryDetailModalProps> = ({
  isOpen,
  onClose,
  record,
}) => {
  const [selectedPost, setSelectedPost] = useState<UnifiedPost | null>(null);
  const [selectedPostComments, setSelectedPostComments] = useState<UnifiedComment[]>([]);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [detailSortBy, setDetailSortBy] = useState<ResultSortBy>('time');

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
      const comments = await searchApi.getPostComments(
        post.platform,
        post.post_id,
        record?.taskId
      );
      setSelectedPostComments(comments);
    } catch {
      setSelectedPostComments([]);
    } finally {
      setIsLoadingComments(false);
    }
  };

  const handleToggleSelection = (postKey: string) => {
    setSelectedPosts((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(postKey)) {
        newSet.delete(postKey);
      } else {
        newSet.add(postKey);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (!record) return;
    if (selectedPosts.size === record.results.length) {
      setSelectedPosts(new Set());
    } else {
      setSelectedPosts(new Set(record.results.map((p) => `${p.platform}-${p.post_id}`)));
    }
  };

  const handleClearSelection = () => {
    setSelectedPosts(new Set());
  };

  const selectedPostsArray = record
    ? record.results.filter((p) => selectedPosts.has(`${p.platform}-${p.post_id}`))
    : [];

  const sortedResults = useMemo(
    () => (record ? sortPosts(record.results, detailSortBy) : []),
    [record, detailSortBy]
  );

  if (!record) return null;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <>
      <PixelModal
        isOpen={isOpen}
        onClose={onClose}
        title={`历史记录: ${record.keyword}`}
        size="large"
      >
        <div className="history-detail-content">
          <div className="history-detail-header">
            <div className="history-detail-info">
              <div className="history-detail-info-item">
                <span className="info-label">关键词:</span>
                <span className="info-value">{record.keyword}</span>
              </div>
              <div className="history-detail-info-item">
                <span className="info-label">创建时间:</span>
                <span className="info-value">{formatDate(record.createdAt)}</span>
              </div>
              {record.completedAt && (
                <div className="history-detail-info-item">
                  <span className="info-label">完成时间:</span>
                  <span className="info-value">{formatDate(record.completedAt)}</span>
                </div>
              )}
              <div className="history-detail-info-item">
                <span className="info-label">状态:</span>
                <span className={`info-value status-${record.status}`}>
                  {record.status === 'completed' ? '已完成' : 
                   record.status === 'stopped' ? '已停止' : '失败'}
                </span>
              </div>
              <div className="history-detail-info-item">
                <span className="info-label">平台:</span>
                <div className="info-platforms">
                  {record.platforms.map((platform) => {
                    const platformInfo = PLATFORMS.find((p) => p.value === platform);
                    const count = record.byPlatform[platform] || 0;
                    return (
                      <span key={platform} className="platform-tag">
                        {platformInfo?.icon} {platformInfo?.label} ({count})
                      </span>
                    );
                  })}
                </div>
              </div>
              <div className="history-detail-info-item">
                <span className="info-label">总计:</span>
                <span className="info-value">{record.totalFound} 条结果</span>
              </div>
            </div>
          </div>

          <div className="history-detail-results">
            <div className="history-detail-actions">
              <BatchActions
                posts={record.results}
                selectedPosts={selectedPosts}
                onClearSelection={handleClearSelection}
              />
              <div className="history-detail-sort">
                <label className="history-detail-sort-label">排序:</label>
                <select
                  className="pixel-select history-detail-sort-select"
                  value={detailSortBy}
                  onChange={(e) => setDetailSortBy(e.target.value as ResultSortBy)}
                >
                  <option value="time">最新</option>
                  <option value="hot">最热</option>
                  <option value="comments">最多评论</option>
                </select>
              </div>
            </div>

            {record.results.length > 0 ? (
              <>
                <ResultList
                  posts={sortedResults}
                  availablePlatforms={record.platforms}
                  onViewDetail={handleViewDetail}
                  embeddedTitle={`本页结果 (共 ${record.results.length} 条)`}
                  embeddedSelection={{
                    selectedPosts,
                    onToggle: handleToggleSelection,
                    onSelectAll: (keys) => setSelectedPosts(new Set(keys)),
                    onClear: handleClearSelection,
                  }}
                />
                <div className="history-detail-footer">
                  <ExportMenu
                    posts={selectedPostsArray.length > 0 ? selectedPostsArray : record.results}
                    totalCount={record.results.length}
                    filteredCount={selectedPostsArray.length > 0 ? selectedPostsArray.length : record.results.length}
                  />
                  <PixelButton
                    onClick={() => setIsAnalysisModalOpen(true)}
                    variant="primary"
                  >
                    📊 数据分析
                  </PixelButton>
                </div>
              </>
            ) : (
              <div className="history-detail-empty">
                <p>该次爬取没有结果</p>
              </div>
            )}
          </div>
        </div>
      </PixelModal>

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
        taskId={record?.taskId ?? null}
        posts={record?.results ?? []}
      />
    </>
  );
};
