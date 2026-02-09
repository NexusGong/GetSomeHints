import React from 'react';
import './StatusIndicator.css';

type Status = 'idle' | 'searching' | 'completed' | 'stopped' | 'error';

interface StatusIndicatorProps {
  status: Status;
  message?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  message,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'idle':
        return { className: 'off', label: '就绪' };
      case 'searching':
        return { className: 'on blink', label: '搜索中' };
      case 'completed':
        return { className: 'on', label: '完成' };
      case 'stopped':
        return { className: 'warning', label: '已停止' };
      case 'error':
        return { className: 'error', label: '错误' };
      default:
        return { className: 'off', label: '未知' };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="status-indicator">
      <div className={`pixel-led ${config.className}`}></div>
      <span className="status-label">
        {config.label}
        {message && `: ${message}`}
      </span>
    </div>
  );
};
