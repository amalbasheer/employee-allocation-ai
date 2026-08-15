import { apiClient } from './api';
import { ChatQueryRequest, ChatQueryResponse } from '../types';

export const chatService = {
  sendQuery: async (payload: ChatQueryRequest): Promise<ChatQueryResponse> => {
    const response = await apiClient.post<ChatQueryResponse>('/chat/', payload);
    return response.data;
  },
};