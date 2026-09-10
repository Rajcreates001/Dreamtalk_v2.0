'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';

export interface VisemeWeights {
  aa: number;
  ee: number;
  ih: number;
  oh: number;
  ou: number;
}

export interface VrmLipsyncProps {
  analyser: AnalyserNode | null;
  className?: string;
  onVisemeUpdate?: (visemes: VisemeWeights) => void;
  smoothing?: {
    attack?: number;
    release?: number;
    volumeThreshold?: number;
  };
  showVisualizer?: boolean;
  children?: React.ReactNode;
}

class LipSyncProcessor {
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array<ArrayBuffer> | null = null;
  private smoothedWeights: VisemeWeights = { aa: 0, ee: 0, ih: 0, oh: 0, ou: 0 };
  private attack: number;
  private release: number;
  private volumeThreshold: number;

  constructor(
    attack = 0.3,
    release = 0.15,
    volumeThreshold = 0.05
  ) {
    this.attack = attack;
    this.release = release;
    this.volumeThreshold = volumeThreshold;
  }

  setAnalyser(analyser: AnalyserNode | null) {
    this.analyser = analyser;
    this.dataArray = analyser ? new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer> : null;
  }

  update(delta: number): VisemeWeights {
    if (!this.analyser || !this.dataArray) {
      this.smoothToZero(delta);
      return this.smoothedWeights;
    }

    this.analyser.getByteFrequencyData(this.dataArray);

    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    const avgVolume = sum / this.dataArray.length / 255;

    if (avgVolume < this.volumeThreshold) {
      this.smoothToZero(delta);
      return this.smoothedWeights;
    }

    const target = this.mapFrequenciesToVisemes(avgVolume);

    const rate = this.attack;
    this.smoothedWeights.aa = this.lerp(this.smoothedWeights.aa, target.aa, rate);
    this.smoothedWeights.ee = this.lerp(this.smoothedWeights.ee, target.ee, rate);
    this.smoothedWeights.ih = this.lerp(this.smoothedWeights.ih, target.ih, rate);
    this.smoothedWeights.oh = this.lerp(this.smoothedWeights.oh, target.oh, rate);
    this.smoothedWeights.ou = this.lerp(this.smoothedWeights.ou, target.ou, rate);

    return this.smoothedWeights;
  }

  private mapFrequenciesToVisemes(volume: number): VisemeWeights {
    if (!this.dataArray) {
      return { aa: 0, ee: 0, ih: 0, oh: 0, ou: 0 };
    }

    const len = this.dataArray.length;
    const lowEnd = Math.floor(len * 0.1);
    const lowMidEnd = Math.floor(len * 0.25);
    const midEnd = Math.floor(len * 0.5);
    const highEnd = Math.floor(len * 0.75);

    const low = this.averageRange(0, lowEnd) / 255;
    const lowMid = this.averageRange(lowEnd, lowMidEnd) / 255;
    const mid = this.averageRange(lowMidEnd, midEnd) / 255;
    const high = this.averageRange(midEnd, highEnd) / 255;

    const scale = Math.min(volume * 2, 1);

    return {
      aa: Math.min(low * 1.5 * scale, 0.8),
      oh: Math.min(lowMid * 1.3 * scale, 0.7),
      ee: Math.min(mid * 1.2 * scale, 0.6),
      ih: Math.min(high * 1.0 * scale, 0.5),
      ou: Math.min((low + lowMid) * 0.5 * scale, 0.6),
    };
  }

  private averageRange(start: number, end: number): number {
    if (!this.dataArray || end <= start) return 0;
    let sum = 0;
    for (let i = start; i < end && i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    return sum / (end - start);
  }

  private smoothToZero(delta: number) {
    const rate = this.release;
    this.smoothedWeights.aa = this.lerp(this.smoothedWeights.aa, 0, rate);
    this.smoothedWeights.ee = this.lerp(this.smoothedWeights.ee, 0, rate);
    this.smoothedWeights.ih = this.lerp(this.smoothedWeights.ih, 0, rate);
    this.smoothedWeights.oh = this.lerp(this.smoothedWeights.oh, 0, rate);
    this.smoothedWeights.ou = this.lerp(this.smoothedWeights.ou, 0, rate);
  }

  private lerp(current: number, target: number, rate: number): number {
    return current + (target - current) * rate;
  }

  reset() {
    this.smoothedWeights = { aa: 0, ee: 0, ih: 0, oh: 0, ou: 0 };
  }
}

export function VrmLipsync({
  analyser,
  className,
  onVisemeUpdate,
  smoothing = {},
  showVisualizer = false,
  children,
}: VrmLipsyncProps) {
  const processorRef = useRef<LipSyncProcessor>(
    new LipSyncProcessor(
      smoothing.attack ?? 0.3,
      smoothing.release ?? 0.15,
      smoothing.volumeThreshold ?? 0.05
    )
  );
  const [visemes, setVisemes] = useState<VisemeWeights>({
    aa: 0,
    ee: 0,
    ih: 0,
    oh: 0,
    ou: 0,
  });
  const rafRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const processFrame = useCallback(
    (time: number) => {
      const delta = lastTimeRef.current ? (time - lastTimeRef.current) / 1000 : 1 / 60;
      lastTimeRef.current = time;

      const weights = processorRef.current.update(delta);
      setVisemes(weights);
      onVisemeUpdate?.(weights);

      rafRef.current = requestAnimationFrame(processFrame);
    },
    [onVisemeUpdate]
  );

  useEffect(() => {
    const processor = processorRef.current;
    processor.setAnalyser(analyser);

    if (!analyser) {
      processor.reset();
    }
  }, [analyser]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(processFrame);
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [processFrame]);

  const maxViseme = Math.max(...Object.values(visemes));

  return (
    <div className={className}>
      {showVisualizer && (
        <div className='flex items-end gap-0.5'>
          {(Object.entries(visemes) as [string, number][]).map(
            ([name, value]) => (
              <div
                key={name}
                className='flex flex-col items-center gap-0.5'
              >
                <div
                  className='w-4 rounded-t bg-neutral-500 transition-all duration-75'
                  style={{ height: `${value * 40}px` }}
                />
                <span className='text-[8px] text-neutral-400'>{name}</span>
              </div>
            )
          )}
        </div>
      )}

      {children}

      {maxViseme > 0.01 && (
        <div
          className='pointer-events-none fixed inset-0 z-50'
          style={{ display: 'none' }}
          aria-hidden='true'
        />
      )}
    </div>
  );
}

export const lipSyncProcessor = new LipSyncProcessor();
export default VrmLipsync;
