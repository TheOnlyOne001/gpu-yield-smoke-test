import React, { useMemo } from 'react';
import dynamic from 'next/dynamic';
import useSWR from 'swr';
import { 
  Calculator, 
  Zap, 
  Clock,
  DollarSign,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { fetcherWithTimestamp, FetchResult } from '../lib/fetcher';
import { SyncStatusDot } from './SyncStatusBadge';

// Lazy load heavy icons for better performance
const TrendingUp = dynamic(() => import('lucide-react').then(mod => ({ default: mod.TrendingUp })), {
  loading: () => <div className="w-3 h-3 skeleton rounded" />,
  ssr: true
});

// Constants for calculations
const HOURS_PER_DAY = 12;
const DAYS_MONTH = 30;
const POWER_COST = 0.10; // $/kWh
const POWER_WATT_4090 = 350; // avg watt draw

// API configuration
const API_BASE_URL = (() => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (apiUrl.startsWith('http')) {
    return apiUrl;
  }
  return `https://${apiUrl}`;
})();

interface DeltaResponse {
  deltas: Array<{
    gpu_model: string;
    best_source: string;
    price_usd_hr: number;
  }>;
}

interface MiniROIPreviewProps {
  onClick: () => void;
}

export default function MiniROIPreview({ onClick }: MiniROIPreviewProps) {
  // Fetch delta data with timestamp
  const { data: fetchResult, error, isLoading } = useSWR<FetchResult<DeltaResponse>>(
    `${API_BASE_URL}/delta`,
    fetcherWithTimestamp,
    { 
      refreshInterval: 60000,
      errorRetryCount: 3,
      errorRetryInterval: 5000
    }
  );

  const data = fetchResult?.data;
  const timestamp = fetchResult?.timestamp;

  // Find RTX 4090 data
  const rtx4090Data = data?.deltas?.find(d => d.gpu_model === 'RTX 4090');
  const delta = rtx4090Data?.price_usd_hr;

  // Calculate monthly extra profit
  const monthlyExtra = useMemo(() => {
    if (!delta || typeof delta !== 'number' || delta <= 0) return null;
    
    const powerCostPerHour = (POWER_WATT_4090 / 1000) * POWER_COST;
    const netProfitPerHour = delta - powerCostPerHour;
    
    // Only return positive values for "extra profit"
    if (netProfitPerHour <= 0) return null;
    
    const monthlyProfit = netProfitPerHour * HOURS_PER_DAY * DAYS_MONTH;
    return monthlyProfit;
  }, [delta]);

  // Handle click with analytics
  const handleClick = () => {
    onClick();
    // Track analytics event
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'mini_roi_click', {
        event_category: 'engagement',
        event_label: 'roi_preview_calculator'
      });
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="mx-auto mt-12 w-full max-w-lg px-4">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-800/80 p-6 shadow-2xl backdrop-blur-xl ring-1 ring-white/10">
          <div className="animate-pulse">
            <div className="h-5 w-32 bg-white/10 rounded mb-3"></div>
            <div className="h-10 w-40 bg-white/10 rounded mb-2"></div>
            <div className="h-4 w-48 bg-white/10 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  // Error state or no data
  if (error || !data || !data.deltas || data.deltas.length === 0) {
    return (
      <div className="mx-auto mt-12 w-full max-w-lg px-4">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/80 to-slate-800/80 p-6 shadow-2xl backdrop-blur-xl ring-1 ring-white/10">
          <p className="text-gray-400 text-sm text-center">Unable to load profit data. Please check back later.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-12 w-full max-w-lg px-4 mb-8">
      <div className="relative group">
        {/* Background gradient effect */}
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur-xl opacity-30 group-hover:opacity-40 transition-opacity duration-500"></div>
        
        {/* Main card */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/90 to-slate-800/90 p-6 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 transition-all duration-300 hover:ring-white/20 gpu-accelerated">
          {/* Decorative elements */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-8 -left-8 w-24 h-24 bg-gradient-to-tr from-green-500/10 to-emerald-500/10 rounded-full blur-2xl"></div>
          
          {/* Content */}
          <div className="relative z-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                Potential Extra Profit
              </h3>
              <div className="flex items-center gap-2">
                <SyncStatusDot 
                  timestamp={timestamp} 
                  isLoading={isLoading}
                  showTooltip={true}
                />
              </div>
            </div>

            {/* Profit display */}
            <div className="mb-4">
              {delta !== undefined && delta !== null && typeof delta === 'number' ? (
                <>
                  <div className="flex items-baseline gap-2">
                    <p className={`text-4xl font-bold transition-colors duration-300 ${
                      monthlyExtra && monthlyExtra > 0 ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {monthlyExtra && monthlyExtra > 0 ? (
                        `+$${Math.abs(monthlyExtra).toFixed(0)}`
                      ) : (
                        '—'
                      )}
                    </p>
                    <span className="text-lg text-gray-400">/month</span>
                  </div>
                  {rtx4090Data && (
                    <p className="text-xs text-gray-500 mt-1">
                      Best rate: ${delta.toFixed(3)}/hr on {rtx4090Data.best_source}
                      {monthlyExtra === null && (
                        <span className="text-yellow-400 ml-2">
                          (Below break-even)
                        </span>
                      )}
                    </p>
                  )}
                </>
              ) : (
                <div className="flex items-baseline gap-2">
                  <p className="text-4xl font-bold text-gray-400">—</p>
                  <span className="text-lg text-gray-400">/month</span>
                  <span className="text-xs text-gray-500">No data</span>
                </div>
              )}
            </div>

            {/* Assumptions */}
            <div className="bg-white/5 rounded-lg p-3 mb-4 border border-white/10">
              <p className="text-xs text-gray-400 font-medium mb-1">Quick estimate based on:</p>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div className="flex items-center gap-1">
                  <Zap className="w-3 h-3 text-blue-400" />
                  <span>RTX 4090</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-purple-400" />
                  <span>{HOURS_PER_DAY}h/day</span>
                </div>
                <div className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3 text-green-400" />
                  <span>${POWER_COST}/kWh</span>
                </div>
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3 text-orange-400" />
                  <span>{POWER_WATT_4090}W avg</span>
                </div>
              </div>
            </div>

            {/* CTA Button */}
            <button
              onClick={handleClick}
              className="group/btn w-full relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 p-[1px] transition-all duration-300 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] gpu-accelerated"
              style={{ willChange: 'transform, opacity' }}
            >
              <div className="relative flex items-center justify-center gap-2 rounded-[11px] bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 font-semibold text-white transition-all duration-300 group-hover/btn:bg-opacity-90">
                <Calculator className="w-4 h-4" />
                <span>Calculate for my rig</span>
                <ChevronRight className="w-4 h-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
              </div>
              
              {/* Button shine effect */}
              <div className="absolute inset-0 -top-[2px] flex h-full w-full justify-center">
                <div className="h-[2px] w-3/4 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover/btn:opacity-40 transition-opacity duration-500"></div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}