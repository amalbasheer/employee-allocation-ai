import axios from 'axios';

// 1. Remove trailing '/api' to prevent duplicate pathing (/api/api/auth/login)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 10 seconds timeout
  headers: {
    'Content-Type': 'application/json',
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
  },
});

apiClient.interceptors.request.use(
  (config) => {
    // 2. Align token key with App.tsx ('auth_token')
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 3. Export default so 'import api from ./services/api' works in App.tsx
export default apiClient;