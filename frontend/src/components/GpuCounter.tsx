// src/components/GpuCounter.tsx

import React, { useEffect, useState, useRef } from 'react';
import useSWR from 'swr';
import { 
  Cpu, 
  Activity, 
  Globe, 
  TrendingUp,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { fetcherWithTimestamp, FetchResult } from '../lib/fetcher';

// API configuration
const API_BASE_URL = (() => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (apiUrl.startsWith('http')) {
    return apiUrl;
  }
  return `https://${apiUrl}`;
})();

interface StatsResponse {
  gpu_count: number;
  total_providers: number;
  last_update?: string;
  active_models?: string[];
}

interface GpuCounterProps {
  className?: string;
  showDetails?: boolean;
  animate?: boolean;
}

export default function GpuCounter({ 
  className = '', 
  showDetails = false,
  animate = true 
}: GpuCounterProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [previousCount, setPreviousCount] = useState<number | null>(null);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const componentRef = useRef<HTMLDivElement>(null);
  
  // Fetch stats data with timestamp
  const { data: fetchResult, error, isLoading, mutate } = useSWR<FetchResult<StatsResponse>>(
    `${API_BASE_URL}/stats`,
    fetcherWithTimestamp,
    { 
      refreshInterval: 60000, // Refresh every minute
      errorRetryCount: 3,
      errorRetryInterval: 5000
    }
  );
  
  const data = fetchResult?.data;
  const timestamp = fetchResult?.timestamp;
  const count = data?.gpu_count ?? 0;
  
  // Intersection Observer for initial animation
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1 }
    );

    if (componentRef.current) {
      observer.observe(componentRef.current);
    }

    return () => observer.disconnect();
  }, []);
  
  // Track count changes for animation
  useEffect(() => {
    if (count > 0 && previousCount === null) {
      setPreviousCount(count);
    } else if (count !== previousCount && previousCount !== null) {
      setShouldAnimate(true);
      setPreviousCount(count);
      
      // Reset animation after completion
      const timer = setTimeout(() => setShouldAnimate(false), 300);
      return () => clearTimeout(timer);
    }
  }, [count, previousCount]);
  
  // Track analytics
  useEffect(() => {
    if (count > 0 && typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'gpu_counter_view', {
        event_category: 'engagement',
        gpu_count: count,
        providers: data?.total_providers
      });
    }
  }, [count, data?.total_providers]);
  
  // Manual refresh
  const handleRefresh = () => {
    mutate();
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'gpu_counter_refresh');
    }
  };
  
  // Format number with animation
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  };
  
  // Loading state
  if (isLoading && !data) {
    return (
      <div className={`mt-8 ${className}`}>
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading GPU stats...</span>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error && !data) {
    return (
      <div className={`mt-8 ${className}`}>
        <div className="flex items-center justify-center gap-2 text-red-400">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">Unable to load GPU stats</span>
        </div>
      </div>
    );
  }
  
  return (
    <div 
      ref={componentRef}
      className={`mt-8 transition-all duration-600 ${
        animate && isVisible ? 'opacity-100 translate-y-0' : animate ? 'opacity-0 translate-y-5' : ''
      } ${className}`}
    >
      <div className="relative">
        {/* Main counter display */}
        <div 
          className="group relative inline-block"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <p className="text-center text-sm font-medium text-gray-400 transition-colors duration-300 group-hover:text-gray-300">
            Tracking{' '}
            <span className="relative inline-flex items-center">
              <span
                className={`font-bold text-lg text-transparent bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text transition-all duration-300 ${
                  shouldAnimate ? 'animate-number-change' : ''
                }`}
              >
                {count > 0 ? formatNumber(count) : '—'}
              </span>
              
              {/* Live indicator */}
              {count > 0 && (
                <span className="absolute -top-1 -right-3">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                </span>
              )}
            </span>{' '}
            GPUs across{' '}
            <span className="font-bold text-purple-400">
              {data?.total_providers || 5}
            </span>{' '}
            clouds
          </p>
          
          {/* Refresh button */}
          <button
            onClick={handleRefresh}
            className={`
              absolute -right-8 top-1/2 -translate-y-1/2 
              p-1 rounded-full bg-white/5 
              opacity-0 group-hover:opacity-100 
              transition-all duration-300
              hover:bg-white/10 hover:scale-110
              ${isLoading ? 'animate-spin' : ''}
            `}
            disabled={isLoading}
            aria-label="Refresh GPU stats"
          >
            <RefreshCw className="w-3 h-3 text-gray-400" />
          </button>
        </div>
        
        {/* Detailed view on hover */}
        {showDetails && data?.active_models && data.active_models.length > 0 && (
          <div
            className={`
              absolute top-full left-1/2 -translate-x-1/2 mt-4
              bg-slate-900/95 backdrop-blur-sm rounded-lg p-4
              border border-white/10 shadow-xl
              transition-all duration-200 origin-top
              ${isHovered 
                ? 'opacity-100 scale-100 pointer-events-auto animate-tooltip-in' 
                : 'opacity-0 scale-95 pointer-events-none'
              }
              w-64 z-20
            `}
          >
            <div className="space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between pb-2 border-b border-white/10">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-400" />
                  Top GPU Models
                </h4>
                <Activity className="w-4 h-4 text-green-400" />
              </div>
              
              {/* Model list */}
              <div className="space-y-1">
                {data.active_models.slice(0, 5).map((model, index) => (
                  <div
                    key={model}
                    className={`flex items-center justify-between text-xs transition-all duration-300 ${
                      isHovered ? 'animate-fade-in-left' : ''
                    }`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <span className="text-gray-300">{model}</span>
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  </div>
                ))}
              </div>
              
              {/* Footer */}
              <div className="pt-2 border-t border-white/10">
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Globe className="w-3 h-3" />
                  Global coverage • Live data
                </p>
              </div>
            </div>
            
            {/* Tooltip arrow */}
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 
                            bg-slate-900 border-l border-t border-white/10 
                            rotate-45" />
          </div>
        )}
      </div>
    </div>
  );
}

// Minimal version for performance-sensitive contexts
export function GpuCounterMinimal() {
  const { data } = useSWR<StatsResponse>(
    `${API_BASE_URL}/stats`,
    (url) => fetch(url).then(r => r.json()),
    { refreshInterval: 60000 }
  );
  
  const count = data?.gpu_count ?? 0;
  
  return (
    <p className="mt-6 text-center text-sm font-medium text-gray-400">
      Tracking{' '}
      <span className="font-bold text-indigo-300">
        {count > 0 ? count.toLocaleString() : '—'}
      </span>{' '}
      GPUs across {data?.total_providers || 5} clouds
    </p>
  );
}

// Inline version for headers or compact spaces
export function GpuCounterInline({ className = '' }: { className?: string }) {
  const { data } = useSWR<StatsResponse>(
    `${API_BASE_URL}/stats`,
    (url) => fetch(url).then(r => r.json()),
    { refreshInterval: 60000 }
  );
  
  const count = data?.gpu_count ?? 0;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Cpu className="w-4 h-4 text-blue-400" />
      <span className="text-sm text-gray-300">
        <span className="font-semibold text-white">
          {count > 0 ? count.toLocaleString() : '—'}
        </span>{' '}
        GPUs
      </span>
    </div>
  );
}