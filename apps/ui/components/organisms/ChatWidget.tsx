'use client';

import React, { useState } from 'react';
import { Button } from '@/components/atoms/Button';
import { FiMessageSquare, FiX, FiSend, FiMinimize2 } from 'react-icons/fi';
import { Card } from '@/components/molecules/Card';

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{role: 'user'|'agent', text: string}[]>([
    { role: 'agent', text: 'Hi there! 👋 I can help you find the perfect gift or check availability. What are you looking for today?' }
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSend = () => {
    if (!inputValue.trim()) return;
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', text: inputValue }]);
    
    // Simulate generic agent response (would connect to real agent backend)
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'agent', 
        text: "Thanks for asking! I'm a demo agent right now, but soon I'll be connected to our intelligent backend to help you with that request." 
      }]);
    }, 1000);
    
    setInputValue('');
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 p-4 bg-prime-600 text-white rounded-full shadow-lg hover:bg-prime-700 transition-transform hover:scale-105 flex items-center gap-2"
        aria-label="Open chat"
      >
        <FiMessageSquare className="w-6 h-6" />
        <span className="font-semibold hidden md:inline">Ask an Expert</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-full max-w-sm">
      <Card className="flex flex-col h-[500px] shadow-2xl border-prime-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-prime-600 text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <h3 className="font-bold">Holiday Assistant</h3>
          </div>
          <div className="flex gap-2">
             <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white">
               <FiMinimize2 className="w-5 h-5" />
             </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-900">
          {messages.map((m, idx) => (
             <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
               <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                 m.role === 'user' 
                   ? 'bg-prime-600 text-white rounded-br-none' 
                   : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-bl-none shadow-sm'
               }`}>
                 {m.text}
               </div>
             </div>
          ))}
        </div>

        {/* Input */}
        <div className="p-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your question..."
              className="flex-1 bg-gray-100 dark:bg-gray-900 border-0 rounded-full px-4 py-2 focus:ring-2 focus:ring-prime-500 text-sm"
              autoFocus
            />
            <Button type="submit" size="sm" className="rounded-full w-10 h-10 p-0 flex items-center justify-center">
              <FiSend className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
};
