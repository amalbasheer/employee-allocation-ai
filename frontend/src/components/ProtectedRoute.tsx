import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { user, role: contextRole, isAuthenticated } = useAuth();
  const location = useLocation();

  // 1. Redirect to login if unauthenticated
  if (!isAuthenticated && !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 2. Extract role safely (Context -> user.role -> user_metadata.role)
  const userMetadata = (user as any)?.user_metadata;
  const activeRole = (contextRole || user?.role || userMetadata?.role || '').toString().toUpperCase();

  // 3. Case-insensitive role verification & smart redirect
  if (allowedRoles && allowedRoles.length > 0) {
    const hasAccess = allowedRoles.some((role) => role.toUpperCase() === activeRole);

    if (!hasAccess) {
      if (activeRole === 'ADMIN') return <Navigate to="/admin/overview" replace />;
      if (activeRole === 'EMPLOYEE') return <Navigate to="/employee/dashboard" replace />;
      if (activeRole === 'STUDENT' || activeRole === 'INTERN') return <Navigate to="/student/dashboard" replace />;
      return <Navigate to="/login" replace />;
    }
  }

  // 4. Support both explicit wrapper components and nested <Outlet /> routes
  return children ? <>{children}</> : <Outlet />;
};