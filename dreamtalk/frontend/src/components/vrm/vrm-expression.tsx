'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';

export interface ExpressionWeight {
  name: string;
  value: number;
}

export interface VrmExpressionProps {
  availableExpressions: string[];
  className?: string;
  onExpressionChange?: (name: string, value: number) => void;
  onApplyExpression?: (name: string) => void;
  defaultExpression?: string;
  disabled?: boolean;
  compact?: boolean;
}

const EXPRESSION_CATEGORIES: Record<string, { label: string; expressions: string[] }> = {
  mouth: {
    label: 'Mouth',
    expressions: ['aa', 'ee', 'ih', 'oh', 'ou', 'a', 'i', 'u', 'e', 'o', 'jawOpen', 'mouthOpen'],
  },
  eyes: {
    label: 'Eyes',
    expressions: ['blink', 'Blink', 'eyeBlinkLeft', 'eyeBlinkRight', 'wink', 'lookLeft', 'lookRight'],
  },
  emotion: {
    label: 'Emotion',
    expressions: [
      'happy', 'sad', 'angry', 'surprised', 'relaxed', 'neutral',
      'joy', 'fun', 'smile',
    ],
  },
};

export function VrmExpression({
  availableExpressions,
  className,
  onExpressionChange,
  onApplyExpression,
  defaultExpression,
  disabled = false,
  compact = false,
}: VrmExpressionProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('emotion');
  const [sliderValues, setSliderValues] = useState<Record<string, number>>({});
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const sliderTimeouts = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const categorized = availableExpressions.reduce(
    (acc, expr) => {
      const lower = expr.toLowerCase();
      for (const [cat, info] of Object.entries(EXPRESSION_CATEGORIES)) {
        if (info.expressions.some((e) => lower.includes(e))) {
          acc[cat] = acc[cat] || [];
          acc[cat].push(expr);
          return acc;
        }
      }
      acc['emotion'] = acc['emotion'] || [];
      acc['emotion'].push(expr);
      return acc;
    },
    {} as Record<string, string[]>
  );

  const filteredExpressions = categorized[selectedCategory] || availableExpressions;

  const handleSliderChange = useCallback(
    (name: string, value: number) => {
      setSliderValues((prev) => ({ ...prev, [name]: value }));
      setActivePreset(null);

      if (sliderTimeouts.current[name]) {
        clearTimeout(sliderTimeouts.current[name]);
      }

      sliderTimeouts.current[name] = setTimeout(() => {
        onExpressionChange?.(name, value);
      }, 16);

      onExpressionChange?.(name, value);
    },
    [onExpressionChange]
  );

  useEffect(() => {
    if (defaultExpression && availableExpressions.includes(defaultExpression)) {
      handleSliderChange(defaultExpression, 1.0);
    }
  }, [defaultExpression, availableExpressions]);

  useEffect(() => {
    return () => {
      Object.values(sliderTimeouts.current).forEach(clearTimeout);
    };
  }, []);

  const handlePresetClick = useCallback(
    (name: string) => {
      if (activePreset === name) {
        setActivePreset(null);
        handleSliderChange(name, 0);
        return;
      }

      setActivePreset(name);
      onApplyExpression?.(name);

      // Set all expression sliders for this preset
      setSliderValues((prev) => {
        const next = { ...prev };
        filteredExpressions.forEach((expr) => {
          next[expr] = expr === name ? 1.0 : 0;
        });
        return next;
      });

      filteredExpressions.forEach((expr) => {
        onExpressionChange?.(expr, expr === name ? 1.0 : 0);
      });
    },
    [activePreset, filteredExpressions, handleSliderChange, onApplyExpression, onExpressionChange]
  );

  if (compact) {
    return (
      <div className={cn('flex flex-wrap gap-1', className)}>
        {availableExpressions.slice(0, 6).map((expr) => (
          <button
            key={expr}
            onClick={() => handlePresetClick(expr)}
            disabled={disabled}
            className={cn(
              'rounded-md px-2 py-1 text-xs font-medium transition-colors',
              activePreset === expr
                ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
                : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
            )}
          >
            {expr}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {Object.keys(categorized).length > 0 && (
        <div className='flex gap-1 overflow-x-auto'>
          {Object.entries(EXPRESSION_CATEGORIES).map(([key, info]) => (
            <button
              key={key}
              onClick={() => setSelectedCategory(key)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                selectedCategory === key
                  ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
                  : 'bg-neutral-100 text-neutral-500 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
              )}
            >
              {info.label}
            </button>
          ))}
        </div>
      )}

      <div className='space-y-2'>
        {filteredExpressions.map((expr) => (
          <div key={expr} className='flex items-center gap-2'>
            <span className='w-20 shrink-0 text-xs font-medium text-neutral-600 dark:text-neutral-400'>
              {expr}
            </span>
            <input
              type='range'
              min={0}
              max={1}
              step={0.01}
              value={sliderValues[expr] ?? 0}
              onChange={(e) =>
                handleSliderChange(expr, parseFloat(e.target.value))
              }
              disabled={disabled}
              className='h-1.5 w-full appearance-none rounded-full bg-neutral-200 accent-neutral-900 dark:bg-neutral-700 dark:accent-white'
            />
            <span className='w-8 text-right text-xs tabular-nums text-neutral-500'>
              {Math.round((sliderValues[expr] ?? 0) * 100)}
            </span>
          </div>
        ))}
      </div>

      {availableExpressions.length === 0 && (
        <div className='flex items-center justify-center py-4 text-xs text-neutral-400'>
          No expressions available on this model
        </div>
      )}
    </div>
  );
}

export default VrmExpression;
