import React from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { PixelButton } from '../PixelButton/PixelButton';
import './NotificationModal.css';

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message: string;
  type?: 'info' | 'warning' | 'error' | 'success';
}

export const NotificationModal: React.FC<NotificationModalProps> = ({
  isOpen,
  onClose,
  title,
  message,
  type = 'info',
}) => {
  const getTitle = () => {
    if (title) return title;
    switch (type) {
      case 'error':
        return '❌ 错误';
      case 'warning':
        return '⚠️ 警告';
      case 'success':
        return '✅ 成功';
      default:
        return 'ℹ️ 提示';
    }
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title={getTitle()}
      size="small"
    >
      <div className={`notification-modal-content notification-modal-${type}`}>
        <p className="notification-message">{message}</p>
        <div className="notification-actions">
          <PixelButton onClick={onClose} variant="primary" className="notification-confirm-btn">
            确定
          </PixelButton>
        </div>
      </div>
    </PixelModal>
  );
};
