/**
 * 搜索选项类型定义，供 SearchOptionsModal、searchStore 使用。
 * 原 SearchOptions 组件已废弃（由 SearchOptionsModal 内联实现）。
 */
export type TimeRange = 'all' | '1day' | '1week' | '1month' | '3months' | '6months';
export type ContentType = 'video' | 'image_text' | 'link';

export interface SearchOptionsConfig {
  maxCount: number;
  enableComments: boolean;
  enableSubComments: boolean;
  timeRange: TimeRange;
  contentTypes: ContentType[];
}
