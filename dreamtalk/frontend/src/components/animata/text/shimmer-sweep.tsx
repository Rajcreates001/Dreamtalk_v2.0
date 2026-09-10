// Dreamtalk - Frontend Animata
// Based on animata (MIT License)
// Source: animata

"use client";

import { useMemo } from "react";

import TextAnimator, {
  type TextAnimationPhaseSpec,
  type TextAnimationSpec,
} from "./text-animator";

const BASE_SPEC: TextAnimationSpec = {
  id: "shimmer-sweep",
  target: "whole",
  enter: {
    durationMs: 850,
    staggerMs: 0,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    from: {
      opacity: 0,
      xPx: -22,
      blurPx: 8,
    },
    to: {
      opacity: 1,
      xPx: 0,
      blurPx: 0,
    },
  },
  exit: {
    durationMs: 650,
    staggerMs: 0,
    easing: "cubic-bezier(0.7, 0, 0.84, 0)",
    from: {
      opacity: 1,
      xPx: 0,
      blurPx: 0,
    },
    to: {
      opacity: 0,
      xPx: 22,
      blurPx: 8,
    },
  },
  swap: {
    mode: "crossfade",
    overlapMs: 0,
    microDelayMs: 36,
  },
};

const DEFAULT_SAMPLES: readonly string[] = [
  "Drifts in from the left.",
  "Carries a soft shine.",
  "Sweeps across the line.",
];

export interface ShimmerSweepProps {
  text?: string | string[];
  enter?: Partial<TextAnimationPhaseSpec>;
  exit?: Partial<TextAnimationPhaseSpec>;
  speed?: number;
  holdMs?: number;
  gapMs?: number;
  yTravel?: number;
  className?: string;
}

export default function ShimmerSweep({
  text,
  enter,
  exit,
  speed,
  holdMs,
  gapMs,
  yTravel,
  className,
}: ShimmerSweepProps = {}) {
  const spec = useMemo<TextAnimationSpec>(
    () => ({
      ...BASE_SPEC,
      enter: {
        ...BASE_SPEC.enter,
        ...enter,
        from: { ...BASE_SPEC.enter.from, ...enter?.from },
        to: { ...BASE_SPEC.enter.to, ...enter?.to },
      },
      exit: {
        ...BASE_SPEC.exit,
        ...exit,
        from: { ...BASE_SPEC.exit.from, ...exit?.from },
        to: { ...BASE_SPEC.exit.to, ...exit?.to },
      },
    }),
    [enter, exit],
  );
  const samples = useMemo(() => {
    if (text == null) return [...DEFAULT_SAMPLES];
    return Array.isArray(text) ? text : [text];
  }, [text]);
  return (
    <TextAnimator
      spec={spec}
      samples={samples}
      speed={speed}
      holdMs={holdMs}
      gapMs={gapMs}
      yTravel={yTravel}
      className={className}
    />
  );
}
