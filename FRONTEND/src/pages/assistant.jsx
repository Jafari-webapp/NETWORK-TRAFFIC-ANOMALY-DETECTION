import React, { useRef, useState, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import Layout from '../components/Layout';
import MarkdownLite from '../components/MarkdownLite';
import * as api from '../services/api';

export default function AssistantPage() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi, I'm your AI Network Assistant. Ask me about traffic, anomalies, threats, IPs, or protocols in your network." },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setInput('');
    setSending(true);
    setError('');

    try {
      const history = newMessages
        .slice(0, -1)
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-10);
      const res = await api.chatWithAssistant(text, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch (err) {
      setError(api.getErrorMessage(err, 'Assistant is unavailable right now.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <Layout title="AI Network Assistant">
      <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-160px)] rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div className={`max-w-[75%] px-3.5 py-2.5 rounded-2xl text-sm ${
                m.role === 'user' ? 'bg-sky-600 text-white rounded-br-sm whitespace-pre-wrap' : 'bg-slate-100 text-slate-800 rounded-bl-sm'
              }`}>
                {m.role === 'assistant' ? <MarkdownLite text={m.content} /> : m.content}
              </div>
              {m.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
          {sending && <p className="text-xs text-slate-400 pl-9">Thinking...</p>}
          <div ref={bottomRef} />
        </div>

        {error && <div className="mx-5 mb-2 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">{error}</div>}

        <div className="p-3 border-t border-slate-200 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about traffic, anomalies, an IP, a protocol..."
            className="flex-1 px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-4 py-2.5 rounded-xl bg-sky-600 text-white disabled:opacity-40 hover:bg-sky-700"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Layout>
  );
}
