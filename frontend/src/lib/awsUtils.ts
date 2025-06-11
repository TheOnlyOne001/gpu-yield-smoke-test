// types/aws-spot.ts
export interface AWSSpotOffer {
  // Core fields we already scrape
  model: string;           // GPU model (A100, T4, V100, etc.)
  usd_hr: number;         // Per-GPU hourly price
  region: string;         // AWS region (us-east-1, etc.)
  availability: number;   // GPU count per instance (1-8)
  instance_type: string;  // EC2 instance type (p4d.24xlarge, etc.)
  provider: 'aws_spot';
  
  // Additional fields from scraper
  total_instance_price: number;  // Total hourly cost for entire instance
  gpu_memory_gb: number;         // VRAM per GPU
  timestamp: string;             // ISO timestamp of price fetch
  synthetic?: boolean;           // Flag for synthetic data
}

// Extended offer with derived fields
export interface EnrichedAWSSpotOffer extends AWSSpotOffer {
  // Derived fields
  interruption_risk: 'low' | 'medium' | 'high';
  freshness: 'live' | 'recent' | 'stale';
  vcpu_count?: number;
  ram_gb?: number;
  network_performance?: string;
  storage_gb?: number;
  ebs_optimized?: boolean;
}

// Instance metadata mapping
export const AWS_INSTANCE_METADATA: Record<string, {
  vcpu: number;
  ram_gb: number;
  network: string;
  storage_gb?: number;
  ebs_optimized: boolean;
}> = {
  // G4dn - T4 instances
  "g4dn.xlarge": { vcpu: 4, ram_gb: 16, network: "Up to 25 Gbps", storage_gb: 125, ebs_optimized: true },
  "g4dn.2xlarge": { vcpu: 8, ram_gb: 32, network: "Up to 25 Gbps", storage_gb: 225, ebs_optimized: true },
  "g4dn.4xlarge": { vcpu: 16, ram_gb: 64, network: "Up to 25 Gbps", storage_gb: 225, ebs_optimized: true },
  "g4dn.8xlarge": { vcpu: 32, ram_gb: 128, network: "50 Gbps", storage_gb: 900, ebs_optimized: true },
  "g4dn.12xlarge": { vcpu: 48, ram_gb: 192, network: "50 Gbps", storage_gb: 900, ebs_optimized: true },
  "g4dn.16xlarge": { vcpu: 64, ram_gb: 256, network: "50 Gbps", storage_gb: 900, ebs_optimized: true },
  
  // G5 - A10G instances
  "g5.xlarge": { vcpu: 4, ram_gb: 16, network: "Up to 10 Gbps", storage_gb: 250, ebs_optimized: true },
  "g5.2xlarge": { vcpu: 8, ram_gb: 32, network: "Up to 10 Gbps", storage_gb: 450, ebs_optimized: true },
  "g5.4xlarge": { vcpu: 16, ram_gb: 64, network: "Up to 25 Gbps", storage_gb: 600, ebs_optimized: true },
  "g5.8xlarge": { vcpu: 32, ram_gb: 128, network: "25 Gbps", storage_gb: 900, ebs_optimized: true },
  "g5.12xlarge": { vcpu: 48, ram_gb: 192, network: "40 Gbps", storage_gb: 3800, ebs_optimized: true },
  "g5.16xlarge": { vcpu: 64, ram_gb: 256, network: "25 Gbps", storage_gb: 1900, ebs_optimized: true },
  "g5.24xlarge": { vcpu: 96, ram_gb: 384, network: "50 Gbps", storage_gb: 3800, ebs_optimized: true },
  "g5.48xlarge": { vcpu: 192, ram_gb: 768, network: "100 Gbps", storage_gb: 7600, ebs_optimized: true },
  
  // P3 - V100 instances
  "p3.2xlarge": { vcpu: 8, ram_gb: 61, network: "Up to 10 Gbps", ebs_optimized: true },
  "p3.8xlarge": { vcpu: 32, ram_gb: 244, network: "10 Gbps", ebs_optimized: true },
  "p3.16xlarge": { vcpu: 64, ram_gb: 488, network: "25 Gbps", ebs_optimized: true },
  "p3dn.24xlarge": { vcpu: 96, ram_gb: 768, network: "100 Gbps", storage_gb: 1800, ebs_optimized: true },
  
  // P4 - A100 instances
  "p4d.24xlarge": { vcpu: 96, ram_gb: 1152, network: "400 Gbps", storage_gb: 8000, ebs_optimized: true },
  "p4de.24xlarge": { vcpu: 96, ram_gb: 1152, network: "400 Gbps", storage_gb: 8000, ebs_optimized: true },
  
  // P5 - H100 instances
  "p5.48xlarge": { vcpu: 192, ram_gb: 2048, network: "3200 Gbps", storage_gb: 30720, ebs_optimized: true },
};

// Utility functions
export function calculateInterruptionRisk(availability: number): 'low' | 'medium' | 'high' {
  if (availability >= 4) return 'low';
  if (availability >= 2) return 'medium';
  return 'high';
}

export function calculateFreshness(timestamp: string): 'live' | 'recent' | 'stale' {
  const age = Date.now() - new Date(timestamp).getTime();
  const hours = age / (1000 * 60 * 60);
  
  if (hours < 1) return 'live';
  if (hours < 6) return 'recent';
  return 'stale';
}

export function enrichAWSSpotOffer(offer: AWSSpotOffer): EnrichedAWSSpotOffer {
  const metadata = AWS_INSTANCE_METADATA[offer.instance_type] || {};
  
  return {
    ...offer,
    interruption_risk: calculateInterruptionRisk(offer.availability),
    freshness: calculateFreshness(offer.timestamp),
    vcpu_count: metadata.vcpu,
    ram_gb: metadata.ram_gb,
    network_performance: metadata.network,
    storage_gb: metadata.storage_gb,
    ebs_optimized: metadata.ebs_optimized,
  };
}

// Region display names
export const AWS_REGION_DISPLAY: Record<string, string> = {
  'us-east-1': 'US East (N. Virginia)',
  'us-west-2': 'US West (Oregon)',
  'eu-west-1': 'EU West (Ireland)',
  'us-east-2': 'US East (Ohio)',
  'ap-southeast-1': 'Asia Pacific (Singapore)',
  'eu-central-1': 'EU Central (Frankfurt)',
  'ap-northeast-1': 'Asia Pacific (Tokyo)',
};

// Power cost estimates by region (example values)
export const REGION_POWER_COSTS: Record<string, number> = {
  'us-east-1': 0.12,    // $/kWh
  'us-west-2': 0.09,
  'eu-west-1': 0.18,
  'us-east-2': 0.11,
  'ap-southeast-1': 0.15,
  'eu-central-1': 0.20,
  'ap-northeast-1': 0.17,
};

// GPU TDP values for yield calculations
export const GPU_TDP_WATTS: Record<string, number> = {
  'T4': 70,
  'A10G': 150,
  'V100': 300,
  'A100': 400,
  'H100': 700,
  'K80': 300,
  'M60': 300,
};