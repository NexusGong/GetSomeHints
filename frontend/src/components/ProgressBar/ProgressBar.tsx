import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  showText?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  showText = true,
}) => {
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className="progress-bar-container">
      {label && <div className="progress-label">{label}</div>}
      <div className="pixel-progress">
        <div
          className="pixel-progress-bar"
          style={{ width: `${clampedProgress}%` }}
        >
          {showText && <span className="progress-text">{clampedProgress}%</span>}
        </div>
      </div>
    </div>
  );
};
