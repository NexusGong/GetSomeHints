import React, { useState } from 'react';
import type { UnifiedPost, UnifiedComment } from '../../types';
import { PixelModal } from '../PixelModal/PixelModal';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { PLATFORMS } from '../../utils/constants';
import { getPublishDate } from '../../utils/sortUtils';
import './DetailModal.css';

interface DetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  post: UnifiedPost | null;
  comments?: UnifiedComment[];
  isLoadingComments?: boolean;
}

export const DetailModal: React.FC<DetailModalProps> = ({
  isOpen,
  onClose,
  post,
  comments = [],
  isLoadingComments = false,
}) => {
  const [expandedComments, setExpandedComments] = useState<Set<string>>(new Set());

  if (!post) return null;

  const platformInfo = PLATFORMS.find((p) => p.value === post.platform);

  const formatTime = (timeStr: string) => {
    const date = getPublishDate(timeStr);
    if (!date) return timeStr || '—';
    try {
      return formatDistanceToNow(date, { addSuffix: true, locale: zhCN });
    } catch {
      return timeStr || '—';
    }
  };

  const toggleComment = (commentId: string) => {
    const newExpanded = new Set(expandedComments);
    if (newExpanded.has(commentId)) {
      newExpanded.delete(commentId);
    } else {
      newExpanded.add(commentId);
    }
    setExpandedComments(newExpanded);
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title={`${platformInfo?.icon} ${platformInfo?.label} - 详情`}
      size="large"
    >
      <div className="detail-modal-content">
        {/* 帖子信息 */}
        <div className="detail-section">
          <h3 className="detail-section-title">📝 帖子信息</h3>
          <div className="detail-post">
            <div className="detail-post-header">
              <h4 className="detail-post-title">{post.title}</h4>
              <span className="detail-post-time">{formatTime(post.publish_time)}</span>
            </div>
            <div className="detail-post-content">{post.content}</div>
            <div className="detail-post-stats">
              <span>👍 {post.like_count}</span>
              <span>💬 {post.comment_count}</span>
              <span>📤 {post.share_count}</span>
              {post.collect_count !== undefined && (
                <span>⭐ {post.collect_count}</span>
              )}
            </div>
            {post.image_urls.length > 0 && (
              <div className="detail-post-images">
                {post.image_urls.map((url, index) => (
                  <img
                    key={index}
                    src={url}
                    alt={`Image ${index + 1}`}
                    className="detail-image"
                  />
                ))}
              </div>
            )}
            {post.video_url && (
              <div className="detail-post-video">
                <video src={post.video_url} controls className="detail-video" />
              </div>
            )}
          </div>
        </div>

        {/* 作者信息 */}
        <div className="detail-section">
          <h3 className="detail-section-title">👤 作者信息</h3>
          <div className="detail-author">
            {post.author.author_avatar && (
              <img
                src={post.author.author_avatar}
                alt={post.author.author_name}
                className="detail-author-avatar"
              />
            )}
            <div className="detail-author-info">
              <div className="detail-author-name">{post.author.author_name}</div>
              <div className="detail-author-id">账号ID: {post.author.author_id}</div>
              <div className="detail-author-platform">平台: {platformInfo?.label}</div>
            </div>
          </div>
        </div>

        {/* 评论列表 */}
        <div className="detail-section">
          <h3 className="detail-section-title">
            💬 评论 {comments.length > 0 && `(${comments.length})`}
          </h3>
          {isLoadingComments ? (
            <div className="detail-comments-loading">加载评论中...</div>
          ) : comments.length > 0 ? (
            <div className="detail-comments">
              {comments.map((comment) => (
                <div key={comment.comment_id} className="detail-comment">
                  <div className="detail-comment-header">
                    <div className="detail-comment-author">
                      {comment.author.author_avatar && (
                        <img
                          src={comment.author.author_avatar}
                          alt={comment.author.author_name}
                          className="detail-comment-avatar"
                        />
                      )}
                      <div className="detail-comment-author-info">
                        <div className="detail-comment-author-name">
                          {comment.author.author_name}
                        </div>
                        <div className="detail-comment-author-details">
                          {comment.author.user_unique_id && (
                            <span className="detail-comment-author-username">
                              @{comment.author.user_unique_id}
                            </span>
                          )}
                          {comment.author.short_user_id && (
                            <span className="detail-comment-author-short-id">
                              ID: {comment.author.short_user_id}
                            </span>
                          )}
                          {comment.author.ip_location && (
                            <span className="detail-comment-author-location">
                              📍 {comment.author.ip_location}
                            </span>
                          )}
                        </div>
                        {comment.author.signature && (
                          <div className="detail-comment-author-signature">
                            {comment.author.signature}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="detail-comment-meta">
                      <span className="detail-comment-time">
                        {formatTime(comment.comment_time)}
                      </span>
                      <span className="detail-comment-likes">👍 {comment.like_count}</span>
                    </div>
                  </div>
                  <div className="detail-comment-content">{comment.content}</div>
                  {comment.sub_comment_count > 0 && (
                    <button
                      className="detail-comment-toggle"
                      onClick={() => toggleComment(comment.comment_id)}
                    >
                      {expandedComments.has(comment.comment_id)
                        ? '收起'
                        : `展开 ${comment.sub_comment_count} 条回复`}
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="detail-comments-empty">暂无评论</div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="detail-actions">
          <a
            href={post.url}
            target="_blank"
            rel="noopener noreferrer"
            className="pixel-button pixel-button-primary"
          >
            打开原链接
          </a>
        </div>
      </div>
    </PixelModal>
  );
};
