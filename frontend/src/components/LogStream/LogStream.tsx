import React, { useEffect, useRef, useState } from 'react';
import { websocketService, LogEntry } from '../../services/websocketService';
import { useSearchStore } from '../../stores/searchStore';
import './LogStream.css';

interface LogStreamProps {
  maxLines?: number;
  autoScroll?: boolean;
  /** 变化时清空当前日志（例如每次新搜索或刷新时由父组件传入新值） */
  clearTrigger?: number;
}

export const LogStream: React.FC<LogStreamProps> = ({
  maxLines = 100,
  autoScroll = true,
  clearTrigger = 0,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const { progress, status, stats } = useSearchStore();
  const isSearching = status === 'searching' || status === 'running';
  const [isExpanded, setIsExpanded] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLogs([]);
  }, [clearTrigger]);

  useEffect(() => {
    // 延迟首次连接，避免页面刚打开时后端尚未就绪导致立即报错（会自动重试）
    const t = window.setTimeout(() => {
      websocketService.connect();
    }, 800);

    const unsubLog = websocketService.subscribe((log) => {
      setLogs((prev) => {
        const newLogs = [...prev, log];
        return newLogs.slice(-maxLines);
      });
    });
    const unsubConn = websocketService.subscribeConnectionState(setConnectionState);

    return () => {
      window.clearTimeout(t);
      unsubLog();
      unsubConn();
    };
  }, [maxLines]);

  useEffect(() => {
    if (isSearching) setIsExpanded(true);
  }, [isSearching]);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getLogLevelClass = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'log-error';
      case 'warning':
        return 'log-warning';
      case 'success':
        return 'log-success';
      default:
        return 'log-info';
    }
  };

  return (
    <div className={`log-stream ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="log-stream-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="log-stream-header-left">
          <span>实时日志</span>
          <span className={`log-connection log-connection-${connectionState}`} title="WebSocket 连接状态">
            {connectionState === 'connected' && '● 已连接'}
            {connectionState === 'connecting' && '○ 连接中…'}
            {connectionState === 'disconnected' && '○ 未连接'}
          </span>
          {stats.totalFound > 0 && (
            <span className="log-stats-indicator">
              已获取: {stats.totalFound} 条
            </span>
          )}
          {isSearching && stats.totalFound === 0 && (
            <span className="log-progress-indicator">
              正在搜索...
            </span>
          )}
        </div>
        <span className="log-toggle">{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="log-stream-content" ref={logContainerRef}>
            {logs.length === 0 ? (
              <div className="log-empty">
                {connectionState === 'disconnected'
                  ? '未连接后端，请确认后端已启动（端口 8000）'
                  : isSearching
                    ? '正在连接日志流，请稍候…'
                    : '等待日志…（开始搜索后会收到进度）'}
              </div>
            ) : (
              logs
                .filter(log => log.message !== 'heartbeat' && log.message !== 'pong') // 过滤心跳消息
                .map((log, index) => (
                  <div key={index} className={`log-entry ${getLogLevelClass(log.level)}`}>
                    <span className="log-time">[{formatTime(log.timestamp)}]</span>
                    {log.platform && (
                      <span className="log-platform">[{log.platform}]</span>
                    )}
                    <span className="log-message">{log.message}</span>
                  </div>
                ))
            )}
        </div>
      )}
    </div>
  );
};
