import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar/Sidebar';
import { HomePage } from './pages/HomePage/HomePage';
import { HistoryPage } from './pages/HistoryPage/HistoryPage';
import './styles/index.css';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState<'home' | 'history'>('home');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="app-container">
      <Sidebar 
        currentPage={currentPage} 
        onPageChange={setCurrentPage}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={setIsSidebarCollapsed}
      />
      <main className={`app-main ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {currentPage === 'home' && <HomePage />}
        {currentPage === 'history' && <HistoryPage />}
      </main>
    </div>
  );
}

export default App;
