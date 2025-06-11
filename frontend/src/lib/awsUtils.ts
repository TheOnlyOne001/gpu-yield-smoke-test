// Import types from the dedicated types file
import { AWSSpotOffer, EnrichedAWSSpotOffer } from '@/types/aws-spot';

// AWS Instance metadata
export const AWS_INSTANCE_METADATA: Record<string, {
  vcpu: number;
  ram_gb: number;
  network: string;
  storage_gb?: number;
  ebs_optimized?: boolean;
}> = {
  'p4d.24xlarge': { vcpu: 96, ram_gb: 1152, network: '400 Gbps', storage_gb: 8000, ebs_optimized: true },
  'p3.8xlarge': { vcpu: 32, ram_gb: 244, network: '10 Gbps', storage_gb: 0, ebs_optimized: true },
  'g4dn.xlarge': { vcpu: 4, ram_gb: 16, network: 'Up to 25 Gbps', storage_gb: 125, ebs_optimized: true },
  'g5.xlarge': { vcpu: 4, ram_gb: 16, network: 'Up to 10 Gbps', storage_gb: 250, ebs_optimized: true },
  'p5.48xlarge': { vcpu: 192, ram_gb: 2048, network: '3200 Gbps', storage_gb: 8000, ebs_optimized: true },
  'p2.xlarge': { vcpu: 4, ram_gb: 61, network: 'High', storage_gb: 0, ebs_optimized: true }
};

// Regional power costs ($/kWh)
export const REGION_POWER_COSTS: Record<string, number> = {
  'us-east-1': 0.10,
  'us-west-2': 0.08,
  'eu-west-1': 0.20,
  'ap-southeast-1': 0.15,
  'us-west-1': 0.12,
  'eu-central-1': 0.18
};

// GPU TDP in watts
export const GPU_TDP_WATTS: Record<string, number> = {
  'A100': 400,
  'H100': 700,
  'V100': 300,
  'T4': 70,
  'A10G': 150,
  'K80': 300
};

// Region display names
export const AWS_REGION_DISPLAY: Record<string, string> = {
  'us-east-1': 'N. Virginia',
  'us-west-2': 'Oregon',
  'eu-west-1': 'Ireland',
  'ap-southeast-1': 'Singapore',
  'us-west-1': 'N. California',
  'eu-central-1': 'Frankfurt'
};

// Calculate interruption risk based on availability
export function calculateInterruptionRisk(availability: number): 'low' | 'medium' | 'high' {
  if (availability >= 4) return 'low';
  if (availability >= 2) return 'medium';
  return 'high';
}

// Calculate data freshness
export function calculateFreshness(timestamp?: string): 'live' | 'recent' | 'stale' {
  if (!timestamp) return 'stale';
  
  const age = Date.now() - new Date(timestamp).getTime();
  const hours = age / (1000 * 60 * 60);
  
  if (hours < 1) return 'live';
  if (hours < 6) return 'recent';
  return 'stale';
}

// Type guard to check if offer is enriched
export function isEnrichedOffer(offer: AWSSpotOffer | EnrichedAWSSpotOffer): offer is EnrichedAWSSpotOffer {
  return 'interruption_risk' in offer && 'freshness' in offer;
}

// Enrich a single offer
export function enrichAWSSpotOffer(offer: AWSSpotOffer): EnrichedAWSSpotOffer {
  const metadata = AWS_INSTANCE_METADATA[offer.instance_type] || {};
  const timestamp = offer.timestamp || new Date().toISOString();
  
  return {
    ...offer,
    interruption_risk: calculateInterruptionRisk(offer.availability),
    freshness: calculateFreshness(timestamp),
    vcpu_count: metadata.vcpu,
    ram_gb: metadata.ram_gb,
    network_performance: metadata.network,
    storage_gb: metadata.storage_gb,
    ebs_optimized: metadata.ebs_optimized,
  };
}

// Safely ensure an offer is enriched
export function ensureEnrichedOffer(offer: AWSSpotOffer | EnrichedAWSSpotOffer): EnrichedAWSSpotOffer {
  if (isEnrichedOffer(offer)) {
    return offer;
  }
  return enrichAWSSpotOffer(offer);
}

// Validate offer completeness
export function isValidOffer(offer: Partial<AWSSpotOffer>): offer is AWSSpotOffer {
  return !!(
    offer.model &&
    offer.usd_hr !== undefined &&
    offer.region &&
    offer.availability !== undefined &&
    offer.instance_type &&
    offer.provider
  );
}

// Batch enrichment with validation
export function enrichOffersBatch(offers: (AWSSpotOffer | EnrichedAWSSpotOffer)[]): EnrichedAWSSpotOffer[] {
  return offers
    .filter((offer): offer is AWSSpotOffer | EnrichedAWSSpotOffer => {
      return !!(offer.model && offer.usd_hr !== undefined && offer.region);
    })
    .map(ensureEnrichedOffer);
}

// Calculate yield metrics with power costs
export function calculateOfferYieldMetrics(offer: AWSSpotOffer | EnrichedAWSSpotOffer) {
  const powerCost = REGION_POWER_COSTS[offer.region] ?? 0.12;
  const tdp = GPU_TDP_WATTS[offer.model] ?? 300;
  const powerCostPerHour = (tdp / 1000) * powerCost;
  const netYield = offer.usd_hr - powerCostPerHour;
  const margin = offer.usd_hr > 0 ? (netYield / offer.usd_hr) * 100 : 0;
  
  return {
    powerCostPerHour,
    netYield,
    margin,
    breakEven: netYield > 0,
    totalInstancePrice: offer.total_instance_price || 0,
    gpuMemory: offer.gpu_memory_gb || 16
  };
}

// Re-export types for convenience
export type { AWSSpotOffer, EnrichedAWSSpotOffer };