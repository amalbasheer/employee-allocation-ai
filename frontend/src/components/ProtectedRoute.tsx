import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  children: React.ReactElement;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const location = useLocation();

  // Retrieve user session from localStorage (or update to your auth context hook)
  const storedUser = localStorage.getItem('user');
  const user = storedUser ? JSON.parse(storedUser) : null;

  // 1. Redirect to login if unauthenticated
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 2. Case-insensitive role verification
  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = (user.role || user.userType || '').toString().toUpperCase();
    const hasAccess = allowedRoles.some((role) => role.toUpperCase() === userRole);

    if (!hasAccess) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  // 3. Render dashboard if authorized
  return children;
};