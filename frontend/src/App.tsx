import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={
          <ProtectedRoute><Dashboard /></ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}