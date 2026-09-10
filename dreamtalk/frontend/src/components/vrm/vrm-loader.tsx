'use client';

import React, { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';

export interface VRMLoadProgress {
  loaded: number;
  total: number;
  percent: number;
}

export interface VrmLoaderProps {
  modelUrl: string | null;
  className?: string;
  children?: React.ReactNode;
  renderLoading?: (progress: number) => React.ReactNode;
  renderError?: (error: string, retry: () => void) => React.ReactNode;
  renderEmpty?: () => React.ReactNode;
  onLoadStart?: () => void;
  onLoadComplete?: () => void;
  onError?: (error: string) => void;
}

export function VrmLoader({
  modelUrl,
  className,
  children,
  renderLoading,
  renderError,
  renderEmpty,
  onLoadStart,
  onLoadComplete,
  onError,
}: VrmLoaderProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const handleLoadStart = useCallback(() => {
    setIsLoading(true);
    setError(null);
    setProgress(0);
    onLoadStart?.();
  }, [onLoadStart]);

  const handleProgress = useCallback((pct: number) => {
    setProgress(pct);
  }, []);

  const handleLoadComplete = useCallback(() => {
    setIsLoading(false);
    setProgress(100);
    onLoadComplete?.();
  }, [onLoadComplete]);

  const handleError = useCallback(
    (err: string) => {
      setIsLoading(false);
      setError(err);
      onError?.(err);
    },
    [onError]
  );

  const handleRetry = useCallback(() => {
    setRetryCount((prev) => prev + 1);
    setError(null);
    setIsLoading(false);
    setProgress(0);
  }, []);

  if (!modelUrl) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-neutral-100 dark:bg-neutral-800',
          className
        )}
      >
        {renderEmpty ? (
          renderEmpty()
        ) : (
          <div className='flex flex-col items-center gap-2 text-neutral-400'>
            <svg
              className='h-12 w-12'
              fill='none'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={1.5}
                d='M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z'
              />
            </svg>
            <span className='text-sm'>No model loaded</span>
            <span className='text-xs'>Select a VRM model to display</span>
          </div>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-neutral-100 dark:bg-neutral-800',
          className
        )}
      >
        {renderError ? (
          renderError(error, handleRetry)
        ) : (
          <div className='flex flex-col items-center gap-2 text-red-400'>
            <svg
              className='h-12 w-12'
              fill='none'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={1.5}
                d='M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z'
              />
            </svg>
            <span className='text-sm font-medium'>{error}</span>
            <button
              onClick={handleRetry}
              className='rounded-md bg-neutral-200 px-3 py-1 text-xs text-neutral-700 hover:bg-neutral-300 dark:bg-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-600'
            >
              Retry
            </button>
          </div>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-neutral-100 dark:bg-neutral-800',
          className
        )}
      >
        {renderLoading ? (
          renderLoading(progress)
        ) : (
          <div className='flex flex-col items-center gap-3'>
            <div className='h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-600' />
            <div className='flex w-32 items-center gap-2'>
              <div className='h-1 flex-1 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700'>
                <div
                  className='h-full rounded-full bg-neutral-500 transition-all duration-300'
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className='text-xs text-neutral-400'>{progress}%</span>
            </div>
          </div>
        )}
      </div>
    );
  }

  return <>{children}</>;
}

export default VrmLoader;
