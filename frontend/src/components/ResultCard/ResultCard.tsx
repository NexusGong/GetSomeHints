import React, { useState } from 'react';
import type { UnifiedPost } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import { getPublishDate } from '../../utils/sortUtils';
import { PixelCard } from '../PixelCard/PixelCard';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import './ResultCard.css';

interface ResultCardProps {
  post: UnifiedPost;
  onViewDetail?: (post: UnifiedPost) => void;
  isSelected?: boolean;
  onToggleSelect?: (postKey: string) => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  post,
  onViewDetail,
  isSelected = false,
  onToggleSelect,
}) => {
  const [expanded, setExpanded] = useState(false);
  const platformInfo = PLATFORMS.find((p) => p.value === post.platform);
  const postKey = `${post.platform}-${post.post_id}`;

  const formatTime = (timeStr: string) => {
    const date = getPublishDate(timeStr);
    if (!date) return timeStr || '—';
    try {
      return formatDistanceToNow(date, { addSuffix: true, locale: zhCN });
    } catch {
      return timeStr || '—';
    }
  };

  return (
    <PixelCard className={`result-card ${isSelected ? 'selected' : ''}`}>
      <div className="result-card-header">
        <div className="result-card-header-left">
          {onToggleSelect && (
            <input
              type="checkbox"
              className="result-card-checkbox"
              checked={isSelected}
              onChange={() => onToggleSelect(postKey)}
              onClick={(e) => e.stopPropagation()}
            />
          )}
          <div className="result-platform">
            <span className="platform-icon">{platformInfo?.icon}</span>
            <span className="platform-name">{platformInfo?.label}</span>
          </div>
        </div>
        <span className="result-time">{formatTime(post.publish_time)}</span>
      </div>

      <div className="result-title" onClick={() => setExpanded(!expanded)}>
        {post.title || post.content.substring(0, 50) + '...'}
      </div>

      {expanded && (
        <div className="result-content">
          <p>{post.content}</p>
        </div>
      )}

      <div className="result-author">
        <span className="author-label">作者:</span>
        <span className="author-name">{post.author.author_name}</span>
        <span className="author-id">(@{post.author.author_id})</span>
      </div>

      <div className="result-stats">
        <span>👍 {post.like_count}</span>
        <span>💬 {post.comment_count}</span>
        <span>📤 {post.share_count}</span>
        {post.collect_count !== undefined && (
          <span>⭐ {post.collect_count}</span>
        )}
      </div>

      <div className="result-actions">
        <button
          className="pixel-button-small"
          onClick={() => onViewDetail?.(post)}
        >
          查看详情
        </button>
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="pixel-button-small"
        >
          打开链接
        </a>
      </div>
    </PixelCard>
  );
};
