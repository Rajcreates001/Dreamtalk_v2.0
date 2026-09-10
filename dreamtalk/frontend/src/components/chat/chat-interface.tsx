"use client";

import { useState, useRef, useEffect } from "react";
import { useWebSocket, ChatMessage } from "@/hooks/use-websocket";

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-gray-800 text-gray-100 rounded-bl-md"
        }`}
      >
        <p className="text-sm leading-relaxed">{message.content}</p>
        {message.emotion && (
          <p className="text-xs mt-1 opacity-60">
            Emotion: {message.emotion}
          </p>
        )}
      </div>
    </div>
  );
}

function EmotionIndicator({ emotion }: { emotion: any }) {
  if (!emotion) return null;
  const moodColors: Record<string, string> = {
    happy: "text-yellow-400",
    sad: "text-blue-400",
    angry: "text-red-400",
    excited: "text-orange-400",
    calm: "text-green-400",
    neutral: "text-gray-400",
    fearful: "text-purple-400",
    surprised: "text-pink-400",
  };
  const color = moodColors[emotion.primary_mood] || "text-gray-400";

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded-lg text-xs">
      <span className={`font-medium ${color}`}>{emotion.primary_mood}</span>
      <span className="text-gray-500">|</span>
      <span className="text-gray-400">V: {emotion.valence?.toFixed(2)}</span>
      <span className="text-gray-500">|</span>
      <span className="text-gray-400">A: {emotion.arousal?.toFixed(2)}</span>
    </div>
  );
}

function BrainStateIndicator({ state }: { state: any }) {
  if (!state) return null;
  return (
    <div className="flex items-center gap-3 px-3 py-1.5 bg-gray-800/50 rounded-lg text-xs text-gray-400">
      <span>PFC: {state.pfc_firing_rate?.toFixed(1)}Hz</span>
      <span className="text-gray-600">|</span>
      <span>Conflict: {state.dacc_conflict?.toFixed(2)}</span>
      <span className="text-gray-600">|</span>
      <span>Action: {state.basal_ganglia_action?.replace("respond_", "")}</span>
    </div>
  );
}

export default function ChatInterface() {
  const {
    connected,
    messages,
    processing,
    currentEmotion,
    currentBrainState,
    connect,
    sendMessage,
    clearHistory,
  } = useWebSocket();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || processing) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              connected ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <h2 className="font-semibold">Digital Twin Chat</h2>
        </div>
        <button
          onClick={clearHistory}
          className="text-xs text-gray-400 hover:text-white transition-colors"
        >
          Clear History
        </button>
      </div>

      {/* Brain State + Emotion Indicators */}
      <div className="flex gap-2 px-4 py-2 border-b border-gray-800">
        <EmotionIndicator emotion={currentEmotion} />
        <BrainStateIndicator state={currentBrainState} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>Start a conversation with your Digital Twin</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {processing && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-100" />
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-200" />
                <span className="text-xs text-gray-400 ml-1">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-700">
        <div className="flex items-center gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 bg-gray-800 text-white rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500"
            disabled={!connected || processing}
          />
          <button
            onClick={handleSend}
            disabled={!connected || processing || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl px-4 py-3 text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
