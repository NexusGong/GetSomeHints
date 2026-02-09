import React, { useEffect, useState } from 'react';
import { PixelModal } from '../PixelModal/PixelModal';
import { analysisApi } from '../../services/api';
import type { AnalysisStats, PlatformStats } from '../../types';
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
  Legend
);

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string | null;
}

export const AnalysisModal: React.FC<AnalysisModalProps> = ({
  isOpen,
  onClose,
  taskId,
}) => {
  const [stats, setStats] = useState<AnalysisStats | null>(null);
  const [distribution, setDistribution] = useState<Record<string, number>>({});
  const [trends, setTrends] = useState<Record<string, number>>({});
  const [topAuthors, setTopAuthors] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && taskId) {
      loadAnalysisData();
    }
  }, [isOpen, taskId]);

  const loadAnalysisData = async () => {
    if (!taskId) return;

    setLoading(true);
    try {
      const [statsData, distData, trendsData, authorsData] = await Promise.all([
        analysisApi.getStats(taskId),
        analysisApi.getDistribution(taskId),
        analysisApi.getTrends(taskId),
        analysisApi.getTopAuthors(taskId, 10),
      ]);

      setStats(statsData);
      setDistribution(distData);
      setTrends(trendsData);
      setTopAuthors(authorsData);
    } catch (error) {
      console.error('Failed to load analysis data:', error);
    } finally {
      setLoading(false);
    }
  };

  const pieData = {
    labels: Object.keys(distribution).map(
      (p) => PLATFORMS.find((pl) => pl.value === p)?.label || p
    ),
    datasets: [
      {
        data: Object.values(distribution),
        backgroundColor: Object.keys(distribution).map(
          (p) => PLATFORMS.find((pl) => pl.value === p)?.color || '#00ff00'
        ),
        borderColor: '#000000',
        borderWidth: 2,
      },
    ],
  };

  const lineData = {
    labels: Object.keys(trends).sort(),
    datasets: [
      {
        label: '发布数量',
        data: Object.keys(trends)
          .sort()
          .map((key) => trends[key]),
        borderColor: '#00ff00',
        backgroundColor: 'rgba(0, 255, 0, 0.1)',
        borderWidth: 2,
        fill: true,
      },
    ],
  };

  const barData = {
    labels: topAuthors.slice(0, 10).map((a) => a.author.author_name),
    datasets: [
      {
        label: '帖子数',
        data: topAuthors.slice(0, 10).map((a) => a.post_count),
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
      onClose={onClose}
      title="📊 数据分析"
      size="large"
    >
      <div className="analysis-modal-content">
        {loading ? (
          <div className="analysis-loading">加载中...</div>
        ) : (
          <>
            {/* 统计概览 */}
            {stats && (
              <div className="analysis-stats-overview">
                <div className="stat-card">
                  <div className="stat-value">{stats.total_posts}</div>
                  <div className="stat-label">总帖子数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.total_comments}</div>
                  <div className="stat-label">总评论数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.total_authors}</div>
                  <div className="stat-label">总作者数</div>
                </div>
              </div>
            )}

            {/* 平台分布 */}
            {Object.keys(distribution).length > 0 && (
              <div className="analysis-chart">
                <h3 className="analysis-chart-title">平台分布</h3>
                <div className="chart-container">
                  <Pie data={pieData} options={chartOptions} />
                </div>
              </div>
            )}

            {/* 时间趋势 */}
            {Object.keys(trends).length > 0 && (
              <div className="analysis-chart">
                <h3 className="analysis-chart-title">时间趋势</h3>
                <div className="chart-container">
                  <Line data={lineData} options={chartOptions} />
                </div>
              </div>
            )}

            {/* 热门作者 */}
            {topAuthors.length > 0 && (
              <div className="analysis-chart">
                <h3 className="analysis-chart-title">热门作者 Top 10</h3>
                <div className="chart-container">
                  <Bar data={barData} options={chartOptions} />
                </div>
              </div>
            )}

            {/* 平台详细统计 */}
            {stats && stats.platform_stats.length > 0 && (
              <div className="analysis-platform-stats">
                <h3 className="analysis-chart-title">平台详细统计</h3>
                <div className="platform-stats-grid">
                  {stats.platform_stats.map((platformStat) => {
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
              </div>
            )}
          </>
        )}
      </div>
    </PixelModal>
  );
};
