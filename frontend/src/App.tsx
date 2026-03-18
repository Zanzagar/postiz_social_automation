import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { CreatePage } from "@/pages/CreatePage";
import { DraftsPage } from "@/pages/DraftsPage";
import { CalendarPage } from "@/pages/CalendarPage";
import { SuggestionsPage } from "@/pages/SuggestionsPage";
import { HealthPage } from "@/pages/HealthPage";
import { TemplatesPage } from "@/pages/TemplatesPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

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
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="suggestions" element={<SuggestionsPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="health" element={<HealthPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
