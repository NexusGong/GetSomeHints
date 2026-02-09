import React, { useState, useMemo } from 'react';
import { HistoryCard } from '../../components/HistoryCard/HistoryCard';
import { PixelButton } from '../../components/PixelButton/PixelButton';
import { ExportMenu } from '../../components/ExportMenu/ExportMenu';
import { HistoryDetailModal } from '../../components/HistoryDetailModal/HistoryDetailModal';
import { useHistoryStore, type HistoryRecord } from '../../stores/historyStore';
import { exportToJSON } from '../../utils/exportUtils';
import './HistoryPage.css';

export const HistoryPage: React.FC = () => {
  const { records, deleteRecord, deleteRecords, getRecord, clearAll } = useHistoryStore();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedRecord, setSelectedRecord] = useState<HistoryRecord | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'all' | 'completed' | 'stopped' | 'failed'>('all');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [historySort, setHistorySort] = useState<'newest' | 'oldest' | 'keyword'>('newest');

  // 筛选、搜索、排序
  const filteredRecords = useMemo(() => {
    let list = records.filter((record) => {
      const matchStatus = filterStatus === 'all' || record.status === filterStatus;
      const matchKeyword = !searchKeyword.trim() ||
        record.keyword.toLowerCase().includes(searchKeyword.toLowerCase());
      return matchStatus && matchKeyword;
    });
    if (historySort === 'oldest') {
      list = [...list].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
    } else if (historySort === 'keyword') {
      list = [...list].sort((a, b) => a.keyword.localeCompare(b.keyword, 'zh-CN'));
    }
    // 'newest' 已是 addRecord 时的顺序（新在前），无需再排
    return list;
  }, [records, filterStatus, searchKeyword, historySort]);

  const handleSelectRecord = (id: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
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
    if (window.confirm(`确定要删除选中的 ${selectedIds.size} 条历史记录吗？`)) {
      deleteRecords(Array.from(selectedIds));
      setSelectedIds(new Set());
    }
  };

  const handleViewDetail = (record: HistoryRecord) => {
    setSelectedRecord(record);
    setIsDetailModalOpen(true);
  };

  const handleExportSelected = () => {
    if (selectedIds.size === 0) return;
    const selectedRecords = filteredRecords.filter((r) => selectedIds.has(r.id));
    const allPosts = selectedRecords.flatMap((r) => r.results);
    exportToJSON(allPosts, `历史记录_${new Date().toISOString().split('T')[0]}`);
  };

  const handleClearAll = () => {
    if (records.length === 0) return;
    if (window.confirm(`确定要清空全部 ${records.length} 条历史记录吗？此操作不可恢复。`)) {
      clearAll();
      setSelectedIds(new Set());
    }
  };

  const selectedRecords = useMemo(() => {
    return filteredRecords.filter((r) => selectedIds.has(r.id));
  }, [filteredRecords, selectedIds]);

  return (
    <div className="history-page">
      <div className="history-page-header">
        <div className="history-page-header-title">
          <h1>历史爬取</h1>
          <p className="history-page-subtitle">查看和管理之前的爬取记录</p>
        </div>
        {records.length > 0 && (
          <PixelButton onClick={handleClearAll} variant="danger" size="small">
            清空全部
          </PixelButton>
        )}
      </div>

      <div className="history-page-controls">
        <div className="history-page-filters">
          <input
            type="text"
            className="history-search-input"
            placeholder="搜索关键词..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
          />
          <div className="history-sort-group">
            <label className="history-sort-label">排序:</label>
            <select
              className="history-sort-select"
              value={historySort}
              onChange={(e) => setHistorySort(e.target.value as 'newest' | 'oldest' | 'keyword')}
            >
              <option value="newest">最新优先</option>
              <option value="oldest">最早优先</option>
              <option value="keyword">关键词 A-Z</option>
            </select>
          </div>
          <div className="history-status-filters">
            <button
              className={`status-filter-btn ${filterStatus === 'all' ? 'active' : ''}`}
              onClick={() => setFilterStatus('all')}
            >
              全部
            </button>
            <button
              className={`status-filter-btn ${filterStatus === 'completed' ? 'active' : ''}`}
              onClick={() => setFilterStatus('completed')}
            >
              已完成
            </button>
            <button
              className={`status-filter-btn ${filterStatus === 'stopped' ? 'active' : ''}`}
              onClick={() => setFilterStatus('stopped')}
            >
              已停止
            </button>
            <button
              className={`status-filter-btn ${filterStatus === 'failed' ? 'active' : ''}`}
              onClick={() => setFilterStatus('failed')}
            >
              失败
            </button>
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
            <ExportMenu
              posts={selectedRecords.flatMap((r) => r.results)}
              totalCount={selectedRecords.flatMap((r) => r.results).length}
              filteredCount={selectedRecords.flatMap((r) => r.results).length}
            />
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
            <div className="history-empty-icon">📚</div>
            <p className="history-empty-text">
              {records.length === 0
                ? '还没有历史记录'
                : '没有找到匹配的记录'}
            </p>
          </div>
        ) : (
          <div className="history-list">
            {filteredRecords.map((record) => (
              <HistoryCard
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

      <HistoryDetailModal
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
