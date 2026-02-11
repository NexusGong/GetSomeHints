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
  /** 内容类型分布：视频/图文/链接 */
  content_type_distribution?: Record<string, number>;
  /** 点赞区间分布，供决策 */
  like_buckets?: Record<string, number>;
  /** 评论区间分布，供决策 */
  comment_buckets?: Record<string, number>;
}

export interface PlatformStats {
  platform: Platform;
  post_count: number;
  comment_count: number;
  author_count: number;
  avg_likes: number;
  avg_comments: number;
}

/** 大模型分析：联系方式汇总单条 */
export interface ContactSummary {
  author_id: string;
  platform: string;
  contact_type: string;
  value: string;
  source: string;
}

/** 大模型分析：潜在卖家 */
export interface PotentialSeller {
  author_id: string;
  author_name: string;
  platform: string;
  reason: string;
  source_post_id: string;
  contacts: string[];
}

/** 大模型分析：潜在买家（intent_level: explicit_inquiry | interested | sharing_only | unknown） */
export interface PotentialBuyer {
  author_id: string;
  author_name: string;
  platform: string;
  intent_level: string;
  reason: string;
  source_post_id: string;
  contacts: string[];
}

/** 大模型潜在卖/买家分析结果 */
export interface LlmLeadsResult {
  potential_sellers: PotentialSeller[];
  potential_buyers: PotentialBuyer[];
  contacts_summary: ContactSummary[];
  analysis_summary?: string | null;
}

/** 大模型分析场景（与后端 GET /api/analysis/llm-scenarios 一致） */
export interface LlmScenario {
  id: string;
  name: string;
  seller_label: string;
  buyer_label: string;
}
