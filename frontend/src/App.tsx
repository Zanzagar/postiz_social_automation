import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { CreatePage } from "@/pages/CreatePage";
import { DraftsPage } from "@/pages/DraftsPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

// Placeholder pages — will be replaced by real implementations (Tasks 14-19)
function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-sage-700">{title}</h1>
        <p className="mt-2 text-muted-foreground">Coming soon</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="create" element={<CreatePage />} />
        <Route path="drafts" element={<DraftsPage />} />
        <Route path="calendar" element={<Placeholder title="Content Calendar" />} />
        <Route path="suggestions" element={<Placeholder title="Suggestions" />} />
        <Route path="health" element={<Placeholder title="System Health" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
