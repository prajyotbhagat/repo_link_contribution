import { HashRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Dashboard from './pages/Dashboard';
import RepoDetail from './pages/RepoDetail';

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/repo/:id" element={<RepoDetail />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
}
