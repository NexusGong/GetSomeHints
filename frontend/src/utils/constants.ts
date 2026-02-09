/**
 * 常量定义
 */
import type { Platform } from '../types';

export interface PlatformInfo {
  value: Platform;
  label: string;
  icon: string;
  color: string;
}

/** 当前仅展示已接入真实爬虫的平台：抖音、小红书（抖音在前） */
export const PLATFORMS: PlatformInfo[] = [
  { value: 'dy', label: '抖音', icon: '🎵', color: '#000000' },
  { value: 'xhs', label: '小红书', icon: '📕', color: '#FF2442' },
];

// 使用 8000 避免与占用 8080 的其它进程冲突；127.0.0.1 避免 localhost 解析到 IPv6
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
/** 从 API_BASE_URL 派生，保证与后端同源，避免 WebSocket 连接失败 */
export const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ??
  (API_BASE_URL.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://'));
