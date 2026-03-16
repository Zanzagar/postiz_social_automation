import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";

function DashboardPlaceholder() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-cream-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-sage-700">Gita Valley</h1>
        <p className="mt-2 text-terracotta-500">Content Management System</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPlaceholder />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
