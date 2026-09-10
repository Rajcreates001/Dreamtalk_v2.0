"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  emotion?: string;
  brainState?: Record<string, unknown>;
}

export interface EmotionData {
  primary_mood: string;
  valence: number;
  arousal: number;
  dominance: number;
  intensity: string;
  is_hostile: boolean;
  cognitive_appraisal: string;
  action_tendency: string;
}

export interface BrainStateData {
  pfc_firing_rate: number;
  dacc_conflict: number;
  insula_valence: number;
  basal_ganglia_action: string;
  spiking_activity: {
    total_firing_rate: number;
    network_synchrony: number;
  };
  encoding_method: string;
}

type MessageHandler = (msg: any) => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:5001/ws/chat";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState<EmotionData | null>(null);
  const [currentBrainState, setCurrentBrainState] = useState<BrainStateData | null>(null);
  const handlersRef = useRef<Map<string, MessageHandler>>(new Map());

  const connect = useCallback((customSessionId?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = customSessionId
      ? `${WS_URL}/${customSessionId}`
      : WS_URL;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("[WS] Connected");
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("[WS] Disconnected");
    };

    ws.onerror = (e) => {
      console.error("[WS] Error:", e);
      setConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  const handleServerMessage = useCallback((data: any) => {
    switch (data.type) {
      case "session_info":
        setSessionId(data.session_id);
        break;

      case "processing":
        setProcessing(true);
        break;

      case "emotion":
        setCurrentEmotion(data.data);
        break;

      case "brain_state":
        setCurrentBrainState(data.data);
        break;

      case "response":
        setProcessing(false);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.data.text,
            timestamp: Date.now(),
            emotion: data.data.emotion?.primary_mood,
            brainState: data.data,
          },
        ]);
        break;

      case "error":
        setProcessing(false);
        console.error("[WS] Server error:", data.message);
        break;

      case "pong":
        break;

      default:
        handlersRef.current.get(data.type)?.(data);
    }
  }, []);

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, timestamp: Date.now() },
    ]);

    wsRef.current.send(JSON.stringify({ type: "text", text }));
  }, []);

  const clearHistory = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "clear" }));
    setMessages([]);
  }, []);

  const on = useCallback((type: string, handler: MessageHandler) => {
    handlersRef.current.set(type, handler);
    return () => handlersRef.current.delete(type);
  }, []);

  // Auto-reconnect
  useEffect(() => {
    const interval = setInterval(() => {
      if (!connected && wsRef.current === null) {
        connect();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [connected, connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return {
    connected,
    sessionId,
    messages,
    processing,
    currentEmotion,
    currentBrainState,
    connect,
    disconnect,
    sendMessage,
    clearHistory,
    on,
  };
}
