import React, { useState } from 'react';
import { PixelButton } from '../PixelButton/PixelButton';
import { PixelModal } from '../PixelModal/PixelModal';
import { exportToCSV, exportToJSON, exportToExcel, copyToClipboard } from '../../utils/exportUtils';
import type { UnifiedPost } from '../../types';
import './ExportMenu.css';

interface ExportMenuProps {
  posts: UnifiedPost[];
  totalCount?: number;
  filteredCount?: number;
  onExportComplete?: () => void;
}

export const ExportMenu: React.FC<ExportMenuProps> = ({
  posts,
  totalCount,
  filteredCount,
  onExportComplete,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: 'csv' | 'json' | 'excel' | 'clipboard') => {
    if (posts.length === 0) {
      alert('没有数据可导出');
      return;
    }

    setExporting(true);
    try {
      switch (format) {
        case 'csv':
          exportToCSV(posts, 'search_results');
          break;
        case 'json':
          exportToJSON(posts, 'search_results');
          break;
        case 'excel':
          exportToExcel(posts, 'search_results');
          break;
        case 'clipboard':
          const success = await copyToClipboard(posts);
          if (success) {
            alert('已复制到剪贴板');
          } else {
            alert('复制失败，请重试');
          }
          break;
      }
      setIsOpen(false);
      onExportComplete?.();
    } catch (error) {
      console.error('导出失败:', error);
      alert('导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <PixelButton
        onClick={() => setIsOpen(true)}
        variant="primary"
        disabled={posts.length === 0 || exporting}
      >
        {exporting ? '⏳ 导出中...' : `📥 导出数据 (${posts.length} 条)`}
      </PixelButton>

      <PixelModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="导出搜索结果"
      >
        <div className="export-menu">
          <p className="export-info">
            {filteredCount !== undefined && filteredCount !== posts.length ? (
              <>
                将导出 <strong>{posts.length}</strong> 条筛选后的结果
                {totalCount !== undefined && (
                  <span className="export-info-note">（共 {totalCount} 条）</span>
                )}
              </>
            ) : (
              <>
                当前有 <strong>{posts.length}</strong> 条搜索结果可导出
              </>
            )}
          </p>

          <div className="export-options">
            <button
              className="pixel-button export-option"
              onClick={() => handleExport('csv')}
              disabled={exporting || posts.length === 0}
            >
              <span className="export-icon">📊</span>
              <span className="export-label">CSV 格式</span>
              <span className="export-desc">可用 Excel 打开</span>
            </button>

            <button
              className="pixel-button export-option"
              onClick={() => handleExport('excel')}
              disabled={exporting || posts.length === 0}
            >
              <span className="export-icon">📈</span>
              <span className="export-label">Excel 格式</span>
              <span className="export-desc">CSV 格式，Excel 兼容</span>
            </button>

            <button
              className="pixel-button export-option"
              onClick={() => handleExport('json')}
              disabled={exporting || posts.length === 0}
            >
              <span className="export-icon">📄</span>
              <span className="export-label">JSON 格式</span>
              <span className="export-desc">结构化数据</span>
            </button>

            <button
              className="pixel-button export-option"
              onClick={() => handleExport('clipboard')}
              disabled={exporting || posts.length === 0}
            >
              <span className="export-icon">📋</span>
              <span className="export-label">复制到剪贴板</span>
              <span className="export-desc">文本格式</span>
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
