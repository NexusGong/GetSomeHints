import React from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import type { Platform } from '../../types';
import { PLATFORMS } from '../../utils/constants';
import './PlatformSelectorModal.css';

interface PlatformSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedPlatform: Platform | null;
  onChange: (platform: Platform | null) => void;
  disabled?: boolean;
}

export const PlatformSelectorModal: React.FC<PlatformSelectorModalProps> = ({
  isOpen,
  onClose,
  selectedPlatform,
  onChange,
  disabled = false,
}) => {
  const handlePlatformSelect = (platform: Platform) => {
    if (disabled) return;
    // 单选：点击已选中的取消选择，点击未选中的则选中
    onChange(selectedPlatform === platform ? null : platform);
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title="选择平台"
      size="medium"
    >
      <div className="platform-selector-modal">
        <div className="platform-selector-modal-grid">
          {PLATFORMS.map((platform) => {
            const isSelected = selectedPlatform === platform.value;
            return (
              <button
                key={platform.value}
                className={`platform-selector-modal-item ${isSelected ? 'selected' : ''}`}
                style={{ '--platform-color': platform.color } as React.CSSProperties}
                onClick={() => handlePlatformSelect(platform.value)}
                disabled={disabled}
                type="button"
              >
                <span className="platform-icon">{platform.icon}</span>
                <span className="platform-label">{platform.label}</span>
              </button>
            );
          })}
        </div>
        {selectedPlatform !== null && (
          <div className="platform-selector-modal-info">
            已选择 {PLATFORMS.find(p => p.value === selectedPlatform)?.label ?? selectedPlatform}
          </div>
        )}
      </div>
    </PixelModal>
  );
};
