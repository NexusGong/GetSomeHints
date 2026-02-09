import React from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import type { Platform } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import './PlatformSelectorModal.css';

interface PlatformSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedPlatforms: Platform[];
  onChange: (platforms: Platform[]) => void;
  disabled?: boolean;
}

export const PlatformSelectorModal: React.FC<PlatformSelectorModalProps> = ({
  isOpen,
  onClose,
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

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title="选择平台"
      size="medium"
    >
      <div className="platform-selector-modal">
        <div className="platform-selector-modal-actions">
          <button
            className="pixel-button-small"
            onClick={handleSelectAll}
            disabled={disabled}
            type="button"
          >
            全选
          </button>
          <button
            className="pixel-button-small"
            onClick={handleDeselectAll}
            disabled={disabled}
            type="button"
          >
            取消
          </button>
        </div>
        
        <div className="platform-selector-modal-grid">
          {PLATFORMS.map((platform) => {
            const isSelected = selectedPlatforms.includes(platform.value);
            return (
              <button
                key={platform.value}
                className={`platform-selector-modal-item ${isSelected ? 'selected' : ''}`}
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
          <div className="platform-selector-modal-info">
            已选择 {selectedPlatforms.length} 个平台
          </div>
        )}
      </div>
    </PixelModal>
  );
};
