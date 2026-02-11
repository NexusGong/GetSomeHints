import React, { useEffect, useState, useMemo } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { analysisApi } from '../../services/api';
import type { AnalysisStats, LlmLeadsResult, Platform, PlatformStats, UnifiedPost } from '../../types';
import type { HistoryRecord } from '../../stores/historyStore';
import { PLATFORMS } from '../../utils/constants';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Pie, Line, Bar } from 'react-chartjs-2';
import './AnalysisModal.css';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

/** 根据帖子推断内容类型 */
function postContentType(p: UnifiedPost): string {
  if (p.video_url) return 'video';
  if (p.image_urls?.length) return 'image_text';
  return 'link';
}

/** 从 publish_time 解析出 YYYY-MM-DD */
function parsePublishDate(publishTime: string): string | null {
  if (!publishTime || typeof publishTime !== 'string') return null;
  const s = publishTime.trim();
  if (/^\d+$/.test(s)) {
    let ts = parseInt(s, 10);
    if (ts > 1e12) ts = Math.floor(ts / 1000);
    try {
      return new Date(ts * 1000).toISOString().slice(0, 10);
    } catch {
      return null;
    }
  }
  if (s.length >= 10 && s[4] === '-' && s[7] === '-') return s.slice(0, 10);
  return null;
}

export interface FrequentCommentItem {
  text: string;
  count: number;
  commenters: string[];
}

export interface TopCommenterItem {
  author_id: string;
  author_name: string;
  platform: string;
  comment_count: number;
}

