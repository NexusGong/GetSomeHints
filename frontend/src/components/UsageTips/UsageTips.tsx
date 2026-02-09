import React from 'react';
import './UsageTips.css';

export const UsageTips: React.FC = () => {
  return (
    <div className="usage-tips">
      <h3 className="usage-tips-title">💡 使用提示</h3>
      <div className="usage-tips-content">
        <div className="usage-tip-item">
          <span className="usage-tip-icon">1️⃣</span>
          <div className="usage-tip-text">
            <strong>输入关键词</strong>
            <p>在搜索框中输入你想要搜索的关键词，支持多个关键词用逗号分隔</p>
          </div>
        </div>
        <div className="usage-tip-item">
          <span className="usage-tip-icon">2️⃣</span>
          <div className="usage-tip-text">
            <strong>选择平台</strong>
            <p>点击下方平台按钮选择要搜索的平台，可以选择多个平台同时搜索</p>
          </div>
        </div>
        <div className="usage-tip-item">
          <span className="usage-tip-icon">3️⃣</span>
          <div className="usage-tip-text">
            <strong>开始搜索</strong>
            <p>点击"搜索"按钮开始搜索，系统会在选定的平台中查找相关内容</p>
          </div>
        </div>
        <div className="usage-tip-item">
          <span className="usage-tip-icon">4️⃣</span>
          <div className="usage-tip-text">
            <strong>查看结果</strong>
            <p>搜索完成后可以查看帖子详情、评论信息，还可以进行数据分析和筛选</p>
          </div>
        </div>
      </div>
    </div>
  );
};
