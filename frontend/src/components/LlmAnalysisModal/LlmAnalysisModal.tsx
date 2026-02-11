import React, { useEffect, useRef, useState } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { PixelButton } from '../PixelButton/PixelButton';
import { analysisApi } from '../../services/api';
import { useHistoryStore } from '../../stores/historyStore';
import { useLlmAnalysisStore } from '../../stores/llmAnalysisStore';
import { PLATFORMS } from '../../utils/constants';
import type { LlmLeadsResult, LlmScenario, UnifiedPost } from '../../types';
import './LlmAnalysisModal.css';

const MODEL_OPTIONS = [
  { value: 'deepseek-chat', label: 'DeepSeek' },
];
const DEFAULT_SCENE_ID = 'sell_buy';

interface LogLine {
  time: string;
  text: string;
  level?: 'info' | 'success' | 'error';
}

interface LlmAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** 从首页/历史详情带入的当前结果，可直接用于分析 */
  initialPosts?: UnifiedPost[] | null;
  initialTaskId?: string | null;
}

export const LlmAnalysisModal: React.FC<LlmAnalysisModalProps> = ({
  isOpen,
  onClose,
  initialPosts = null,
  initialTaskId = null,
}) => {
  const { records: historyRecords } = useHistoryStore();
  const addRecord = useLlmAnalysisStore((s) => s.addRecord);

  const [scenarios, setScenarios] = useState<LlmScenario[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string>('');
  const [useCurrentResult, setUseCurrentResult] = useState(false);
  const [scene, setScene] = useState<string>(DEFAULT_SCENE_ID);
  const [model, setModel] = useState<string>('deepseek-chat');
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<LlmLeadsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const currentScenario = scenarios.find((s) => s.id === scene) || scenarios[0];
  const sellerLabel = currentScenario?.seller_label ?? '潜在卖家';
  const buyerLabel = currentScenario?.buyer_label ?? '潜在买家';

  const hasDataSourceSelected = (initialPosts?.length && useCurrentResult) || !!selectedHistoryId;

  const appendLog = (text: string, level: LogLine['level'] = 'info') => {
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogLines((prev) => [...prev, { time, text, level }]);
  };

  useEffect(() => {
    if (isOpen) {
      setLogLines([]);
      setResult(null);
      setError(null);
      setSavedId(null);
      setSelectedHistoryId('');
      setUseCurrentResult(false);
      analysisApi.getLlmScenarios().then(setScenarios).catch(() => setScenarios([]));
    }
  }, [isOpen]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logLines]);

  const getPostsForAnalysis = (): { posts: UnifiedPost[]; taskId?: string } | null => {
    if (useCurrentResult && initialPosts?.length) {
      return { posts: initialPosts, taskId: initialTaskId ?? undefined };
    }
    if (selectedHistoryId) {
      const record = historyRecords.find((r) => r.id === selectedHistoryId);
      if (record?.results?.length) return { posts: record.results };
    }
    return null;
  };

  const canStart = getPostsForAnalysis() !== null && !running;

  const clearDataSource = () => {
    setSelectedHistoryId('');
    setUseCurrentResult(false);
  };

  const handleStart = async () => {
    const source = getPostsForAnalysis();
    if (!source) return;
    setRunning(true);
    setError(null);
    setResult(null);
    setLogLines([]);

    appendLog('准备数据…');
    await new Promise((r) => setTimeout(r, 300));
    appendLog(`已加载 ${source.posts.length} 条帖子与评论`, 'info');
    appendLog('正在调用大模型…');
    try {
      const res = await analysisApi.runLlmLeadsAnalysis({
        posts: source.posts,
        taskId: source.taskId,
        model,
        scene: scene || undefined,
      });
      appendLog('解析结果…');
      await new Promise((r) => setTimeout(r, 200));
      appendLog('分析完成', 'success');
      setResult(res);
      const name = `分析 ${new Date().toLocaleString('zh-CN')}`;
      addRecord({
        name,
        model,
        postsCount: source.posts.length,
        result: res,
        scene,
        sceneName: currentScenario?.name,
        sellerLabel,
        buyerLabel,
      });
      setSavedId(name);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? '请求失败';
      const str = Array.isArray(msg) ? msg.join(' ') : String(msg);
      appendLog(str, 'error');
      setError(str);
    } finally {
      setRunning(false);
    }
  };

  const intentLabel: Record<string, string> = {
    explicit_inquiry: '明确询价/求购',
    interested: '感兴趣/羡慕',
    sharing_only: '仅分享/炫耀',
    unknown: '无法判断',
  };

  /** 涉及联系方式时展示完整「昵称（平台号）」 */
  const formatAuthorDisplay = (name: string, id: string) =>
    name && id ? `${name}（${id}）` : (name || id || '—');

  return (
    <PixelModal isOpen={isOpen} onClose={onClose} title="大模型分析" size="large">
      <div className="llm-analysis-modal-content">
        {/* 第一步：选择数据来源（列表） */}
        {!hasDataSourceSelected ? (
          <section className="llm-analysis-select-source">
            <h3 className="llm-analysis-select-source-title">选择数据来源</h3>
            <p className="llm-analysis-select-source-desc">选择一条历史记录作为分析数据，或使用当前搜索结果（从首页/历史详情打开时可见）。</p>
            {historyRecords.length === 0 && !initialPosts?.length ? (
              <div className="llm-analysis-no-data">暂无数据，请先完成一次搜索后再来新建分析。</div>
            ) : (
              <ul className="llm-analysis-source-list">
                {initialPosts && initialPosts.length > 0 && (
                  <li>
                    <button
                      type="button"
                      className="llm-analysis-source-item"
                      onClick={() => { setUseCurrentResult(true); setSelectedHistoryId(''); }}
                    >
                      <span className="llm-analysis-source-item-title">当前搜索结果</span>
                      <span className="llm-analysis-source-item-meta">{initialPosts.length} 条</span>
                    </button>
                  </li>
                )}
                {historyRecords.slice(0, 80).map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      className="llm-analysis-source-item"
                      onClick={() => { setSelectedHistoryId(r.id); setUseCurrentResult(false); }}
                    >
                      <span className="llm-analysis-source-item-title">「{r.keyword}」</span>
                      <span className="llm-analysis-source-item-meta">{r.results.length} 条 · {new Date(r.createdAt).toLocaleString('zh-CN')}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : (
          <>
            {/* 第二步：已选数据源 + 模型 + 开始 */}
            <section className="llm-analysis-form">
              <div className="llm-analysis-field llm-analysis-selected-source">
                <label>数据来源</label>
                <div className="llm-analysis-selected-source-value">
                  {useCurrentResult && initialPosts?.length
                    ? `当前搜索结果（${initialPosts.length} 条）`
                    : (() => {
                        const r = historyRecords.find((x) => x.id === selectedHistoryId);
                        return r ? `「${r.keyword}」${r.results.length} 条` : '';
                      })()}
                  <button type="button" className="llm-analysis-change-source" onClick={clearDataSource} disabled={running}>
                    更换数据来源
                  </button>
                </div>
              </div>
              <div className="llm-analysis-field">
                <label>分析场景</label>
                <select className="llm-analysis-select" value={scene} onChange={(e) => setScene(e.target.value)} disabled={running}>
                  {(scenarios.length ? scenarios : [{ id: DEFAULT_SCENE_ID, name: '潜在买家/卖家', seller_label: '潜在卖家', buyer_label: '潜在买家' }]).map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div className="llm-analysis-field">
                <label>模型</label>
                <select className="llm-analysis-select" value={model} onChange={(e) => setModel(e.target.value)} disabled={running}>
                  {MODEL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="llm-analysis-actions">
                <PixelButton onClick={handleStart} variant="primary" disabled={!canStart}>
                  {running ? '分析中…' : '开始分析'}
                </PixelButton>
              </div>
            </section>
          </>
        )}

        {/* 已选数据源后才显示日志与结果 */}
        {hasDataSourceSelected && (
          <>
        {/* 实时日志 */}
        <section className="llm-analysis-log-section">
          <h3 className="llm-analysis-log-title">运行日志</h3>
          <div className="llm-analysis-log-box">
            {logLines.length === 0 ? (
              <div className="llm-analysis-log-empty">等待开始…</div>
            ) : (
              logLines.map((line, i) => (
                <div key={i} className={`llm-analysis-log-line log-${line.level ?? 'info'}`}>
                  <span className="llm-analysis-log-time">[{line.time}]</span>
                  <span className="llm-analysis-log-text">{line.text}</span>
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </section>

        {/* 错误 */}
        {error && (
          <div className="llm-analysis-error">{error}</div>
        )}

        {/* 结果 */}
        {result && (
          <section className="llm-analysis-result-section">
            {savedId && <p className="llm-analysis-saved-hint">已保存到侧边栏「大模型分析」</p>}
            {result.analysis_summary && <p className="llm-analysis-summary">{result.analysis_summary}</p>}
            {result.potential_sellers.length > 0 && (
              <div className="llm-analysis-block">
                <h4>{sellerLabel}</h4>
                <ul className="llm-analysis-list">
                  {result.potential_sellers.map((s, idx) => (
                    <li key={`s-${idx}`}>
                      <span className="llm-analysis-item-name">{formatAuthorDisplay(s.author_name, s.author_id)}</span>
                      <span className="llm-analysis-item-platform">{PLATFORMS.find((p) => p.value === s.platform)?.label ?? s.platform}</span>
                      <span className="llm-analysis-item-reason">{s.reason}</span>
                      {s.contacts.length > 0 && <span className="llm-analysis-item-contacts">联系方式: {s.contacts.join(' / ')}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.potential_buyers.length > 0 && (
              <div className="llm-analysis-block">
                <h4>{buyerLabel}</h4>
                <ul className="llm-analysis-list">
                  {result.potential_buyers.map((b, idx) => (
                    <li key={`b-${idx}`}>
                      <span className="llm-analysis-item-name">{formatAuthorDisplay(b.author_name, b.author_id)}</span>
                      <span className="llm-analysis-item-platform">{PLATFORMS.find((p) => p.value === b.platform)?.label ?? b.platform}</span>
                      <span className="llm-analysis-intent">{intentLabel[b.intent_level] ?? b.intent_level}</span>
                      <span className="llm-analysis-item-reason">{b.reason}</span>
                      {b.contacts.length > 0 && <span className="llm-analysis-item-contacts">联系方式: {b.contacts.join(' / ')}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.contacts_summary.length > 0 && (
              <div className="llm-analysis-block">
                <h4>联系方式汇总</h4>
                <ul className="llm-analysis-list llm-analysis-contacts">
                  {result.contacts_summary.map((c, idx) => (
                    <li key={`c-${idx}`}>
                      <span className="llm-analysis-contact-author">{c.author_id || '—'}</span> <span>{c.platform}</span> <span>{c.contact_type}: {c.value}</span>
                      {c.source && <span className="llm-analysis-item-source">（{c.source}）</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.potential_sellers.length === 0 && result.potential_buyers.length === 0 && !result.analysis_summary && (
              <p className="llm-analysis-no-result">本次未识别到{sellerLabel}或{buyerLabel}。</p>
            )}
          </section>
        )}
          </>
        )}
      </div>
    </PixelModal>
  );
};
