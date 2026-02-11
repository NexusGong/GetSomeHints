import React from 'react';
import './PixelCard.css';

interface PixelCardProps {
  children: React.ReactNode;
  onClick?: (e?: React.MouseEvent) => void;
  className?: string;
}

export const PixelCard: React.FC<PixelCardProps> = ({
  children,
  onClick,
  className = '',
}) => {
  return (
    <div
      className={`pixel-card ${onClick ? 'pixel-card-clickable' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};
