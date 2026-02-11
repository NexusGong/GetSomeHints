import React from 'react';
import './Sidebar.css';

interface SidebarProps {
  currentPage: 'home' | 'history' | 'llm';
  onPageChange: (page: 'home' | 'history' | 'llm') => void;
  isCollapsed: boolean;
  onToggleCollapse: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentPage, 
  onPageChange,
  isCollapsed,
  onToggleCollapse,
}) => {
  const toggleSidebar = () => {
    onToggleCollapse(!isCollapsed);
  };

  return (
    <div className={`sidebar ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-header">
        {!isCollapsed && <h2 className="sidebar-title">GetSomeHints</h2>}
        <button
          className="sidebar-toggle"
          onClick={toggleSidebar}
          aria-label={isCollapsed ? '展开菜单' : '收起菜单'}
        >
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>
      
      <nav className="sidebar-nav">
        <button
          className={`sidebar-item ${currentPage === 'home' ? 'active' : ''}`}
          onClick={() => onPageChange('home')}
        >
          <span className="sidebar-icon">🔍</span>
          {!isCollapsed && <span className="sidebar-label">搜索</span>}
        </button>
        
        <button
          className={`sidebar-item ${currentPage === 'history' ? 'active' : ''}`}
          onClick={() => onPageChange('history')}
        >
          <span className="sidebar-icon">📚</span>
          {!isCollapsed && <span className="sidebar-label">历史爬取</span>}
        </button>

        <button
          className={`sidebar-item ${currentPage === 'llm' ? 'active' : ''}`}
          onClick={() => onPageChange('llm')}
        >
          <span className="sidebar-icon">🤖</span>
          {!isCollapsed && <span className="sidebar-label">大模型分析</span>}
        </button>
      </nav>
    </div>
  );
};
