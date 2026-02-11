import { useState } from 'react';
import { Sidebar } from './components/Sidebar/Sidebar';
import { HomePage } from './pages/HomePage/HomePage';
import { HistoryPage } from './pages/HistoryPage/HistoryPage';
import { LlmAnalysisPage } from './pages/LlmAnalysisPage/LlmAnalysisPage';
import './styles/index.css';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState<'home' | 'history' | 'llm'>('home');
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
        {currentPage === 'llm' && <LlmAnalysisPage />}
      </main>
    </div>
  );
}

export default App;
