import axios from 'axios';
import {
  CompanyEmployeeResponse,
  CompanyEmployeeCreate,
  CompanyEmployeeUpdate,
  InternResponse,
  InternCreate,
  InternUpdate,
} from '../types/userManagement';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ==========================================
// EMPLOYEE API CALLS
// ==========================================
export const employeeApi = {
  getAll: async (): Promise<CompanyEmployeeResponse[]> => {
    const res = await api.get('/employees');
    return res.data;
  },

  getById: async (id: string): Promise<CompanyEmployeeResponse> => {
    const res = await api.get(`/employees/${id}`);
    return res.data;
  },

  create: async (data: CompanyEmployeeCreate): Promise<CompanyEmployeeResponse> => {
    const res = await api.post('/employees', data);
    return res.data;
  },

  update: async (id: string, data: CompanyEmployeeUpdate): Promise<CompanyEmployeeResponse> => {
    const res = await api.patch(`/employees/${id}`, data);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/employees/${id}`);
  },
};

// ==========================================
// INTERN API CALLS
// ==========================================
export const internApi = {
  getAll: async (): Promise<InternResponse[]> => {
    const res = await api.get('/interns');
    return res.data;
  },

  getById: async (id: string): Promise<InternResponse> => {
    const res = await api.get(`/interns/${id}`);
    return res.data;
  },

  create: async (data: InternCreate): Promise<InternResponse> => {
    const res = await api.post('/interns', data);
    return res.data;
  },

  update: async (id: string, data: InternUpdate): Promise<InternResponse> => {
    const res = await api.patch(`/interns/${id}`, data);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/interns/${id}`);
  },
};