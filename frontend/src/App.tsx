import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { Login } from './pages/auth/Login';
import { ActivateAccount } from './pages/auth/ActivateAccount';
import DashboardOverview from './pages/admin/OverviewDashboard';
import { UserManagement } from './pages/admin/UserManagement';
import { TrainingManagement } from './pages/admin/WebinarManagement';
import { EmployeeDashboard } from './pages/employee/EmployeeDashboard';
import StudentDashboard from './pages/student/StudentDashboard';
import { Role } from './types';
import { ProjectAllocation } from './pages/admin/ProjectAllocations';
import { EmployeeAvailabilityPage } from './pages/employee/EmployeeAvailability';
import { TrainingAllocationsDashboard } from './pages/employee/TrainingEngagement';

interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles?: Role[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, role: contextRole, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Extract role and normalize to uppercase for robust case-insensitive matching
  const activeRole = (contextRole || user?.role || (user as any)?.user_metadata?.role || '')?.toUpperCase();

  if (allowedRoles && activeRole) {
    const normalizedAllowed = allowedRoles.map((r) => r.toUpperCase());

    if (!normalizedAllowed.includes(activeRole)) {
      if (activeRole === 'ADMIN') return <Navigate to="/admin/overview" replace />;
      if (activeRole === 'STUDENT' || activeRole === 'INTERN') return <Navigate to="/student/dashboard" replace />;
      return <Navigate to="/employee/dashboard" replace />;
    }
  }

  return children ? <>{children}</> : <Outlet />;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/activate" element={<ActivateAccount />} />

          {/* Protected Routes inside AppLayout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route
                path="/admin/overview"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <DashboardOverview />
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
                path="/admin/allocations" 
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <ProjectAllocation />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/webinars"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <TrainingManagement />
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
                path="/employee/engagement"
                element={
                  <ProtectedRoute allowedRoles={['EMPLOYEE']}>
                    <TrainingAllocationsDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/employee/availability"
                element={
                  <ProtectedRoute allowedRoles={['EMPLOYEE']}>
                    <EmployeeAvailabilityPage />
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