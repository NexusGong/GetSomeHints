/**
 * WebSocket 服务
 */
import { WS_BASE_URL } from '../utils/constants';

export type LogLevel = 'info' | 'warning' | 'error' | 'success';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  platform?: string;
  /** 非空时表示本条应在原位置更新，不追加新行 */
  replaceId?: string;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Set<(log: LogEntry) => void> = new Set();
  private connectionStateListeners: Set<(state: ConnectionState) => void> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1500;
  private _connectionState: ConnectionState = 'disconnected';
  private setConnectionState(state: ConnectionState) {
    if (this._connectionState === state) return;
    this._connectionState = state;
    this.connectionStateListeners.forEach((cb) => {
      try {
        cb(state);
      } catch {}
    });
  }

  getConnectionState(): ConnectionState {
    if (this.ws?.readyState === WebSocket.OPEN) return 'connected';
    if (this.ws?.readyState === WebSocket.CONNECTING) return 'connecting';
    return this._connectionState;
  }

  subscribeConnectionState(callback: (state: ConnectionState) => void): () => void {
    this.connectionStateListeners.add(callback);
    callback(this.getConnectionState());
    return () => {
      this.connectionStateListeners.delete(callback);
    };
  }

  connect(url: string = `${WS_BASE_URL}/api/ws/logs`) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.setConnectionState('connected');
      return;
    }
    if (this.ws?.readyState === WebSocket.CONNECTING) {
      this.setConnectionState('connecting');
      return;
    }

    this.setConnectionState('connecting');
    try {
      const wsUrl = url.startsWith('ws') ? url : url.replace(/^http/, 'ws');
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setConnectionState('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const logEntry: LogEntry = {
            timestamp: data.timestamp || new Date().toISOString(),
            level: data.level || 'info',
            message: data.message || data.content || '',
            platform: data.platform,
            replaceId: data.replace_id,
          };
          this.notifyListeners(logEntry);
        } catch {
          // 忽略非 JSON 消息
        }
      };

      this.ws.onerror = () => {
        // 不刷控制台，onclose 会触发重连
      };

      this.ws.onclose = () => {
        this.setConnectionState('disconnected');
        this.ws = null;
        this.attemptReconnect(url);
      };
    } catch {
      this.setConnectionState('disconnected');
      this.attemptReconnect(url);
    }
  }

  private attemptReconnect(url: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(
        this.reconnectDelay * this.reconnectAttempts,
        10000
      );
      setTimeout(() => {
        this.connect(url);
      }, delay);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  subscribe(callback: (log: LogEntry) => void) {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  private notifyListeners(log: LogEntry) {
    this.listeners.forEach((callback) => {
      try {
        callback(log);
      } catch (error) {
        console.error('Error in WebSocket listener:', error);
      }
    });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();
