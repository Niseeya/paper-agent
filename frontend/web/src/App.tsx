import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import LibraryPage from "./pages/LibraryPage";
import SearchPage from "./pages/SearchPage";
import ProjectPage from "./pages/ProjectPage";
import OutlinePage from "./pages/OutlinePage";
import EditorPage from "./pages/EditorPage";
import PolishPage from "./pages/PolishPage";
import CitationsPage from "./pages/CitationsPage";
import ExportPage from "./pages/ExportPage";
import ResearchToolsPage from "./pages/ResearchToolsPage";
import AdminPage from "./pages/AdminPage";
import AppLayout from "./layouts/AppLayout";

function Private({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated());

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true));
    if (useAuthStore.persist.hasHydrated()) setHydrated(true);
    return unsub;
  }, []);

  // 新开标签页时 persist 尚未读完 localStorage，不能立刻当成未登录
  if (!hydrated) return null;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <Private>
              <AppLayout />
            </Private>
          }
        >
          <Route index element={<HomePage />} />
          <Route path="library" element={<LibraryPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="tools/analysis" element={<ResearchToolsPage />} />
          <Route path="projects/:id" element={<ProjectPage />} />
          <Route path="projects/:id/search" element={<SearchPage />} />
          <Route path="projects/:id/outline" element={<OutlinePage />} />
          <Route path="projects/:id/editor" element={<EditorPage />} />
          <Route path="projects/:id/polish" element={<PolishPage />} />
          <Route path="projects/:id/citations" element={<CitationsPage />} />
          <Route path="projects/:id/export" element={<ExportPage />} />
          {/* 旧分析路径改走独立工具页 */}
          <Route path="projects/:id/analysis" element={<Navigate to="/tools/analysis" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
