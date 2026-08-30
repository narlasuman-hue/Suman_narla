import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import SearchPage from './pages/SearchPage';
import AssetDetail from './pages/AssetDetail';
import LineagePage from './pages/LineagePage';
import ReportsPage from './pages/ReportsPage';
import LifecyclePage from './pages/LifecyclePage';
import QueryAnalysisPage from './pages/QueryAnalysisPage';
import './styles/globals.css';

const App: React.FC = () => {
  return (
    <Router>
      <Toaster position="top-right" />
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/tables/:id" element={<AssetDetail assetType="table" />} />
          <Route path="/databases/:id" element={<AssetDetail assetType="database" />} />
          <Route path="/lineage/:id" element={<LineagePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/lifecycle" element={<LifecyclePage />} />
          <Route path="/analysis" element={<QueryAnalysisPage />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
