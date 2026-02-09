import React from 'react';
import './PixelButton.css';

interface PixelButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'danger' | 'secondary' | 'default';
  size?: 'small' | 'medium' | 'large';
  title?: string;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
}

export const PixelButton: React.FC<PixelButtonProps> = ({
  children,
  onClick,
  disabled = false,
  variant = 'default',
  size = 'medium',
  type = 'button',
  className = '',
  title,
}) => {
  return (
    <button
      type={type}
      className={`pixel-button pixel-button-${variant} pixel-button-${size} ${className}`}
      onClick={onClick}
      disabled={disabled}
      title={title}
    >
      {children}
    </button>
  );
};
