"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface EmotionEvent {
  timestamp: number;
  emotion: string;
  valence: number;
  arousal: number;
  intensity: number;
}

interface EmotionTimelineProps {
  refreshInterval?: number; // ms
}

const EMOTION_COLORS: Record<string, string> = {
  happy: "#22c55e",
  sad: "#3b82f6",
  angry: "#ef4444",
  fear: "#a855f7",
  surprise: "#f59e0b",
  disgust: "#84cc16",
  neutral: "#6b7280",
  contempt: "#f97316",
};

export function EmotionTimeline({ refreshInterval = 5000 }: EmotionTimelineProps) {
  const [events, setEvents] = useState<EmotionEvent[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const resp = await fetch("/analytics/emotions");
        if (resp.ok) {
          const data = await resp.json();
          setAnalytics(data);
          if (data.recent_emotions) {
            setEvents(data.recent_emotions.map((e: any) => ({
              timestamp: e.timestamp || Date.now(),
              emotion: e.emotion || "neutral",
              valence: e.valence || 0,
              arousal: e.arousal || 0,
              intensity: e.intensity || 0.5,
            })));
          }
        }
      } catch (err) {
        // Silently retry
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          📊 Emotion Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold">
              {analytics?.total_events || 0}
            </div>
            <div className="text-xs text-muted-foreground">Total Events</div>
          </div>
          <div>
            <div className="text-2xl font-bold">
              {analytics?.dominant_emotion || "N/A"}
            </div>
            <div className="text-xs text-muted-foreground">Dominant</div>
          </div>
          <div>
            <div className="text-2xl font-bold">
              {analytics?.avg_valence?.toFixed(2) || "0.00"}
            </div>
            <div className="text-xs text-muted-foreground">Avg Valence</div>
          </div>
        </div>

        {/* Emotion distribution bar */}
        {analytics?.emotion_counts && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Distribution</h4>
            <div className="flex h-6 overflow-hidden rounded-full">
              {Object.entries(analytics.emotion_counts).map(
                ([emotion, count]: [string, any]) => {
                  const total = analytics.total_events || 1;
                  const pct = ((count as number) / total) * 100;
                  return (
                    <div
                      key={emotion}
                      className="h-full transition-all"
                      style={{
                        width: `${pct}%`,
                        backgroundColor:
                          EMOTION_COLORS[emotion] || "#6b7280",
                      }}
                      title={`${emotion}: ${count} (${pct.toFixed(1)}%)`}
                    />
                  );
                }
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(analytics.emotion_counts).map(
                ([emotion, count]: [string, any]) => (
                  <div key={emotion} className="flex items-center gap-1 text-xs">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{
                        backgroundColor:
                          EMOTION_COLORS[emotion] || "#6b7280",
                      }}
                    />
                    {emotion} ({count})
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* Recent events */}
        {events.length > 0 && (
          <div className="space-y-1">
            <h4 className="text-sm font-medium">Recent</h4>
            <div className="max-h-40 space-y-1 overflow-y-auto">
              {events.slice(-10).reverse().map((e, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded bg-muted/50 px-2 py-1 text-xs"
                >
                  <span className="flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{
                        backgroundColor:
                          EMOTION_COLORS[e.emotion] || "#6b7280",
                      }}
                    />
                    {e.emotion}
                  </span>
                  <span className="text-muted-foreground">
                    v:{e.valence.toFixed(2)} a:{e.arousal.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {events.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">
            No emotion data yet. Start a conversation to see emotions.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
