import React from 'react';
import { PixelCard } from '../PixelCard/PixelCard';
import type { LlmAnalysisRecord } from '../../stores/llmAnalysisStore';
import './LlmAnalysisCard.css';

interface LlmAnalysisCardProps {
  record: LlmAnalysisRecord;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

export const LlmAnalysisCard: React.FC<LlmAnalysisCardProps> = ({
  record,
  isSelected = false,
  onSelect,
  onClick,
  onDelete,
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      const hours = Math.floor(diff / (1000 * 60 * 60));
      if (hours === 0) {
        const minutes = Math.floor(diff / (1000 * 60));
        return minutes <= 0 ? '刚刚' : `${minutes}分钟前`;
      }
      return `${hours}小时前`;
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    }
  };

  const handleCardClick = (e?: React.MouseEvent) => {
    if (e?.target && (
      (e.target as HTMLElement).closest('.llm-analysis-card-select') ||
      (e.target as HTMLElement).closest('.llm-analysis-card-delete')
    )) {
      return;
    }
    onClick();
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete && window.confirm('确定要删除这条分析记录吗？')) {
      onDelete(record.id);
    }
  };

  return (
    <PixelCard
      className={`llm-analysis-card ${isSelected ? 'selected' : ''}`}
      onClick={handleCardClick}
    >
      <div className="llm-analysis-card-header">
        <div className="llm-analysis-card-main">
          {onSelect && (
            <input
              type="checkbox"
              className="llm-analysis-card-select"
              checked={isSelected}
              onChange={(e) => {
                e.stopPropagation();
                onSelect(record.id);
              }}
              onClick={(e) => e.stopPropagation()}
            />
          )}
          <div className="llm-analysis-card-content">
            <div className="llm-analysis-card-title">
              <span className="llm-analysis-card-name">{record.name}</span>
              <span className="llm-analysis-card-model">{record.model}</span>
            </div>
            <div className="llm-analysis-card-meta">
              <span className="llm-analysis-card-time">{formatDate(record.createdAt)}</span>
              <span className="llm-analysis-card-count">共 {record.postsCount} 条数据</span>
              {record.sceneName && <span className="llm-analysis-card-scene">{record.sceneName}</span>}
            </div>
          </div>
        </div>
        {onDelete && (
          <button
            className="llm-analysis-card-delete"
            onClick={handleDelete}
            aria-label="删除"
          >
            🗑️
          </button>
        )}
      </div>
    </PixelCard>
  );
};
