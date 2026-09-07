import { apiClient } from './api';
import { ChatQueryRequest, ChatQueryResponse } from '../types';
const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';
export const chatService = {
  /**
   * Send a natural language query to the backend AI assistant
   */
  
  
  sendQuery: async (payload: ChatQueryRequest): Promise<ChatQueryResponse> => {
    const response = await apiClient.post<ChatQueryResponse>(`${API_BASE}/api/chat-queries/`, payload);
    return response.data;
  },

  /**
   * Retrieve chat history for the logged-in user
   */
  getHistory: async (userId?: string): Promise<ChatQueryResponse[]> => {
    const response = await apiClient.get<ChatQueryResponse[]>(`${API_BASE}/api/chat-queries/`, {
      params: userId ? { user_id: userId } : {},
    });
    return response.data;
  },
};