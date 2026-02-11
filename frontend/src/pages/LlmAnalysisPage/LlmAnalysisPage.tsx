import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LlmAnalysisCard } from '../../components/LlmAnalysisCard/LlmAnalysisCard';
import { PixelButton } from '../../components/PixelButton/PixelButton';
import { LlmAnalysisModal } from '../../components/LlmAnalysisModal/LlmAnalysisModal';
import { LlmAnalysisDetailModal } from '../../components/LlmAnalysisDetailModal/LlmAnalysisDetailModal';
import { useLlmAnalysisStore, type LlmAnalysisRecord } from '../../stores/llmAnalysisStore';
import '../HistoryPage/HistoryPage.css';
import './LlmAnalysisPage.css';

export const LlmAnalysisPage: React.FC = () => {
  const { records, deleteRecord, deleteRecords, clearAll } = useLlmAnalysisStore();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedRecord, setSelectedRecord] = useState<LlmAnalysisRecord | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'name'>('newest');

  const filteredRecords = useMemo(() => {
    let list = records.filter((record) => {
      const matchKeyword = !searchKeyword.trim() ||
        record.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        record.model.toLowerCase().includes(searchKeyword.toLowerCase());
      return matchKeyword;
    });
    if (sortBy === 'oldest') {
      list = [...list].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
    } else if (sortBy === 'name') {
      list = [...list].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
    }
    return list;
  }, [records, searchKeyword, sortBy]);

  const handleSelectRecord = (id: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredRecords.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredRecords.map((r) => r.id)));
    }
  };

  const handleDeleteRecord = (id: string) => {
    deleteRecord(id);
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
  };

  const handleDeleteSelected = () => {
    if (selectedIds.size === 0) return;
    if (window.confirm(`确定要删除选中的 ${selectedIds.size} 条分析记录吗？`)) {
      deleteRecords(Array.from(selectedIds));
      setSelectedIds(new Set());
    }
  };

  const handleViewDetail = (record: LlmAnalysisRecord) => {
    setSelectedRecord(record);
    setIsDetailModalOpen(true);
  };

  const handleClearAll = () => {
    if (records.length === 0) return;
    if (window.confirm(`确定要清空全部 ${records.length} 条分析记录吗？此操作不可恢复。`)) {
      clearAll();
      setSelectedIds(new Set());
    }
  };

  const selectedRecords = useMemo(
    () => filteredRecords.filter((r) => selectedIds.has(r.id)),
    [filteredRecords, selectedIds]
  );

  return (
    <div className="history-page">
      <div className="history-page-header">
        <div className="history-page-header-title">
          <h1>大模型分析</h1>
          <p className="history-page-subtitle">查看和管理潜在卖家/买家分析结果</p>
        </div>
        <div className="history-page-header-actions">
          <PixelButton onClick={() => setIsNewModalOpen(true)} variant="primary" size="small">
            新建分析
          </PixelButton>
          {records.length > 0 && (
            <PixelButton onClick={handleClearAll} variant="danger" size="small">
              清空全部
            </PixelButton>
          )}
        </div>
      </div>

      <div className="history-page-controls">
        <div className="history-page-filters">
          <input
            type="text"
            className="history-search-input"
            placeholder="搜索名称或模型..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
          />
          <div className="history-sort-group">
            <label className="history-sort-label">排序:</label>
            <select
              className="history-sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'newest' | 'oldest' | 'name')}
            >
              <option value="newest">最新优先</option>
              <option value="oldest">最早优先</option>
              <option value="name">名称 A-Z</option>
            </select>
          </div>
        </div>

        {selectedIds.size > 0 && (
          <div className="history-page-batch-actions">
            <span className="batch-action-count">已选择 {selectedIds.size} 项</span>
            <PixelButton
              onClick={handleSelectAll}
              variant="secondary"
              size="small"
            >
              {selectedIds.size === filteredRecords.length ? '取消全选' : '全选'}
            </PixelButton>
            <PixelButton
              onClick={handleDeleteSelected}
              variant="danger"
              size="small"
            >
              删除选中
            </PixelButton>
          </div>
        )}
      </div>

      <div className="history-page-content">
        {filteredRecords.length === 0 ? (
          <div className="history-empty">
            <div className="history-empty-icon">🤖</div>
            <p className="history-empty-text">
              {records.length === 0
                ? '还没有分析结果'
                : '没有找到匹配的记录'}
            </p>
            {records.length === 0 && (
              <p className="llm-analysis-empty-hint">点击「新建分析」或从首页/历史详情使用「大模型分析」运行后，结果会保存到这里</p>
            )}
          </div>
        ) : (
          <div className="history-list">
            {filteredRecords.map((record) => (
              <LlmAnalysisCard
                key={record.id}
                record={record}
                isSelected={selectedIds.has(record.id)}
                onSelect={handleSelectRecord}
                onClick={() => handleViewDetail(record)}
                onDelete={handleDeleteRecord}
              />
            ))}
          </div>
        )}
      </div>

      <LlmAnalysisModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
      />

      <LlmAnalysisDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedRecord(null);
        }}
        record={selectedRecord}
      />
    </div>
  );
};
