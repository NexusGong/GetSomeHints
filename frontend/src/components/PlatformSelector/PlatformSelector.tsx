import React from 'react';
import type { Platform } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import './PlatformSelector.css';

interface PlatformSelectorProps {
  selectedPlatforms: Platform[];
  onChange: (platforms: Platform[]) => void;
  disabled?: boolean;
}

export const PlatformSelector: React.FC<PlatformSelectorProps> = ({
  selectedPlatforms,
  onChange,
  disabled = false,
}) => {
  const handlePlatformToggle = (platform: Platform) => {
    if (disabled) return;
    
    if (selectedPlatforms.includes(platform)) {
      onChange(selectedPlatforms.filter(p => p !== platform));
    } else {
      onChange([...selectedPlatforms, platform]);
    }
  };

  const handleSelectAll = () => {
    if (disabled) return;
    onChange(PLATFORMS.map(p => p.value));
  };

  const handleDeselectAll = () => {
    if (disabled) return;
    onChange([]);
  };

  const allSelected = selectedPlatforms.length === PLATFORMS.length;
  const noneSelected = selectedPlatforms.length === 0;

  return (
    <div className="platform-selector">
      <div className="platform-selector-header">
        <span className="platform-selector-title">📱 选择平台</span>
        <div className="platform-selector-actions">
          <button
            className="pixel-button-small"
            onClick={handleSelectAll}
            disabled={disabled || allSelected}
            type="button"
          >
            全选
          </button>
          <button
            className="pixel-button-small"
            onClick={handleDeselectAll}
            disabled={disabled || noneSelected}
            type="button"
          >
            取消
          </button>
        </div>
      </div>
      
      <div className="platform-selector-grid">
        {PLATFORMS.map((platform) => {
          const isSelected = selectedPlatforms.includes(platform.value);
          return (
            <button
              key={platform.value}
              className={`platform-button ${isSelected ? 'selected' : ''}`}
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
        <div className="platform-selector-info">
          已选择 {selectedPlatforms.length} 个平台
        </div>
      )}
    </div>
  );
};
