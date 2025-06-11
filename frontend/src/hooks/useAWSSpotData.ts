import { useState, useEffect, useCallback } from 'react';
import { AWSSpotOffer, EnrichedAWSSpotOffer } from '../types/aws-spot';
import { enrichAWSSpotOffer } from '../lib/awsUtils';

interface UseAWSSpotDataParams {
  region?: string;
  model?: string;
  minAvailability?: number;
  viewType?: 'operator' | 'renter';
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface AWSSpotDataState {
  offers: EnrichedAWSSpotOffer[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  totalCount: number;
  metadata: {
    regionsAvailable: string[];
    modelsAvailable: string[];
    dataSource: 'live' | 'synthetic' | 'none';
  };
}

export function useAWSSpotData({
  region,
  model,
  minAvailability,
  viewType = 'operator',
  autoRefresh = true,
  refreshInterval = 30000 // 30 seconds
}: UseAWSSpotDataParams = {}) {
  const [data, setData] = useState<AWSSpotDataState>({
    offers: [],
    loading: true,
    error: null,
    lastUpdated: null,
    totalCount: 0,
    metadata: {
      regionsAvailable: [],
      modelsAvailable: [],
      dataSource: 'none'
    }
  });

  // Add WebSocket connection for real-time updates
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  const fetchAWSSpotData = useCallback(async () => {
    try {
      setData(prev => ({ ...prev, loading: true, error: null }));

      const params = new URLSearchParams();
      if (region) params.append('region', region);
      if (model) params.append('model', model);
      if (minAvailability) params.append('min_availability', minAvailability.toString());
      params.append('view_type', viewType);
      params.append('include_synthetic', 'true');
      params.append('limit', '100');

      // Use environment variable for API URL
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/aws-spot/prices?${params}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Enrich offers on the frontend for additional calculations
      const enrichedOffers = result.offers.map((offer: AWSSpotOffer) => 
        enrichAWSSpotOffer(offer)
      );

      setData({
        offers: enrichedOffers,
        loading: false,
        error: null,
        lastUpdated: result.metadata.last_updated,
        totalCount: result.total_count,
        metadata: {
          regionsAvailable: result.metadata.regions_available || [],
          modelsAvailable: result.metadata.models_available || [],
          dataSource: result.metadata.data_source || 'none'
        }
      });

    } catch (error) {
      console.error('Error fetching AWS Spot data:', error);
      setData(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }));
    }
  }, [region, model, minAvailability, viewType]);

  // WebSocket setup for real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    // Try to connect to WebSocket for real-time updates
    try {
      const wsUrl = `ws://localhost:8000/ws/aws-spot`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('AWS Spot WebSocket connected');
        setWsConnection(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          if (update.type === 'aws_spot_update') {
            // Update data with new offers
            setData(prev => ({
              ...prev,
              offers: update.offers.map((offer: AWSSpotOffer) => enrichAWSSpotOffer(offer)),
              lastUpdated: update.timestamp,
              metadata: {
                ...prev.metadata,
                dataSource: update.dataSource || 'live'
              }
            }));
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('AWS Spot WebSocket disconnected');
        setWsConnection(null);
      };
      
      return () => {
        ws.close();
      };
    } catch (e) {
      console.log('WebSocket not available, falling back to polling');
    }
  }, [autoRefresh]);

  // Initial fetch
  useEffect(() => {
    fetchAWSSpotData();
  }, [fetchAWSSpotData]);

  // Auto-refresh setup (fallback if WebSocket fails)
  useEffect(() => {
    if (!autoRefresh || wsConnection) return;

    const interval = setInterval(fetchAWSSpotData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchAWSSpotData, wsConnection]);

  const refetch = useCallback(() => {
    fetchAWSSpotData();
  }, [fetchAWSSpotData]);

  // Utility functions for data analysis
  const getBestPriceByModel = useCallback(() => {
    const modelPrices: Record<string, EnrichedAWSSpotOffer> = {};
    
    data.offers.forEach(offer => {
      if (!modelPrices[offer.model] || offer.usd_hr < modelPrices[offer.model].usd_hr) {
        modelPrices[offer.model] = offer;
      }
    });
    
    return modelPrices;
  }, [data.offers]);

  const getRegionSummary = useCallback(() => {
    const regionStats: Record<string, {
      offerCount: number;
      avgPrice: number;
      models: Set<string>;
    }> = {};

    data.offers.forEach(offer => {
      if (!regionStats[offer.region]) {
        regionStats[offer.region] = {
          offerCount: 0,
          avgPrice: 0,
          models: new Set()
        };
      }
      
      regionStats[offer.region].offerCount++;
      regionStats[offer.region].avgPrice += offer.usd_hr;
      regionStats[offer.region].models.add(offer.model);
    });

    // Calculate averages
    Object.keys(regionStats).forEach(region => {
      regionStats[region].avgPrice /= regionStats[region].offerCount;
    });

    return regionStats;
  }, [data.offers]);

  const getLowRiskOffers = useCallback(() => {
    return data.offers.filter(offer => offer.interruption_risk === 'low');
  }, [data.offers]);

  const getLiveDataOffers = useCallback(() => {
    return data.offers.filter(offer => offer.freshness === 'live');
  }, [data.offers]);

  return {
    ...data,
    refetch,
    // Utility functions
    getBestPriceByModel,
    getRegionSummary,
    getLowRiskOffers,
    getLiveDataOffers,
    // Computed values - Fix Set iteration issue
    hasLiveData: data.offers.some(o => o.freshness === 'live'),
    hasSyntheticData: data.offers.some(o => o.synthetic),
    averagePrice: data.offers.length > 0 
      ? data.offers.reduce((sum, o) => sum + o.usd_hr, 0) / data.offers.length 
      : 0,
    uniqueModels: Array.from(new Set(data.offers.map(o => o.model))),
    uniqueRegions: Array.from(new Set(data.offers.map(o => o.region)))
  };
}

// Hook for getting AWS regions
export function useAWSRegions() {
  const [regions, setRegions] = useState<Array<{code: string, name: string, available: boolean}>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRegions() {
      try {
        const response = await fetch('/api/aws-spot/regions');
        if (!response.ok) throw new Error('Failed to fetch regions');
        
        const data = await response.json();
        setRegions(data.regions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchRegions();
  }, []);

  return { regions, loading, error };
}

// Hook for getting AWS GPU models
export function useAWSModels() {
  const [models, setModels] = useState<Array<{name: string, available: boolean, category?: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchModels() {
      try {
        const response = await fetch('/api/aws-spot/models');
        if (!response.ok) throw new Error('Failed to fetch models');
        
        const data = await response.json();
        setModels(data.models);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchModels();
  }, []);

  return { models, loading, error };
}