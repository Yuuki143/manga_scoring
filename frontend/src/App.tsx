import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { authApi } from './services/api';
import type { PublisherInfo } from './types/api';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import TitleDetailPage from './pages/TitleDetailPage';
import GenreTrendPage from './pages/GenreTrendPage';
import AlertsPage from './pages/AlertsPage';

// Common components
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';

// ============================================================
// Auth Context
// ============================================================

interface AuthContextType {
  isAuthenticated: boolean;
  publisher: PublisherInfo | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [publisher, setPublisher] = useState<PublisherInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchPublisher = useCallback(async () => {
    try {
      const res = await authApi.getPublisherInfo();
      setPublisher(res.data);
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
      setPublisher(null);
      localStorage.removeItem('mmip_token');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('mmip_token');
    if (token) {
      fetchPublisher();
    } else {
      setLoading(false);
    }
  }, [fetchPublisher]);

  const login = useCallback(async (token: string) => {
    localStorage.setItem('mmip_token', token);
    await fetchPublisher();
  }, [fetchPublisher]);

  const logout = useCallback(() => {
    authApi.logout();
    setIsAuthenticated(false);
    setPublisher(null);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, publisher, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================
// Protected Route
// ============================================================

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="loading-container" style={{ height: '100vh' }}>
        <div className="loading-spinner" />
        <span className="loading-text">読み込み中...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// ============================================================
// App Shell (layout with sidebar + header)
// ============================================================

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <Header />
        <main className="page-content fade-in">
          {children}
        </main>
      </div>
    </div>
  );
}

// ============================================================
// Router
// ============================================================

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/title/:id"
        element={
          <ProtectedRoute>
            <AppShell>
              <TitleDetailPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/genres"
        element={
          <ProtectedRoute>
            <AppShell>
              <GenreTrendPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/alerts"
        element={
          <ProtectedRoute>
            <AppShell>
              <AlertsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// ============================================================
// Root App
// ============================================================

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
