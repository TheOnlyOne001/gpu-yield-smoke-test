export interface AWSSpotOffer {
  // Core fields from scraper
  model: string;           // GPU model (A100, T4, V100, etc.)
  usd_hr: number;         // Per-GPU hourly price
  region: string;         // AWS region (us-east-1, etc.)
  availability: number;   // GPU count per instance (1-8)
  instance_type: string;  // EC2 instance type (p4d.24xlarge, etc.)
  provider: 'aws_spot';
  
  // Additional fields from scraper
  total_instance_price?: number;  // Total hourly cost for entire instance
  gpu_memory_gb?: number;         // VRAM per GPU
  timestamp?: string;             // ISO timestamp of price fetch
  synthetic?: boolean;           // Flag for synthetic data
}

// Extended offer with derived fields
export interface EnrichedAWSSpotOffer extends AWSSpotOffer {
  // Derived fields from enrichment
  interruption_risk?: 'low' | 'medium' | 'high';
  freshness?: 'live' | 'recent' | 'stale';
  vcpu_count?: number;
  ram_gb?: number;
  network_performance?: string;
  storage_gb?: number;
  ebs_optimized?: boolean;
  yield_metrics?: {
    power_cost_hr: number;
    net_yield_hr: number;
    margin_percentage: number;
    break_even: boolean;
  };
}