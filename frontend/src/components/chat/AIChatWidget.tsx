// src/components/chat/AIChatWidget.tsx
import React, { useState } from 'react';
import { MessageSquare, X, Send, Bot, User, Sparkles } from 'lucide-react';
import { apiClient } from '../../services/api';
import { ChatQueryResponse } from '../../types';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  recommendations?: ChatQueryResponse['recommendations'];
}

export const AIChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'bot',
      text: 'Hello! I am your AI Allocation Assistant. Ask me anything about project requirements, skill availability, or mentor recommendations.',
    },
  ]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiClient.post<ChatQueryResponse>('/chat/', {
        query: userMsg.text,
        top_k: 3,
      });

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: response.data.response_text,
        recommendations: response.data.recommendations,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'bot',
          text: 'I could not process that query. Please make sure the backend API is online.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white p-4 rounded-full shadow-2xl transition-all duration-300 hover:scale-105"
        >
          <Sparkles className="w-6 h-6 animate-pulse" />
          <span className="font-semibold text-sm hidden sm:inline">AI Assistant</span>
        </button>
      )}

      {isOpen && (
        <div className="w-[360px] sm:w-[420px] h-[540px] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-slate-800 p-4 border-b border-slate-700 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600/30 text-indigo-400 rounded-lg">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">Allocation AI Assistant</h3>
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-ping" /> Online
                </span>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Container */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-950/50">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.sender === 'bot' && (
                  <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] p-3 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-indigo-600 text-white rounded-tr-none'
                      : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none'
                  }`}
                >
                  <p>{msg.text}</p>
                  {msg.recommendations && msg.recommendations.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-700 space-y-2">
                      <span className="text-[11px] font-semibold text-indigo-300">Top Recommendations:</span>
                      {msg.recommendations.map((rec) => (
                        <div
                          key={rec.resource_id}
                          className="bg-slate-900/80 p-2 rounded-lg text-xs flex justify-between items-center border border-slate-800"
                        >
                          <div>
                            <span className="font-medium text-white">{rec.name}</span>
                            <span className="block text-[10px] text-slate-400 capitalize">{rec.resource_type}</span>
                          </div>
                          <span className="bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-mono font-bold text-[10px]">
                            {rec.suitability_score}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {msg.sender === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-slate-700 text-slate-300 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-2 text-slate-400 text-xs items-center">
                <Bot className="w-4 h-4 animate-spin text-indigo-400" /> AI is reasoning...
              </div>
            )}
          </div>

          {/* Input Box */}
          <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about candidate recommendations..."
              className="flex-1 bg-slate-800 text-white placeholder-slate-400 text-xs sm:text-sm px-3 py-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={handleSend}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white p-2.5 rounded-xl transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};