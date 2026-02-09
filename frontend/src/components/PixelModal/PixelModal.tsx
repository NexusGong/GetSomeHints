import React, { useEffect } from 'react';
import './PixelModal.css';

interface PixelModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'small' | 'medium' | 'large';
}

export const PixelModal: React.FC<PixelModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'medium',
}) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  return (
    <div 
      className={`pixel-modal-overlay ${isOpen ? 'is-visible' : ''}`}
      onClick={onClose}
      style={{ display: isOpen ? 'flex' : 'none' }}
    >
      <div
        className={`pixel-modal pixel-modal-${size}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pixel-modal-header">
          <h2 className="pixel-modal-title">{title}</h2>
          <button className="pixel-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="pixel-modal-content">{children}</div>
      </div>
    </div>
  );
};
