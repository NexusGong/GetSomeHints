import React, { useMemo, useState } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { exportToCSV, exportToJSON, copyToClipboard } from '../../utils/exportUtils';
import type { UnifiedPost } from '../../types';
import './BatchActions.css';

interface BatchActionsProps {
  posts: UnifiedPost[];
  /** 已选中的帖子 key 集合，支持 Set 或 string[]（如 `${platform}-${post_id}`） */
  selectedPosts: Set<string> | string[];
  onClearSelection: () => void;
}

/** 将 selectedPosts 规范为 Set，避免 persist 等导致传入数组时 .has 报错 */
function toSelectedSet(selectedPosts: Set<string> | string[] | undefined | null): Set<string> {
  if (selectedPosts instanceof Set) return selectedPosts;
  if (Array.isArray(selectedPosts)) return new Set(selectedPosts);
  return new Set();
}

export const BatchActions: React.FC<BatchActionsProps> = ({
  posts,
  selectedPosts,
  onClearSelection,
}) => {
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const selectedSet = useMemo(() => toSelectedSet(selectedPosts), [selectedPosts]);
  const selectedPostsList = useMemo(
    () => posts.filter((post) => selectedSet.has(`${post.platform}-${post.post_id}`)),
    [posts, selectedSet]
  );

  const handleExport = async (format: 'csv' | 'json' | 'clipboard') => {
    if (selectedPostsList.length === 0) {
      alert('请先选择要导出的数据');
      return;
    }

    setExporting(true);
    try {
      switch (format) {
        case 'csv':
          exportToCSV(selectedPostsList, 'selected_results');
          break;
        case 'json':
          exportToJSON(selectedPostsList, 'selected_results');
          break;
        case 'clipboard':
          const success = await copyToClipboard(selectedPostsList);
          if (success) {
            alert('已复制到剪贴板');
          } else {
            alert('复制失败，请重试');
          }
          break;
      }
      setIsExportModalOpen(false);
      onClearSelection();
    } catch (error) {
      console.error('导出失败:', error);
      alert('导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  if (selectedSet.size === 0) {
    return null;
  }

  return (
    <>
      <div className="batch-actions-bar">
        <div className="batch-actions-info">
          <span>已选择 <strong>{selectedSet.size}</strong> 条</span>
        </div>
        <div className="batch-actions-buttons">
          <button
            className="pixel-button-small"
            onClick={() => setIsExportModalOpen(true)}
            disabled={exporting}
          >
            📥 导出选中
          </button>
          <button
            className="pixel-button-small"
            onClick={onClearSelection}
          >
            ✖️ 取消选择
          </button>
        </div>
      </div>

      <PixelModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        title="导出选中的数据"
      >
        <div className="batch-export-menu">
          <p className="export-info">
            将导出 <strong>{selectedPostsList.length}</strong> 条选中的数据
          </p>

          <div className="export-options">
            <button
              className="pixel-button export-option"
              onClick={() => handleExport('csv')}
              disabled={exporting}
            >
              <span className="export-icon">📊</span>
              <span className="export-label">CSV 格式</span>
            </button>

            <button
              className="pixel-button export-option"
              onClick={() => handleExport('json')}
              disabled={exporting}
            >
              <span className="export-icon">📄</span>
              <span className="export-label">JSON 格式</span>
            </button>

            <button
              className="pixel-button export-option"
              onClick={() => handleExport('clipboard')}
              disabled={exporting}
            >
              <span className="export-icon">📋</span>
              <span className="export-label">复制到剪贴板</span>
            </button>
          </div>

          {exporting && (
            <div className="export-loading">
              <span>正在导出...</span>
            </div>
          )}
        </div>
      </PixelModal>
    </>
  );
};
