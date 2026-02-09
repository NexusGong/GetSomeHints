import React from 'react';
import { PixelCard } from '../PixelCard/PixelCard';
import type { HistoryRecord } from '../../stores/historyStore';
import { PLATFORMS } from '../../utils/constants';
import './HistoryCard.css';

interface HistoryCardProps {
  record: HistoryRecord;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onClick: () => void;
  onDelete?: (id: string) => void;
}

export const HistoryCard: React.FC<HistoryCardProps> = ({
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

  const getStatusLabel = () => {
    switch (record.status) {
      case 'completed':
        return '已完成';
      case 'stopped':
        return '已停止';
      case 'failed':
        return '失败';
      default:
        return '未知';
    }
  };

  const getStatusClass = () => {
    switch (record.status) {
      case 'completed':
        return 'status-completed';
      case 'stopped':
        return 'status-stopped';
      case 'failed':
        return 'status-failed';
      default:
        return '';
    }
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // 如果点击的是选择框或删除按钮，不触发卡片点击
    if (
      (e.target as HTMLElement).closest('.history-card-select') ||
      (e.target as HTMLElement).closest('.history-card-delete')
    ) {
      return;
    }
    onClick();
  };

  const handleSelect = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSelect) {
      onSelect(record.id);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete && window.confirm('确定要删除这条历史记录吗？')) {
      onDelete(record.id);
    }
  };

  return (
    <PixelCard
      className={`history-card ${isSelected ? 'selected' : ''}`}
      onClick={handleCardClick}
    >
      <div className="history-card-header">
        <div className="history-card-main">
          {onSelect && (
            <input
              type="checkbox"
              className="history-card-select"
              checked={isSelected}
              onChange={handleSelect}
              onClick={handleSelect}
            />
          )}
          <div className="history-card-content">
            <div className="history-card-title">
              <span className="history-card-keyword">{record.keyword}</span>
              <span className={`history-card-status ${getStatusClass()}`}>
                {getStatusLabel()}
              </span>
            </div>
            <div className="history-card-meta">
              <span className="history-card-time">
                {formatDate(record.createdAt)}
              </span>
              <span className="history-card-count">
                共 {record.totalFound} 条结果
              </span>
            </div>
          </div>
        </div>
        {onDelete && (
          <button
            className="history-card-delete"
            onClick={handleDelete}
            aria-label="删除"
          >
            🗑️
          </button>
        )}
      </div>
      
      <div className="history-card-platforms">
        {record.platforms.map((platform) => {
          const platformInfo = PLATFORMS.find((p) => p.value === platform);
          const count = record.byPlatform[platform] || 0;
          return (
            <span key={platform} className="history-card-platform">
              {platformInfo?.icon} {platformInfo?.label} ({count})
            </span>
          );
        })}
      </div>
    </PixelCard>
  );
};
