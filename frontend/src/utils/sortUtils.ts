/**
 * 解析发布时间为毫秒时间戳，用于排序。
 * 支持：ISO 字符串、Date、数字（秒或毫秒）、数字字符串（秒），无效/空返回 0（会排到末尾）。
 * 排序时用「数值大的 = 最新」，所以按 getPublishTimeMs(b) - getPublishTimeMs(a) 即最新在前。
 */
export function getPublishTimeMs(value: string | number | Date | undefined | null): number {
  if (value == null || value === '') return 0;
  if (typeof value === 'number') {
    const ms = value < 1e12 ? value * 1000 : value;
    return Number.isFinite(ms) ? ms : 0;
  }
  if (value instanceof Date) {
    const t = value.getTime();
    return Number.isFinite(t) ? t : 0;
  }
  // 字符串：可能是数字字符串（Unix 秒）或 ISO 日期
  const trimmed = String(value).trim();
  if (!trimmed) return 0;
  // 纯数字：按 Unix 时间戳处理（< 1e12 视为秒，否则毫秒）
  const asNum = Number(trimmed);
  if (Number.isFinite(asNum) && asNum > 0) {
    const ms = asNum < 1e12 ? asNum * 1000 : asNum;
    return ms;
  }
  // ISO 日期：若无时区则按 UTC 解析，避免「无 Z」被当成本地时间导致排序错乱
  let dateStr = trimmed;
  if (trimmed.includes('T') && !/Z|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
    dateStr = trimmed + 'Z';
  }
  const t = new Date(dateStr).getTime();
  return Number.isFinite(t) ? t : 0;
}

/** 解析 publish_time 为 Date，供展示用；与 getPublishTimeMs 同源，保证排序与展示一致 */
export function getPublishDate(value: string | number | Date | undefined | null): Date | null {
  const ms = getPublishTimeMs(value);
  return ms > 0 ? new Date(ms) : null;
}

export type ResultSortBy = 'time' | 'hot' | 'comments';

/** 对帖子列表按 sortBy 排序，不修改原数组 */
export function sortPosts<T extends { publish_time?: string | number | Date; like_count?: number; comment_count?: number }>(
  posts: T[],
  sortBy: ResultSortBy
): T[] {
  const arr = [...posts];
  arr.sort((a, b) => {
    switch (sortBy) {
      case 'time':
        return getPublishTimeMs(b.publish_time) - getPublishTimeMs(a.publish_time);
      case 'hot':
        return (b.like_count ?? 0) - (a.like_count ?? 0);
      case 'comments':
        return (b.comment_count ?? 0) - (a.comment_count ?? 0);
      default:
        return 0;
    }
  });
  return arr;
}
