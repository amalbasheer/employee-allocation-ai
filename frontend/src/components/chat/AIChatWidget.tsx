import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Bot, User, X, Send, Loader2, History, RotateCcw } from 'lucide-react';
import { ChatQueryResponse } from '../../types';
import { chatService } from '../../services/chatService';

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
  const [fetchingHistory, setFetchingHistory] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const defaultWelcomeMessage: Message = {
    id: '1',
    sender: 'bot',
    text: 'Hello! I am your AI Allocation Assistant. Ask me anything about projects, mentor availability, or student batches.',
  };

  const [messages, setMessages] = useState<Message[]>([defaultWelcomeMessage]);

  const getCurrentUserId = (): string | null => {
    return localStorage.getItem('user_id') || localStorage.getItem('userId') || null;
  };

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  // Fetch History for the current user
  const handleFetchHistory = async () => {
    setFetchingHistory(true);
    try {
      const userId = getCurrentUserId();
      const historyData = await chatService.getHistory(userId || undefined);

      if (historyData && historyData.length > 0) {
        const restoredMessages: Message[] = [];
        historyData.forEach((log, idx) => {
          restoredMessages.push({
            id: `hist-u-${log.id || idx}`,
            sender: 'user',
            text: log.query,
          });
          restoredMessages.push({
            id: `hist-b-${log.id || idx}`,
            sender: 'bot',
            text: log.response_text || 'No response recorded.',
            recommendations: log.recommendations || [],
          });
        });
        setMessages(restoredMessages);
        setHistoryLoaded(true);
      }
    } catch (err) {
      console.error('Failed to load chat history', err);
    } finally {
      setFetchingHistory(false);
    }
  };

  // Sending a Message
  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const queryText = input.trim();
    const userId = getCurrentUserId();

    // 1. Append user message to state
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: queryText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // 2. Post query to backend
      const response = await chatService.sendQuery({
        query: queryText,
        user_id: userId,
      });

      // 3. Append bot response to state
      const botMsg: Message = {
        id: response.id || `bot-${Date.now()}`,
        sender: 'bot',
        text: response.response_text || 'No response generated.',
        recommendations: response.recommendations || [],
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error('Failed to send query', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([defaultWelcomeMessage]);
    setHistoryLoaded(false);
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

            {/* Actions: History, Reset, Close */}
            <div className="flex items-center gap-1">
              <button
                onClick={handleFetchHistory}
                disabled={fetchingHistory}
                title="Load History"
                className="p-1.5 text-slate-400 hover:text-indigo-400 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50"
              >
                {fetchingHistory ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <History className="w-4 h-4" />
                )}
              </button>

              {historyLoaded && (
                <button
                  onClick={handleResetChat}
                  title="Clear View"
                  className="p-1.5 text-slate-400 hover:text-amber-400 rounded-lg hover:bg-slate-700 transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}

              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages Window */}
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
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.recommendations && msg.recommendations.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-700 space-y-2">
                      <span className="text-[11px] font-semibold text-indigo-300">Top Recommendations:</span>
                      {msg.recommendations.map((rec, idx) => (
                        <div
                          key={rec.resource_id || idx}
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
              <div className="flex gap-2 text-slate-400 text-xs items-center p-2 bg-slate-800/40 rounded-lg w-fit">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" /> AI is reasoning...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question..."
              className="flex-1 bg-slate-800 text-white placeholder-slate-400 text-xs sm:text-sm px-3 py-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
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