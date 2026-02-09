/**
 * 导出工具函数
 * 支持 CSV、Excel、JSON 格式导出
 */
import type { UnifiedPost } from '../types';

/**
 * 导出为 CSV 格式
 */
export const exportToCSV = (posts: UnifiedPost[], filename: string = 'search_results') => {
  if (posts.length === 0) {
    alert('没有数据可导出');
    return;
  }

  // CSV 表头
  const headers = [
    '平台',
    'ID',
    '标题',
    '内容',
    '作者',
    '作者ID',
    '发布时间',
    '点赞数',
    '评论数',
    '分享数',
    '收藏数',
    '链接',
  ];

  // 转换数据为 CSV 行
  const rows = posts.map((post) => {
    const escapeCSV = (str: string) => {
      if (str === null || str === undefined) return '';
      const s = String(str);
      // 如果包含逗号、引号或换行符，需要用引号包裹并转义引号
      if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    };

    return [
      post.platform,
      post.post_id,
      escapeCSV(post.title),
      escapeCSV(post.content),
      escapeCSV(post.author.author_name),
      post.author.author_id,
      typeof post.publish_time === 'string' 
        ? post.publish_time 
        : (post.publish_time instanceof Date 
          ? post.publish_time.toISOString() 
          : String(post.publish_time)),
      post.like_count,
      post.comment_count,
      post.share_count,
      post.collect_count || '',
      post.url,
    ].map(escapeCSV).join(',');
  });

  // 组合 CSV 内容
  const csvContent = [headers.join(','), ...rows].join('\n');

  // 添加 BOM 以支持中文
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};

/**
 * 导出为 JSON 格式
 */
export const exportToJSON = (posts: UnifiedPost[], filename: string = 'search_results') => {
  if (posts.length === 0) {
    alert('没有数据可导出');
    return;
  }

  const jsonContent = JSON.stringify(posts, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}_${new Date().toISOString().split('T')[0]}.json`;
  link.click();
  URL.revokeObjectURL(url);
};

/**
 * 导出为 Excel 格式（使用 CSV，Excel 可以打开）
 */
export const exportToExcel = (posts: UnifiedPost[], filename: string = 'search_results') => {
  // Excel 可以打开 CSV 文件，所以我们使用 CSV 格式
  exportToCSV(posts, filename);
};

/**
 * 复制到剪贴板
 */
export const copyToClipboard = async (posts: UnifiedPost[]): Promise<boolean> => {
  if (posts.length === 0) {
    alert('没有数据可复制');
    return false;
  }

  try {
    // 格式化为易读的文本
    const text = posts.map((post, index) => {
      return `[${index + 1}] ${post.platform.toUpperCase()}
标题: ${post.title}
作者: ${post.author.author_name} (@${post.author.author_id})
发布时间: ${typeof post.publish_time === 'string' 
  ? post.publish_time 
  : (post.publish_time instanceof Date 
    ? post.publish_time.toISOString() 
    : String(post.publish_time))}
点赞: ${post.like_count} | 评论: ${post.comment_count} | 分享: ${post.share_count}
链接: ${post.url}
${post.content ? `内容: ${post.content.substring(0, 200)}${post.content.length > 200 ? '...' : ''}` : ''}
---
`;
    }).join('\n');

    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    console.error('复制失败:', error);
    return false;
  }
};
