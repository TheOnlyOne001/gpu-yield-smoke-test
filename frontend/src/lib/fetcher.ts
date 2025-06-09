// frontend/src/lib/fetcher.ts

export interface FetchResult<T> {
  data: T;
  timestamp: number;
}

/**
 * Enhanced fetcher that extracts timestamp from response headers
 * Falls back to current time if header is unavailable
 */
export async function fetcherWithTimestamp<T = any>(url: string): Promise<FetchResult<T>> {
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Try multiple header variations for better compatibility
    const timestampHeader = 
      response.headers.get('x-updated-at') || 
      response.headers.get('X-Updated-At') ||
      response.headers.get('last-modified') ||
      response.headers.get('Last-Modified');
    
    let timestamp: number;
    
    if (timestampHeader) {
      // Handle both Unix timestamp (ms) and ISO date strings
      const parsed = parseInt(timestampHeader, 10);
      if (!isNaN(parsed)) {
        timestamp = parsed;
      } else {
        // Try parsing as date string
        const dateTimestamp = new Date(timestampHeader).getTime();
        timestamp = isNaN(dateTimestamp) ? Date.now() : dateTimestamp;
      }
    } else {
      timestamp = Date.now();
    }
    
    return { data, timestamp };
  } catch (error) {
    console.error('Fetcher error:', error);
    throw error;
  }
}

/**
 * Format timestamp into human-readable "time ago" string
 * @param timestamp - Unix timestamp in milliseconds
 * @param locale - Optional locale for formatting
 */
export function formatTimeAgo(timestamp: number, locale: string = 'en'): string {
  const now = Date.now();
  const seconds = Math.floor((now - timestamp) / 1000);
  
  // Handle future timestamps (clock skew)
  if (seconds < 0) {
    return 'just now';
  }
  
  // Define time intervals
  const intervals: Array<[number, string, string]> = [
    [31536000, 'year', 'years'],
    [2592000, 'month', 'months'],
    [604800, 'week', 'weeks'],
    [86400, 'day', 'days'],
    [3600, 'hour', 'hours'],
    [60, 'minute', 'minutes'],
    [1, 'second', 'seconds']
  ];
  
  // Find appropriate interval
  for (const [secondsInInterval, singular, plural] of intervals) {
    const interval = Math.floor(seconds / secondsInInterval);
    if (interval >= 1) {
      if (interval === 1) {
        return `${interval} ${singular} ago`;
      }
      return `${interval} ${plural} ago`;
    }
  }
  
  return 'just now';
}

/**
 * Compact version of formatTimeAgo for tight UI spaces
 */
export function formatTimeAgoCompact(timestamp: number): string {
  const now = Date.now();
  const seconds = Math.floor((now - timestamp) / 1000);
  
  if (seconds < 0 || seconds < 5) return 'now';
  if (seconds < 60) return `${seconds}s ago`;
  
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks}w ago`;
  
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

/**
 * Determine freshness status of data based on age
 */
export function getDataFreshness(timestamp: number): 'fresh' | 'stale' | 'critical' {
  const age = Date.now() - timestamp;
  const ONE_MINUTE = 60 * 1000;
  const THREE_MINUTES = 3 * ONE_MINUTE;
  
  if (age < ONE_MINUTE) return 'fresh';
  if (age < THREE_MINUTES) return 'stale';
  return 'critical';
}