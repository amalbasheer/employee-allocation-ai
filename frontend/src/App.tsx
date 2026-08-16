import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { Login } from './pages/auth/Login';
import { Register } from './pages/auth/Register';
import { OverviewDashboard } from './pages/admin/OverviewDashboard';
import { UserManagement } from './pages/admin/UserManagement';
import { WebinarManagement } from './pages/admin/WebinarManagement';
import { EmployeeDashboard } from './pages/employee/EmployeeDashboard';
import { StudentDashboard } from './pages/student/StudentDashboard';
import { Role } from './types';
import { ProjectAllocations } from './pages/admin/ProjectAllocations';

interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles?: Role[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user?.role && !allowedRoles.includes(user.role)) {
    const role = user.role.toUpperCase();
    if (role === 'ADMIN') return <Navigate to="/admin/overview" replace />;
    if (role === 'STUDENT' || role === 'INTERN') return <Navigate to="/student/dashboard" replace />;
    return <Navigate to="/employee/dashboard" replace />;
  }

  // Render children if passed as a wrapper, otherwise render Outlet for layout routes
  return children ? <>{children}</> : <Outlet />;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/register" element={<Register />} />
          

          {/* Protected Routes inside AppLayout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route
                path="/admin/overview"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <OverviewDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <UserManagement />
                  </ProtectedRoute>
                }
              />
              <Route 
                path="/admin/project-allocation" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <ProjectAllocations />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/webinars"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <WebinarManagement />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/employee/dashboard"
                element={
                  <ProtectedRoute allowedRoles={['EMPLOYEE']}>
                    <EmployeeDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/student/dashboard"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'INTERN']}>
                    <StudentDashboard />
                  </ProtectedRoute>
                }
              />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}