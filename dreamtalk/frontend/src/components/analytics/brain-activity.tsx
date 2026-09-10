"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface BrainArea {
  name: string;
  firing_rate: number;
  status: "active" | "inactive" | "conflict";
}

interface BrainActivityProps {
  refreshInterval?: number;
}

const BRAIN_AREAS: Record<string, { label: string; color: string; description: string }> = {
  pfc: { label: "Prefrontal Cortex", color: "#853953", description: "Executive function" },
  dacc: { label: "dACC", color: "#D84C63", description: "Conflict monitoring" },
  insula: { label: "Insula", color: "#9E3B6B", description: "Emotion processing" },
  ipl: { label: "IPL", color: "#8F9A5E", description: "Context integration" },
  bg: { label: "Basal Ganglia", color: "#D6A44C", description: "Action selection" },
};

export function BrainActivity({ refreshInterval = 3000 }: BrainActivityProps) {
  const [areas, setAreas] = useState<BrainArea[]>([]);
  const [action, setAction] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const resp = await fetch("/analytics/brain");
        if (resp.ok) {
          const data = await resp.json();
          if (data.brain_areas) {
            setAreas(
              Object.entries(data.brain_areas).map(([key, info]: [string, any]) => ({
                name: key,
                firing_rate: info.firing_rate || info.total || 0,
                status: info.status || (info.firing_rate > 0 ? "active" : "inactive"),
              }))
            );
          }
          if (data.last_action) setAction(data.last_action);
          if (data.avg_confidence) setConfidence(data.avg_confidence);
        }
      } catch {
        // Silently retry
      }
    };

    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  const maxFiring = Math.max(...areas.map((a) => a.firing_rate), 1);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          🧠 Brain Activity
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Brain areas visualization */}
        <div className="space-y-3">
          {Object.entries(BRAIN_AREAS).map(([key, info]) => {
            const area = areas.find((a) => a.name === key);
            const rate = area?.firing_rate || 0;
            const pct = (rate / maxFiring) * 100;
            const isActive = area?.status === "active";

            return (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        isActive ? "animate-pulse" : ""
                      }`}
                      style={{ backgroundColor: info.color }}
                    />
                    {info.label}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {rate.toFixed(1)} Hz
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(pct, 2)}%`,
                      backgroundColor: info.color,
                      opacity: isActive ? 1 : 0.3,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">{info.description}</p>
              </div>
            );
          })}
        </div>

        {/* Action selection */}
        {action && (
          <div className="rounded-lg border bg-muted/50 p-3">
            <div className="text-sm font-medium">Selected Action</div>
            <div className="mt-1 font-mono text-lg">{action}</div>
            <div className="text-xs text-muted-foreground">
              Confidence: {(confidence * 100).toFixed(1)}%
            </div>
          </div>
        )}

        {areas.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">
            No brain activity data. Send a message to see brain activation.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
