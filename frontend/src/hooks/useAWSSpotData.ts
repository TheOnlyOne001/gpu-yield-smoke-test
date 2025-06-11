import { useState, useEffect, useCallback } from 'react';
import { AWSSpotOffer, EnrichedAWSSpotOffer, AWSSpotDataResponse } from '@/types/aws-spot';
import { enrichAWSSpotOffer, isValidOffer } from '@/lib/awsUtils';

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
  refreshInterval = 30000
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

  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  // Fetch data from API
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

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/aws-spot/prices?${params}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result: AWSSpotDataResponse = await response.json();
      
      // Validate and enrich offers
      const validOffers = result.offers.filter(isValidOffer);
      const enrichedOffers = validOffers.map(enrichAWSSpotOffer);

      setData({
        offers: enrichedOffers,
        loading: false,
        error: null,
        lastUpdated: result.metadata.last_updated,
        totalCount: result.total_count,
        metadata: {
          regionsAvailable: result.metadata.regions_available,
          modelsAvailable: result.metadata.models_available,
          dataSource: result.metadata.data_source
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

  // WebSocket for real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    try {
      // Use proper WebSocket URL with same host as API
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const wsUrl = apiUrl.replace('http', 'ws') + '/ws/aws-spot';
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('AWS Spot WebSocket connected');
        setWsConnection(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          if (update.type === 'aws_spot_update') {
            const validOffers = update.offers
              .filter((offer: any) => {
                return offer.model && 
                       offer.usd_hr !== undefined && 
                       offer.region && 
                       offer.availability !== undefined && 
                       offer.instance_type;
              })
              .map((offer: any) => {
                const validOffer: AWSSpotOffer = {
                  model: offer.model,
                  usd_hr: Number(offer.usd_hr),
                  region: offer.region,
                  availability: Number(offer.availability),
                  instance_type: offer.instance_type,
                  provider: 'aws_spot' as const,
                };

                // Add optional fields
                if (offer.total_instance_price !== undefined) {
                  validOffer.total_instance_price = Number(offer.total_instance_price);
                }
                if (offer.gpu_memory_gb !== undefined) {
                  validOffer.gpu_memory_gb = Number(offer.gpu_memory_gb);
                }
                if (offer.timestamp) {
                  validOffer.timestamp = offer.timestamp;
                }
                if (offer.synthetic !== undefined) {
                  validOffer.synthetic = Boolean(offer.synthetic);
                }

                return validOffer;
              });

            const enrichedOffers = validOffers.map(enrichAWSSpotOffer);

            setData(prev => ({
              ...prev,
              offers: enrichedOffers,
              lastUpdated: update.timestamp,
              totalCount: enrichedOffers.length,
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

  // Polling fallback
  useEffect(() => {
    if (!autoRefresh || wsConnection) return;

    const interval = setInterval(fetchAWSSpotData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchAWSSpotData, wsConnection]);

  // Utility functions
  const refetch = useCallback(() => {
    fetchAWSSpotData();
  }, [fetchAWSSpotData]);

  return {
    ...data,
    refetch,
    hasLiveData: data.offers.some(o => o.freshness === 'live'),
    hasSyntheticData: data.offers.some(o => o.synthetic === true),
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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/aws-spot/regions`);
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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/aws-spot/models`);
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