/** 从帖子的内嵌评论中提取高频评论与评论者 */
function extractCommentStats(posts: UnifiedPost[]): {
  frequentComments: FrequentCommentItem[];
  topCommenters: TopCommenterItem[];
} {
  const comments: { content: string; author_name: string; author_id: string; platform: string }[] = [];
  posts.forEach((p) => {
    const list = (p.platform_data?.comments ?? []) as Array<{ content?: string; author?: { author_name?: string; author_id?: string; platform?: string } }>;
    list.forEach((c) => {
      const content = (c.content ?? '').trim();
      if (!content) return;
      const author = c.author ?? {};
      comments.push({
        content,
        author_name: author.author_name ?? author.author_id ?? '未知',
        author_id: author.author_id ?? '',
        platform: author.platform ?? (p.platform || ''),
      });
    });
  });

  const textKey = (s: string) => s.replace(/\s+/g, ' ').slice(0, 80);
  const byText: Record<string, { count: number; commenters: Set<string> }> = {};
  comments.forEach((c) => {
    const key = textKey(c.content);
    if (!byText[key]) byText[key] = { count: 0, commenters: new Set() };
    byText[key].count += 1;
    byText[key].commenters.add(c.author_name || '未知');
  });
  const frequentComments: FrequentCommentItem[] = Object.entries(byText)
    .map(([text, v]) => ({ text, count: v.count, commenters: Array.from(v.commenters).slice(0, 5) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const commenterCounts: Record<string, { count: number; author_name: string; author_id: string; platform: string }> = {};
  comments.forEach((c) => {
    const key = `${c.author_id}\t${c.platform}`;
    if (!commenterCounts[key]) commenterCounts[key] = { count: 0, author_name: c.author_name, author_id: c.author_id, platform: c.platform };
    commenterCounts[key].count += 1;
  });
  const topCommenters: TopCommenterItem[] = Object.values(commenterCounts)
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
    .map((o) => ({ author_id: o.author_id, author_name: o.author_name, platform: o.platform, comment_count: o.count }));

  return { frequentComments, topCommenters };
}

/** 基于当前帖子列表在前端计算分析数据（不依赖 task_id/后端） */
function computeAnalysisFromPosts(posts: UnifiedPost[]): {
  stats: AnalysisStats;
  distribution: Record<string, number>;
  trends: Record<string, number>;
  topAuthors: { author: { author_id: string; author_name: string; platform: string }; post_count: number }[];
  topPosts: { post_id: string; platform: string; title: string; like_count: number; comment_count: number; content_type: string }[];
  frequentComments: FrequentCommentItem[];
  topCommenters: TopCommenterItem[];
} {
  const total_posts = posts.length;
  const total_comments = posts.reduce((s, p) => s + p.comment_count, 0);
  const authorsSet = new Set(posts.map((p) => `${p.author.author_id}\t${p.platform}`));
  const total_authors = authorsSet.size;

  const byPlatform: Record<string, number> = {};
  posts.forEach((p) => { byPlatform[p.platform] = (byPlatform[p.platform] || 0) + 1; });

  const platform_stats: PlatformStats[] = Object.keys(byPlatform).sort().map((platform) => {
    const plPosts = posts.filter((p) => p.platform === platform);
    const sumLikes = plPosts.reduce((s, p) => s + p.like_count, 0);
    const sumComments = plPosts.reduce((s, p) => s + p.comment_count, 0);
    const authorCount = new Set(plPosts.map((p) => p.author.author_id)).size;
    return {
      platform: platform as Platform,
      post_count: plPosts.length,
      comment_count: plPosts.reduce((s, p) => s + p.comment_count, 0),
      author_count: authorCount,
      avg_likes: plPosts.length ? sumLikes / plPosts.length : 0,
      avg_comments: plPosts.length ? sumComments / plPosts.length : 0,
    };
  });

  const content_type_distribution: Record<string, number> = {};
  posts.forEach((p) => {
    const t = postContentType(p);
    content_type_distribution[t] = (content_type_distribution[t] || 0) + 1;
  });

  const like_buckets = { '0-100': 0, '101-1k': 0, '1k-10k': 0, '10k+': 0 };
  const comment_buckets = { '0-10': 0, '11-100': 0, '101-1k': 0, '1k+': 0 };
  posts.forEach((p) => {
    if (p.like_count <= 100) like_buckets['0-100']++;
    else if (p.like_count <= 1000) like_buckets['101-1k']++;
    else if (p.like_count <= 10000) like_buckets['1k-10k']++;
    else like_buckets['10k+']++;
    if (p.comment_count <= 10) comment_buckets['0-10']++;
    else if (p.comment_count <= 100) comment_buckets['11-100']++;
    else if (p.comment_count <= 1000) comment_buckets['101-1k']++;
    else comment_buckets['1k+']++;
  });

  const trends: Record<string, number> = {};
  posts.forEach((p) => {
    const day = parsePublishDate(p.publish_time);
    if (day) trends[day] = (trends[day] || 0) + 1;
  });

  const authorCounts: Record<string, number> = {};
  const authorInfo: Record<string, { author_id: string; author_name: string; platform: string }> = {};
  posts.forEach((p) => {
    const key = `${p.author.author_id}\t${p.platform}`;
    authorCounts[key] = (authorCounts[key] || 0) + 1;
    if (!authorInfo[key]) {
      authorInfo[key] = {
        author_id: p.author.author_id,
        author_name: p.author.author_name || p.author.author_id,
        platform: p.platform,
      };
    }
  });
  const topAuthors = Object.entries(authorCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([k, c]) => ({ author: authorInfo[k], post_count: c }));

  const topPosts = [...posts]
    .sort((a, b) => b.like_count - a.like_count)
    .slice(0, 10)
    .map((p) => ({
      post_id: p.post_id,
      platform: p.platform,
      title: (p.title || p.content || '').slice(0, 80),
      like_count: p.like_count,
      comment_count: p.comment_count,
      content_type: postContentType(p),
    }));

  const stats: AnalysisStats = {
    total_posts,
    total_comments,
    total_authors,
    platform_stats,
    time_range: {},
    content_type_distribution,
    like_buckets,
    comment_buckets,
  };

  const { frequentComments, topCommenters } = extractCommentStats(posts);

  return { stats, distribution: byPlatform, trends, topAuthors, topPosts, frequentComments, topCommenters };
}

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string | null;
  /** 当前页面的搜索结果；传入则直接基于这些数据做分析 */
  posts?: UnifiedPost[] | null;
  /** 历史记录列表；无当前结果时可选择其中一条进行分析 */
  historyRecords?: HistoryRecord[];
  /** 打开时是否滚动到大模型分析区块 */
  scrollToLlmOnOpen?: boolean;
}

export const AnalysisModal: React.FC<AnalysisModalProps> = ({
  isOpen,
  onClose,
  taskId,
  posts: postsProp = null,
  historyRecords = [],
  scrollToLlmOnOpen = false,
}) => {
  const [stats, setStats] = useState<AnalysisStats | null>(null);
  const [distribution, setDistribution] = useState<Record<string, number>>({});
  const [trends, setTrends] = useState<Record<string, number>>({});
  const [topAuthors, setTopAuthors] = useState<any[]>([]);
  const [topPosts, setTopPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedHistoryRecord, setSelectedHistoryRecord] = useState<HistoryRecord | null>(null);
  const [llmResult, setLlmResult] = useState<LlmLeadsResult | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);

  const analysisPosts: UnifiedPost[] = (postsProp && postsProp.length > 0)
    ? postsProp
    : (selectedHistoryRecord?.results ?? []);
  const hasLocalData = analysisPosts.length > 0;

  const computedFromPosts = useMemo(() => {
    if (!hasLocalData) return null;
    return computeAnalysisFromPosts(analysisPosts);
  }, [hasLocalData, analysisPosts]);

  useEffect(() => {
    if (!isOpen) {
      setSelectedHistoryRecord(null);
      return;
    }
    setLoadError(null);
    if (hasLocalData && computedFromPosts) {
      setStats(computedFromPosts.stats);
      setDistribution(computedFromPosts.distribution);
      setTrends(computedFromPosts.trends);
      setTopAuthors(computedFromPosts.topAuthors);
      setTopPosts(computedFromPosts.topPosts);
      setLoading(false);
      return;
    }
    if (taskId) {
      loadAnalysisData();
    }
  }, [isOpen, taskId, hasLocalData, computedFromPosts]);

  useEffect(() => {
    if (isOpen && scrollToLlmOnOpen) {
      const timer = setTimeout(() => {
        document.getElementById('analysis-llm-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [isOpen, scrollToLlmOnOpen]);

  const displayStats = hasLocalData && computedFromPosts ? computedFromPosts.stats : stats;
  const displayDistribution = hasLocalData && computedFromPosts ? computedFromPosts.distribution : distribution;
  const displayTrends = hasLocalData && computedFromPosts ? computedFromPosts.trends : trends;
  const displayTopAuthors = hasLocalData && computedFromPosts ? computedFromPosts.topAuthors : topAuthors;
  const displayTopPosts = hasLocalData && computedFromPosts ? computedFromPosts.topPosts : topPosts;
  const displayFrequentComments = hasLocalData && computedFromPosts ? computedFromPosts.frequentComments : [];
  const displayTopCommenters = hasLocalData && computedFromPosts ? computedFromPosts.topCommenters : [];

  const showHistoryPicker = !hasLocalData && !taskId && historyRecords.length > 0;
  const handleClose = () => {
    setSelectedHistoryRecord(null);
    setLlmResult(null);
    setLlmError(null);
    onClose();
  };

  const canRunLlmAnalysis = hasLocalData || taskId;
  const handleRunLlmLeadsAnalysis = async () => {
    if (!canRunLlmAnalysis) return;
    setLlmLoading(true);
    setLlmError(null);
    setLlmResult(null);
    try {
      const result = await analysisApi.runLlmLeadsAnalysis({
        posts: hasLocalData ? analysisPosts : undefined,
        taskId: !hasLocalData && taskId ? taskId : undefined,
      });
      setLlmResult(result);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? '分析请求失败';
      setLlmError(Array.isArray(msg) ? msg.join(' ') : String(msg));
    } finally {
      setLlmLoading(false);
    }
  };

  const loadAnalysisData = async () => {
    if (!taskId) return;

    setLoading(true);
    setLoadError(null);
    try {
      const [statsData, distData, trendsData, authorsData, topPostsData] = await Promise.all([
        analysisApi.getStats(taskId),
        analysisApi.getDistribution(taskId),
        analysisApi.getTrends(taskId),
        analysisApi.getTopAuthors(taskId, 10),
        analysisApi.getTopPosts(taskId, 10, 'likes').catch(() => []),
      ]);

      setStats(statsData);
      setDistribution(distData);
      setTrends(trendsData);
      setTopAuthors(authorsData);
      setTopPosts(Array.isArray(topPostsData) ? topPostsData : []);
    } catch (error) {
      console.error('Failed to load analysis data:', error);
      setLoadError('加载失败，请确认当前搜索任务有效后重试。');
    } finally {
      setLoading(false);
    }
  };

  const contentTypeLabels: Record<string, string> = {
    video: '视频',
    image_text: '图文',
    link: '链接',
  };

  const pieData = {
    labels: Object.keys(displayDistribution).map(
      (p) => PLATFORMS.find((pl) => pl.value === p)?.label || p
    ),
    datasets: [
      {
        data: Object.values(displayDistribution),
        backgroundColor: Object.keys(displayDistribution).map(
          (p) => PLATFORMS.find((pl) => pl.value === p)?.color || '#00ff00'
        ),
        borderColor: '#000000',
        borderWidth: 2,
      },
    ],
  };

  const lineData = {
    labels: Object.keys(displayTrends).sort(),
    datasets: [
      {
        label: '发布数量',
        data: Object.keys(displayTrends)
          .sort()
          .map((key) => displayTrends[key]),
        borderColor: '#00ff00',
        backgroundColor: 'rgba(0, 255, 0, 0.1)',
        borderWidth: 2,
        fill: true,
      },
    ],
  };

  const barData = {
    labels: displayTopAuthors.slice(0, 10).map((a) => a.author.author_name),
    datasets: [
      {
        label: '帖子数',
        data: displayTopAuthors.slice(0, 10).map((a) => a.post_count),
        backgroundColor: '#00ff00',
        borderColor: '#008800',
        borderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          font: {
            family: "'Press Start 2P', monospace",
            size: 8,
          },
          color: '#ffffff',
        },
      },
      title: {
        display: true,
        font: {
          family: "'Press Start 2P', monospace",
          size: 10,
        },
        color: '#00ff00',
      },
    },
    scales: {
      x: {
        ticks: {
          font: {
            family: "'Press Start 2P', monospace",
            size: 6,
          },
          color: '#ffffff',
        },
        grid: {
          color: 'rgba(0, 255, 0, 0.1)',
        },
      },
      y: {
        ticks: {
          font: {
            family: "'Press Start 2P', monospace",
            size: 6,
          },
          color: '#ffffff',
        },
        grid: {
          color: 'rgba(0, 255, 0, 0.1)',
        },
      },
    },
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={handleClose}
      title="📊 数据分析"
      size="large"
    >
      <div className="analysis-modal-content">
        {showHistoryPicker ? (
          <div className="analysis-empty-state">
            <p className="analysis-empty-state-title">当前无本次搜索结果。请选择一条历史记录进行分析：</p>
            <ul className="analysis-history-list">
              {historyRecords.slice(0, 20).map((record) => (
                <li key={record.id}>
                  <button
                    type="button"
                    className="analysis-history-item"
                    onClick={() => setSelectedHistoryRecord(record)}
                  >
                    <span className="analysis-history-keyword">「{record.keyword}」</span>
                    <span className="analysis-history-meta">
                      {record.results.length} 条 · {record.platforms.join('、')} · {new Date(record.createdAt).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : !hasLocalData && !taskId ? (
          <div className="analysis-empty-state">
            <p>请先完成一次搜索或从历史记录中选择数据后再进行分析。</p>
          </div>
        ) : loadError ? (
          <div className="analysis-empty-state analysis-error-state">
            <p>{loadError}</p>
          </div>
        ) : !hasLocalData && loading ? (
          <div className="analysis-loading">加载中...</div>
        ) : (
          <>
            {selectedHistoryRecord && (
              <div className="analysis-back-history">
                <button type="button" onClick={() => setSelectedHistoryRecord(null)}>
                  ← 选择其他历史记录
                </button>
              </div>
            )}
            {/* 统计概览 */}
            {displayStats && (
              <section className="analysis-section analysis-stats-section">
                <h3 className="analysis-section-title">概览</h3>
                <div className="analysis-stats-overview">
                  <div className="stat-card">
                    <div className="stat-value">{displayStats.total_posts}</div>
                    <div className="stat-label">总帖子数</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{displayStats.total_comments}</div>
                    <div className="stat-label">总评论数</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{displayStats.total_authors}</div>
                    <div className="stat-label">总作者数</div>
                  </div>
                </div>
              </section>
            )}

            {/* 大模型分析：潜在卖/买家 */}
            <section id="analysis-llm-section" className="analysis-section analysis-llm-section">
              <h3 className="analysis-section-title">大模型分析（潜在卖家 / 潜在买家）</h3>
              <p className="analysis-section-desc">基于 DeepSeek 对当前帖子与评论做语义分析，识别潜在卖家、潜在买家及消费意向等级，并整理联系方式。</p>
              {canRunLlmAnalysis ? (
                <>
                  <div className="analysis-llm-actions">
                    <button
                      type="button"
                      className="pixel-button analysis-llm-run-btn"
                      onClick={handleRunLlmLeadsAnalysis}
                      disabled={llmLoading}
                    >
                      {llmLoading ? '分析中…' : '运行 DeepSeek 分析'}
                    </button>
                  </div>
                  {llmError && (
                    <div className="analysis-llm-error">
                      {llmError}
                    </div>
                  )}
                  {llmResult && (
                    <div className="analysis-llm-result">
                      {llmResult.analysis_summary && (
                        <p className="analysis-llm-summary">{llmResult.analysis_summary}</p>
                      )}
                      {llmResult.potential_sellers.length > 0 && (
                        <div className="analysis-llm-block">
                          <h4 className="analysis-llm-block-title">潜在卖家</h4>
                          <ul className="analysis-llm-list">
                            {llmResult.potential_sellers.map((s, idx) => (
                              <li key={`s-${s.author_id}-${s.platform}-${idx}`} className="analysis-llm-item">
                                <span className="analysis-llm-item-name">{s.author_name || s.author_id}</span>
                                <span className="analysis-llm-item-platform">{PLATFORMS.find((p) => p.value === s.platform)?.label ?? s.platform}</span>
                                <span className="analysis-llm-item-reason">{s.reason}</span>
                                {s.contacts.length > 0 && (
                                  <span className="analysis-llm-item-contacts">联系方式: {s.contacts.join(' / ')}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {llmResult.potential_buyers.length > 0 && (
                        <div className="analysis-llm-block">
                          <h4 className="analysis-llm-block-title">潜在买家（按意向排序）</h4>
                          <ul className="analysis-llm-list">
                            {llmResult.potential_buyers.map((b, idx) => (
                              <li key={`b-${b.author_id}-${b.platform}-${idx}`} className="analysis-llm-item">
                                <span className="analysis-llm-item-name">{b.author_name || b.author_id}</span>
                                <span className="analysis-llm-item-platform">{PLATFORMS.find((p) => p.value === b.platform)?.label ?? b.platform}</span>
                                <span className="analysis-llm-intent">{({ explicit_inquiry: '明确询价/求购', interested: '感兴趣/羡慕', sharing_only: '仅分享/炫耀', unknown: '无法判断' })[b.intent_level] ?? b.intent_level}</span>
                                <span className="analysis-llm-item-reason">{b.reason}</span>
                                {b.contacts.length > 0 && (
                                  <span className="analysis-llm-item-contacts">联系方式: {b.contacts.join(' / ')}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {llmResult.contacts_summary.length > 0 && (
                        <div className="analysis-llm-block">
                          <h4 className="analysis-llm-block-title">联系方式汇总</h4>
                          <ul className="analysis-llm-list analysis-llm-contacts">
                            {llmResult.contacts_summary.map((c, idx) => (
                              <li key={`c-${idx}`} className="analysis-llm-item">
                                <span className="analysis-llm-item-name">{c.author_id}</span>
                                <span className="analysis-llm-item-platform">{c.platform}</span>
                                <span>{c.contact_type}: {c.value}</span>
                                {c.source && <span className="analysis-llm-item-source">（{c.source}）</span>}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {llmResult.potential_sellers.length === 0 && llmResult.potential_buyers.length === 0 && !llmResult.analysis_summary && (
                        <p className="analysis-section-desc">本次未识别到潜在卖家或买家。</p>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="analysis-section-desc">请先有搜索结果或选择历史记录后再运行分析。</p>
              )}
            </section>

            {/* 内容类型分布（多维度决策） */}
            {displayStats?.content_type_distribution && Object.keys(displayStats.content_type_distribution).length > 0 && (
              <section className="analysis-section">
                <h3 className="analysis-section-title">📋 内容类型分布</h3>
                <div className="analysis-buckets">
                  {Object.entries(displayStats.content_type_distribution).map(([key, value]) => (
                    <div key={key} className="analysis-bucket-row">
                      <span className="analysis-bucket-label">{contentTypeLabels[key] || key}</span>
                      <span className="analysis-bucket-value">{value} 条</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 互动分布：点赞/评论区间（供决策） */}
            {(displayStats?.like_buckets || displayStats?.comment_buckets) && (
              <section className="analysis-section analysis-engagement">
                <h3 className="analysis-section-title">📈 互动分布</h3>
                <div className="analysis-engagement-grid">
                  {displayStats.like_buckets && (
                    <div className="analysis-buckets-block">
                      <div className="analysis-buckets-title">点赞区间</div>
                      {Object.entries(displayStats.like_buckets).map(([range, count]) => (
                        <div key={range} className="analysis-bucket-row">
                          <span className="analysis-bucket-label">{range}</span>
                          <span className="analysis-bucket-value">{count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {displayStats.comment_buckets && (
                    <div className="analysis-buckets-block">
                      <div className="analysis-buckets-title">评论区间</div>
                      {Object.entries(displayStats.comment_buckets).map(([range, count]) => (
                        <div key={range} className="analysis-bucket-row">
                          <span className="analysis-bucket-label">{range}</span>
                          <span className="analysis-bucket-value">{count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* 平台分布 */}
            {Object.keys(displayDistribution).length > 0 && (
              <section className="analysis-section">
                <h3 className="analysis-section-title">平台分布</h3>
                <div className="chart-container">
                  <Pie data={pieData} options={chartOptions} />
                </div>
              </section>
            )}

            {/* 时间趋势 */}
            {Object.keys(displayTrends).length > 0 && (
              <section className="analysis-section">
                <h3 className="analysis-section-title">时间趋势</h3>
                <div className="chart-container">
                  <Line data={lineData} options={chartOptions} />
                </div>
              </section>
            )}

            {/* 热门作者 */}
            {displayTopAuthors.length > 0 && (
              <section className="analysis-section">
                <h3 className="analysis-section-title">热门作者 Top 10</h3>
                <div className="chart-container">
                  <Bar data={barData} options={chartOptions} />
                </div>
              </section>
            )}

            {/* 高互动帖子 Top 10（决策参考） */}
            {displayTopPosts.length > 0 && (
              <section className="analysis-section">
                <h3 className="analysis-section-title">🔥 高互动帖子 Top 10（按点赞）</h3>
                <div className="analysis-top-posts">
                  {displayTopPosts.map((post: any, idx: number) => (
                    <div key={post.post_id + post.platform} className="analysis-top-post-item">
                      <span className="analysis-top-post-rank">{idx + 1}</span>
                      <span className="analysis-top-post-title" title={post.title}>{(post.title || '无标题').slice(0, 36)}{(post.title && post.title.length > 36 ? '…' : '')}</span>
                      <span className="analysis-top-post-meta">{post.like_count} 赞 · {post.comment_count} 评</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 高频评论 + 评论者 */}
            {(displayFrequentComments.length > 0 || displayTopCommenters.length > 0) && (
              <section className="analysis-section analysis-comments-section">
                {displayFrequentComments.length > 0 && (
                  <div className="analysis-subsection">
                    <h3 className="analysis-section-title">💬 高频评论</h3>
                    <p className="analysis-section-desc">出现次数最多的评论内容及评论者</p>
                    <ul className="analysis-frequent-comments">
                      {displayFrequentComments.map((item, idx) => (
                        <li key={idx} className="analysis-frequent-comment-item">
                          <div className="analysis-frequent-comment-text">「{item.text.length > 50 ? item.text.slice(0, 50) + '…' : item.text}」</div>
                          <div className="analysis-frequent-comment-meta">
                            <span className="analysis-frequent-comment-count">出现 {item.count} 次</span>
                            {item.commenters.length > 0 && (
                              <span className="analysis-frequent-commenters">评论者：{item.commenters.join('、')}</span>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {displayTopCommenters.length > 0 && (
                  <div className="analysis-subsection">
                    <h3 className="analysis-section-title">👤 高频评论者</h3>
                    <p className="analysis-section-desc">评论条数最多的用户</p>
                    <ul className="analysis-top-commenters">
                      {displayTopCommenters.map((c, idx) => (
                        <li key={c.author_id + c.platform} className="analysis-top-commenter-item">
                          <span className="analysis-top-commenter-rank">{idx + 1}</span>
                          <span className="analysis-top-commenter-name">{c.author_name || c.author_id || '未知'}</span>
                          <span className="analysis-top-commenter-meta">{c.comment_count} 条评论</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )}

            {/* 平台详细统计 */}
            {displayStats && displayStats.platform_stats.length > 0 && (
              <section className="analysis-section analysis-platform-stats">
                <h3 className="analysis-section-title">平台详细统计</h3>
                <div className="platform-stats-grid">
                  {displayStats.platform_stats.map((platformStat) => {
                    const platformInfo = PLATFORMS.find(
                      (p) => p.value === platformStat.platform
                    );
                    return (
                      <div key={platformStat.platform} className="platform-stat-card">
                        <div className="platform-stat-header">
                          <span className="platform-stat-icon">
                            {platformInfo?.icon}
                          </span>
                          <span className="platform-stat-name">
                            {platformInfo?.label}
                          </span>
                        </div>
                        <div className="platform-stat-details">
                          <div>帖子: {platformStat.post_count}</div>
                          <div>评论: {platformStat.comment_count}</div>
                          <div>作者: {platformStat.author_count}</div>
                          <div>平均点赞: {platformStat.avg_likes.toFixed(1)}</div>
                          <div>平均评论: {platformStat.avg_comments.toFixed(1)}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </PixelModal>
  );
};
