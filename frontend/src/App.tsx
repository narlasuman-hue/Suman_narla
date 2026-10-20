import React from 'react';
import { BrowserRouter as Router, Navigate, Routes, Route, useParams } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import SearchPage from './pages/SearchPage';
import AssetDetail from './pages/AssetDetail';
import LineagePage from './pages/LineagePage';
import ReportsPage from './pages/ReportsPage';
import LifecyclePage from './pages/LifecyclePage';
import QueryAnalysisPage from './pages/QueryAnalysisPage';
import JobsPage from './pages/JobsPage';
import JobDetail from './pages/JobDetail';
import JobLineagePage from './pages/JobLineagePage';
import './styles/globals.css';

/** Old Mainframe job links now open the all-platform job page. */
const MainframeJobRedirect: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/jobs/mainframe/${id}`} replace />;
};

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
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:platformKey/:id" element={<JobDetail />} />
          <Route path="/mainframe" element={<Navigate to="/jobs?platform=mainframe" replace />} />
          <Route path="/mainframe/jobs/:id" element={<MainframeJobRedirect />} />
          <Route path="/job-lineage" element={<JobLineagePage />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
