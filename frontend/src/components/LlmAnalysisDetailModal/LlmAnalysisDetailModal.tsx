import React from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import type { LlmAnalysisRecord } from '../../stores/llmAnalysisStore';
import { PLATFORMS } from '../../utils/constants';
import { exportLlmAnalysisToCSV, exportLlmAnalysisToJSON } from '../../utils/exportUtils';
import './LlmAnalysisDetailModal.css';

const INTENT_LABEL: Record<string, string> = {
  explicit_inquiry: '明确询价/求购',
  interested: '感兴趣/羡慕',
  sharing_only: '仅分享/炫耀',
  unknown: '无法判断',
};

interface LlmAnalysisDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  record: LlmAnalysisRecord | null;
}

export const LlmAnalysisDetailModal: React.FC<LlmAnalysisDetailModalProps> = ({
  isOpen,
  onClose,
  record,
}) => {
  if (!record) return null;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const { result } = record;
  const sellerLabel = record.sellerLabel ?? '潜在卖家';
  const buyerLabel = record.buyerLabel ?? '潜在买家';

  /** 涉及联系方式时展示完整「昵称（平台号）」 */
  const formatAuthorDisplay = (name: string, id: string) =>
    name && id ? `${name}（${id}）` : (name || id || '—');

  const handleExport = (format: 'csv' | 'json') => {
    const baseName = record.name.replace(/[/\\?*:"<>|]/g, '_').slice(0, 50) || 'llm_analysis';
    if (format === 'csv') exportLlmAnalysisToCSV([record], baseName);
    else exportLlmAnalysisToJSON([record], baseName);
  };

  return (
    <PixelModal
      isOpen={isOpen}
      onClose={onClose}
      title={record.name}
      size="large"
    >
      <div className="llm-detail-content">
        <div className="llm-detail-header">
          <div className="llm-detail-info">
            <div className="llm-detail-info-item">
              <span className="info-label">模型:</span>
              <span className="info-value">{record.model}</span>
            </div>
            <div className="llm-detail-info-item">
              <span className="info-label">创建时间:</span>
              <span className="info-value">{formatDate(record.createdAt)}</span>
            </div>
            <div className="llm-detail-info-item">
              <span className="info-label">分析数据量:</span>
              <span className="info-value">{record.postsCount} 条</span>
            </div>
            {record.sceneName && (
              <div className="llm-detail-info-item">
                <span className="info-label">分析场景:</span>
                <span className="info-value">{record.sceneName}</span>
              </div>
            )}
          </div>
          <div className="llm-detail-export">
            <button type="button" className="llm-detail-export-btn" onClick={() => handleExport('csv')}>
              📊 导出 CSV
            </button>
            <button type="button" className="llm-detail-export-btn" onClick={() => handleExport('json')}>
              📄 导出 JSON
            </button>
          </div>
        </div>

        <div className="llm-detail-results">
          {result.analysis_summary && (
            <div className="llm-detail-block">
              <h4 className="llm-detail-block-title">分析摘要</h4>
              <p className="llm-detail-summary">{result.analysis_summary}</p>
            </div>
          )}

          {result.potential_sellers.length > 0 && (
            <div className="llm-detail-block">
              <h4 className="llm-detail-block-title">{sellerLabel}</h4>
              <ul className="llm-detail-list">
                {result.potential_sellers.map((s, idx) => (
                  <li key={`s-${idx}`} className="llm-detail-item">
                    <span className="llm-detail-item-name">{formatAuthorDisplay(s.author_name, s.author_id)}</span>
                    <span className="llm-detail-item-platform">{PLATFORMS.find((p) => p.value === s.platform)?.label ?? s.platform}</span>
                    <span className="llm-detail-item-reason">{s.reason}</span>
                    {s.contacts.length > 0 && (
                      <span className="llm-detail-item-contacts">联系方式: {s.contacts.join(' / ')}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.potential_buyers.length > 0 && (
            <div className="llm-detail-block">
              <h4 className="llm-detail-block-title">{buyerLabel}</h4>
              <ul className="llm-detail-list">
                {result.potential_buyers.map((b, idx) => (
                  <li key={`b-${idx}`} className="llm-detail-item">
                    <span className="llm-detail-item-name">{formatAuthorDisplay(b.author_name, b.author_id)}</span>
                    <span className="llm-detail-item-platform">{PLATFORMS.find((p) => p.value === b.platform)?.label ?? b.platform}</span>
                    <span className="llm-detail-item-intent">{INTENT_LABEL[b.intent_level] ?? b.intent_level}</span>
                    <span className="llm-detail-item-reason">{b.reason}</span>
                    {b.contacts.length > 0 && (
                      <span className="llm-detail-item-contacts">联系方式: {b.contacts.join(' / ')}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.contacts_summary.length > 0 && (
            <div className="llm-detail-block">
              <h4 className="llm-detail-block-title">联系方式汇总</h4>
              <ul className="llm-detail-list llm-detail-contacts">
                {result.contacts_summary.map((c, idx) => (
                  <li key={`c-${idx}`} className="llm-detail-item">
                    <span className="llm-detail-contact-author">{c.author_id || '—'}</span>
                    <span>{c.platform}</span>
                    <span>{c.contact_type}: {c.value}</span>
                    {c.source && <span className="llm-detail-item-source">（{c.source}）</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.potential_sellers.length === 0 &&
            result.potential_buyers.length === 0 &&
            !result.analysis_summary && (
              <p className="llm-detail-empty">本次未识别到{sellerLabel}或{buyerLabel}。</p>
            )}
        </div>
      </div>
    </PixelModal>
  );
};
