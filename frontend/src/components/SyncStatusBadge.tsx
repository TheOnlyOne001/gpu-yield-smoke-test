// frontend/src/components/SyncStatusBadge.tsx

import React, { useEffect, useState } from 'react';
import { formatTimeAgoCompact, getDataFreshness } from '../lib/fetcher';
import { RefreshCw, AlertTriangle, CheckCircle, Circle } from 'lucide-react';

interface SyncStatusBadgeProps {
  timestamp: number | undefined;
  isLoading?: boolean;
  className?: string;
  showIcon?: boolean;
  animated?: boolean;
}

export default function SyncStatusBadge({ 
  timestamp, 
  isLoading = false,
  className = '',
  showIcon = true,
  animated = true
}: SyncStatusBadgeProps) {
  const [currentTime, setCurrentTime] = useState(Date.now());
  
  // Update time every second for live updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  const safeTimestamp = timestamp ?? Date.now();
  const timeAgoText = formatTimeAgoCompact(safeTimestamp);
  const freshness = getDataFreshness(safeTimestamp);
  
  // Determine colors and icons based on freshness
  const getStatusConfig = () => {
    if (isLoading) {
      return {
        color: 'text-blue-400',
        bgColor: 'bg-blue-400/20',
        icon: RefreshCw,
        pulse: true,
        text: 'Syncing'
      };
    }
    
    switch (freshness) {
      case 'fresh':
        return {
          color: 'text-green-400',
          bgColor: 'bg-green-400/20',
          icon: CheckCircle,
          pulse: false,
          text: `Synced · ${timeAgoText}`
        };
      case 'stale':
        return {
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-400/20',
          icon: Circle,
          pulse: false,
          text: `Synced · ${timeAgoText}`
        };
      case 'critical':
        return {
          color: 'text-red-400',
          bgColor: 'bg-red-400/20',
          icon: AlertTriangle,
          pulse: true,
          text: `Offline · ${timeAgoText}`
        };
    }
  };
  
  const config = getStatusConfig();
  const Icon = config.icon;
  
  return (
    <div className={`
      inline-flex items-center gap-1.5 px-2.5 py-1 
      rounded-full backdrop-blur-sm transition-all duration-300
      ${config.bgColor} ${config.color} ${className}
      ${animated ? 'hover:scale-105' : ''}
    `}>
      {showIcon && (
        <Icon 
          className={`
            w-3 h-3 
            ${isLoading ? 'animate-spin' : ''}
            ${config.pulse && !isLoading ? 'animate-pulse' : ''}
          `} 
        />
      )}
      <span className="text-xs font-medium whitespace-nowrap">
        {config.text}
      </span>
    </div>
  );
}

// Minimal version for tight spaces
export function SyncStatusDot({ 
  timestamp, 
  isLoading = false,
  showTooltip = true 
}: { 
  timestamp: number | undefined;
  isLoading?: boolean;
  showTooltip?: boolean;
}) {
  const safeTimestamp = timestamp ?? Date.now();
  const freshness = getDataFreshness(safeTimestamp);
  const timeAgoText = formatTimeAgoCompact(safeTimestamp);
  
  const getColor = () => {
    if (isLoading) return 'bg-blue-400';
    switch (freshness) {
      case 'fresh': return 'bg-green-400';
      case 'stale': return 'bg-yellow-400';
      case 'critical': return 'bg-red-400';
    }
  };
  
  return (
    <div className="relative group">
      <div className={`
        w-2 h-2 rounded-full ${getColor()}
        ${isLoading || freshness === 'critical' ? 'animate-pulse' : ''}
      `} />
      {showTooltip && (
        <div className="
          absolute bottom-full left-1/2 -translate-x-1/2 mb-2
          px-2 py-1 bg-slate-900 text-white text-xs rounded
          opacity-0 group-hover:opacity-100 transition-opacity
          pointer-events-none whitespace-nowrap
        ">
          {isLoading ? 'Syncing...' : `Synced ${timeAgoText}`}
        </div>
      )}
    </div>
  );
}