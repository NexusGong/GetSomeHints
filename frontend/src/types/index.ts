/**
 * 类型定义
 */

export type Platform = 'xhs' | 'dy' | 'ks' | 'bili' | 'wb' | 'tieba' | 'zhihu';

export interface PlatformInfo {
  value: Platform;
  label: string;
  icon: string;
  color: string;
}

export interface UnifiedAuthor {
  author_id: string;
  author_name: string;
  author_avatar?: string;
  platform: Platform;
  // 扩展字段（主要用于评论者）
  user_unique_id?: string;
  short_user_id?: string;
  sec_uid?: string;
  signature?: string;
  ip_location?: string;
}

export interface UnifiedPost {
  platform: Platform;
  post_id: string;
  title: string;
  content: string;
  author: UnifiedAuthor;
  publish_time: string;
  like_count: number;
  comment_count: number;
  share_count: number;
  collect_count?: number;
  url: string;
  image_urls: string[];
  video_url?: string;
  platform_data: Record<string, any>;
}

export interface UnifiedComment {
  comment_id: string;
  post_id: string;
  platform: Platform;
  content: string;
  author: UnifiedAuthor;
  comment_time: string;
  like_count: number;
  parent_comment_id?: string;
  sub_comment_count: number;
}

export interface SearchRequest {
  keywords: string;
  platforms: Platform[];
  max_count?: number;
  enable_comments?: boolean;
  enable_sub_comments?: boolean;
  sort_type?: string;
  time_range?: 'all' | '1day' | '1week' | '1month' | '3months' | '6months';
  content_types?: ('video' | 'image_text' | 'link')[];
}

export interface SearchResponse {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  total_found: number;
  by_platform: Record<Platform, number>;
  progress?: number;
  message: string;
}

export interface AnalysisStats {
  total_posts: number;
  total_comments: number;
  total_authors: number;
  platform_stats: PlatformStats[];
  time_range: {
    start?: string;
    end?: string;
  };
}

export interface PlatformStats {
  platform: Platform;
  post_count: number;
  comment_count: number;
  author_count: number;
  avg_likes: number;
  avg_comments: number;
}
