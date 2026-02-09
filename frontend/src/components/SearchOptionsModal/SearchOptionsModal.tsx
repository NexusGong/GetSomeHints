import React, { useEffect, useRef, useState } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import type { SearchOptionsConfig, ContentType } from '../SearchOptions/SearchOptions';
import type { Platform } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import './SearchOptionsModal.css';

const CONTENT_TYPES: { value: ContentType; label: string; icon: string }[] = [
  { value: 'video', label: '视频', icon: '🎬' },
  { value: 'image_text', label: '图文', icon: '📝' },
  { value: 'link', label: '链接', icon: '🔗' },
];

interface SearchOptionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: SearchOptionsConfig;
  onChange: (config: SearchOptionsConfig) => void;
  selectedPlatforms: Platform[];
  onPlatformsChange: (platforms: Platform[]) => void;
  disabled?: boolean;
}

export const SearchOptionsModal: React.FC<SearchOptionsModalProps> = ({
  isOpen,
  onClose,
  config,
  onChange,
  selectedPlatforms,
  onPlatformsChange,
  disabled = false,
}) => {
  const [maxCountInput, setMaxCountInput] = useState(String(config.maxCount));
  const lastAppliedMaxCountRef = useRef(config.maxCount);

  useEffect(() => {
    if (config.maxCount !== lastAppliedMaxCountRef.current) {
      lastAppliedMaxCountRef.current = config.maxCount;
      setMaxCountInput(String(config.maxCount));
    }
  }, [config.maxCount]);

  const handleMaxCountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMaxCountInput(e.target.value);
  };

  const handleMaxCountBlur = () => {
    const raw = maxCountInput.trim();
    if (raw === '') {
      const fallback = 1;
      lastAppliedMaxCountRef.current = fallback;
      setMaxCountInput(String(fallback));
      onChange({ ...config, maxCount: fallback });
      return;
    }
    const value = parseInt(raw, 10);
    const clamped = Number.isNaN(value) ? 1 : Math.min(10000, Math.max(1, value));
    lastAppliedMaxCountRef.current = clamped;
    setMaxCountInput(String(clamped));
    onChange({ ...config, maxCount: clamped });
  };

  const handleCommentsToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...config, enableComments: e.target.checked });
  };

  const handleSubCommentsToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...config, enableSubComments: e.target.checked });
  };

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...config, timeRange: e.target.value as SearchOptionsConfig['timeRange'] });
  };

  const handleContentTypeToggle = (contentType: ContentType) => {
    if (disabled) return;
    
    const currentTypes = config.contentTypes || ['video', 'image_text', 'link'];
    if (currentTypes.includes(contentType)) {
      const newTypes = currentTypes.filter(t => t !== contentType);
      // 如果全部取消选择，则选择全部（避免空选择）
      onChange({ ...config, contentTypes: newTypes.length > 0 ? newTypes : ['video', 'image_text', 'link'] });
    } else {
      onChange({ ...config, contentTypes: [...currentTypes, contentType] });
    }
  };

  const handleSelectAllContentTypes = () => {
    if (disabled) return;
    onChange({ ...config, contentTypes: CONTENT_TYPES.map(t => t.value) });
  };

  const handleDeselectAllContentTypes = () => {
    if (disabled) return;
    onChange({ ...config, contentTypes: [] });
  };

  const handlePlatformToggle = (platform: Platform) => {
    if (disabled) return;
    
    if (selectedPlatforms.includes(platform)) {
      onPlatformsChange(selectedPlatforms.filter(p => p !== platform));
    } else {
      onPlatformsChange([...selectedPlatforms, platform]);
    }
  };

  const handleSelectAllPlatforms = () => {
    if (disabled) return;
    onPlatformsChange(PLATFORMS.map(p => p.value));
  };

  const handleDeselectAllPlatforms = () => {
    if (disabled) return;
    onPlatformsChange([]);
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title="搜索设置"
      size="medium"
    >
      <div className="search-options-modal">
        {/* 平台选择 */}
        <div className="search-options-modal-group">
          <div className="search-options-modal-label">
            <span>选择平台:</span>
            <div className="search-options-modal-platform-actions">
              <button
                className="pixel-button-small"
                onClick={handleSelectAllPlatforms}
                disabled={disabled}
                type="button"
              >
                全选
              </button>
              <button
                className="pixel-button-small"
                onClick={handleDeselectAllPlatforms}
                disabled={disabled}
                type="button"
              >
                取消
              </button>
            </div>
          </div>
          <div className="search-options-modal-platforms">
            {PLATFORMS.map((platform) => {
              const isSelected = selectedPlatforms.includes(platform.value);
              return (
                <button
                  key={platform.value}
                  className={`search-options-modal-platform-item ${isSelected ? 'selected' : ''}`}
                  style={{ '--platform-color': platform.color } as React.CSSProperties}
                  onClick={() => handlePlatformToggle(platform.value)}
                  disabled={disabled}
                  type="button"
                >
                  <span className="platform-icon">{platform.icon}</span>
                  <span className="platform-label">{platform.label}</span>
                </button>
              );
            })}
          </div>
          {selectedPlatforms.length > 0 && (
            <div className="search-options-modal-platform-info">
              已选择 {selectedPlatforms.length} 个平台
            </div>
          )}
        </div>

        {/* 分隔线 */}
        <div className="search-options-modal-divider"></div>
        {/* 搜索选项 */}
        <div className="search-options-modal-group">
          <label className="search-options-modal-label">
            <span>搜索时间范围:</span>
            <select
              className="pixel-select search-options-modal-select"
              value={config.timeRange}
              onChange={handleTimeRangeChange}
              disabled={disabled}
            >
              <option value="all">全部时间</option>
              <option value="1day">一天内</option>
              <option value="1week">一周内</option>
              <option value="1month">一个月内</option>
              <option value="3months">三个月内</option>
              <option value="6months">六个月内</option>
            </select>
          </label>
        </div>

        <div className="search-options-modal-group">
          <div className="search-options-modal-label">
            <span>搜索内容类型:</span>
            <div className="search-options-modal-platform-actions">
              <button
                className="pixel-button-small"
                onClick={handleSelectAllContentTypes}
                disabled={disabled}
                type="button"
              >
                全选
              </button>
              <button
                className="pixel-button-small"
                onClick={handleDeselectAllContentTypes}
                disabled={disabled}
                type="button"
              >
                取消
              </button>
            </div>
          </div>
          <div className="search-options-modal-platforms">
            {CONTENT_TYPES.map((contentType) => {
              const contentTypes = config.contentTypes || ['video', 'image_text', 'link'];
              const isSelected = contentTypes.includes(contentType.value);
              return (
                <button
                  key={contentType.value}
                  className={`search-options-modal-platform-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleContentTypeToggle(contentType.value)}
                  disabled={disabled}
                  type="button"
                >
                  <span className="platform-icon">{contentType.icon}</span>
                  <span className="platform-label">{contentType.label}</span>
                </button>
              );
            })}
          </div>
          <div className="search-options-modal-platform-info">
            {(() => {
              const contentTypes = config.contentTypes || ['video', 'image_text', 'link'];
              if (contentTypes.length === 0) {
                return '未选择任何类型（将显示所有类型）';
              } else if (contentTypes.length === CONTENT_TYPES.length) {
                return '已选择全部类型';
              } else {
                return `已选择 ${contentTypes.length} 种类型`;
              }
            })()}
          </div>
        </div>

        <div className="search-options-modal-group">
          <label className="search-options-modal-label">
            <span>最大搜索数量:</span>
            <div className="search-options-modal-input-wrapper">
              <input
                type="number"
                className="pixel-input search-options-modal-input"
                min={1}
                max={10000}
                value={maxCountInput}
                onChange={handleMaxCountChange}
                onBlur={handleMaxCountBlur}
                disabled={disabled}
              />
              <span className="search-options-modal-hint">(失焦时取 1–10000)</span>
            </div>
          </label>
        </div>

        <div className="search-options-modal-group">
          <label className="search-options-modal-checkbox">
            <input
              type="checkbox"
              checked={config.enableComments}
              onChange={handleCommentsToggle}
              disabled={disabled}
            />
            <span>爬取评论</span>
          </label>
        </div>

        <div className="search-options-modal-group">
          <label className="search-options-modal-checkbox">
            <input
              type="checkbox"
              checked={config.enableSubComments}
              onChange={handleSubCommentsToggle}
              disabled={disabled || !config.enableComments}
            />
            <span>爬取二级评论</span>
          </label>
        </div>

        {/* 确认按钮 */}
        <div className="search-options-modal-footer">
          <button
            className="search-options-modal-confirm-btn"
            onClick={onClose}
            disabled={disabled}
            type="button"
          >
            确认
          </button>
        </div>
      </div>
    </PixelModal>
  );
};
