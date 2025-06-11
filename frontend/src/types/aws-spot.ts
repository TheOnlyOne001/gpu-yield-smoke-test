export interface AWSSpotOffer {
  // Required fields
  model: string;
  usd_hr: number;
  region: string;
  availability: number;
  instance_type: string;
  provider: 'aws_spot';
  
  // Optional fields
  total_instance_price?: number;
  gpu_memory_gb?: number;
  timestamp?: string;
  synthetic?: boolean;
}

export interface EnrichedAWSSpotOffer extends AWSSpotOffer {
  // Computed fields added by enrichment
  interruption_risk: 'low' | 'medium' | 'high';
  freshness: 'live' | 'recent' | 'stale';
  vcpu_count?: number;
  ram_gb?: number;
  network_performance?: string;
  storage_gb?: number;
  ebs_optimized?: boolean;
}

export interface AWSSpotDataResponse {
  offers: AWSSpotOffer[];
  total_count: number;
  metadata: {
    last_updated: string;
    regions_available: string[];
    models_available: string[];
    data_source: 'live' | 'synthetic' | 'none';
  };
}

// Export individual types
export type { AWSSpotOffer as AWSSpotOfferType };
export type { EnrichedAWSSpotOffer as EnrichedAWSSpotOfferType };
export type { AWSSpotDataResponse as AWSSpotDataResponseType };