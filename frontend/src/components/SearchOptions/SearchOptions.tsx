import React, { useEffect, useRef, useState } from 'react';
import './SearchOptions.css';

export type TimeRange = 'all' | '1day' | '1week' | '1month' | '3months' | '6months';
export type ContentType = 'video' | 'image_text' | 'link';

export interface SearchOptionsConfig {
  maxCount: number;
  enableComments: boolean;
  enableSubComments: boolean;
  timeRange: TimeRange;
  contentTypes: ContentType[];
}

interface SearchOptionsProps {
  config: SearchOptionsConfig;
  onChange: (config: SearchOptionsConfig) => void;
  disabled?: boolean;
}

export const SearchOptions: React.FC<SearchOptionsProps> = ({
  config,
  onChange,
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
    onChange({ ...config, timeRange: e.target.value as TimeRange });
  };

  return (
    <div className="search-options">
      <div className="search-options-header">
        <span className="search-options-title">⚙️ 搜索选项</span>
      </div>
      
      <div className="search-options-content">
          <div className="search-options-group">
            <label className="search-options-label">
              <span>搜索时间范围:</span>
              <select
                className="pixel-select search-options-select"
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

          <div className="search-options-group">
            <label className="search-options-label">
              <span>最大搜索数量:</span>
              <input
                type="number"
                className="pixel-input search-options-input"
                min={1}
                max={10000}
                value={maxCountInput}
                onChange={handleMaxCountChange}
                onBlur={handleMaxCountBlur}
                disabled={disabled}
              />
              <span className="search-options-hint">(失焦时取 1–10000)</span>
            </label>
          </div>

          <div className="search-options-group">
            <label className="search-options-checkbox">
              <input
                type="checkbox"
                checked={config.enableComments}
                onChange={handleCommentsToggle}
                disabled={disabled}
              />
              <span>爬取评论</span>
            </label>
          </div>

          <div className="search-options-group">
            <label className="search-options-checkbox">
              <input
                type="checkbox"
                checked={config.enableSubComments}
                onChange={handleSubCommentsToggle}
                disabled={disabled || !config.enableComments}
              />
              <span>爬取二级评论</span>
            </label>
          </div>
        </div>
    </div>
  );
};
