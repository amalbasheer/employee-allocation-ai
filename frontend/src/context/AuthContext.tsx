// src/context/AuthContext.tsx
import React, { createContext, useContext, useState } from 'react';
import { User, Role } from '../types';

interface AuthContextType {
  user: User | null;
  role: Role | null;
  token: string | null;
  login: (userData: any, token?: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Directly pull role strictly from user_metadata
  const extractRole = (userData: any): Role | null => {
    return userData?.user_metadata?.role || null;
  };

  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('auth_user');
    if (!savedUser) return null;
    const parsedUser = JSON.parse(savedUser);
    return {
      ...parsedUser,
      role: extractRole(parsedUser),
    };
  });

  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('auth_token');
  });

  const login = (userData: any, authToken?: string) => {
    const resolvedRole = extractRole(userData);
    const normalizedUser = {
      ...userData,
      role: resolvedRole,
    };

    setUser(normalizedUser);
    localStorage.setItem('auth_user', JSON.stringify(normalizedUser));

    if (authToken) {
      setToken(authToken);
      localStorage.setItem('auth_token', authToken);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_user');
    localStorage.removeItem('auth_token');
  };

  const currentRole = extractRole(user);

  return (
    <AuthContext.Provider
      value={{
        user,
        role: currentRole,
        token,
        login,
        logout,
        isAuthenticated: !!user && !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};