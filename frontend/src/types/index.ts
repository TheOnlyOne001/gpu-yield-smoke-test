// Re-export all AWS Spot types
export * from './aws-spot';

// Dashboard specific types - Remove conflicts by renaming
export interface DashboardGPUData {
  model: string;
  platform: string;
  price: number;
  utilization: number;
  status: 'active' | 'idle' | 'error';
  earnings: number;
  powerDraw: number;
  temperature: number;
  lastUpdate: string;
  region?: string;
  instanceType?: string;
  interruptionRisk?: 'low' | 'medium' | 'high';
  netYield?: number;
  margin?: number;
}

export interface DashboardMarketData {
  timestamp: string;
  price: number;
  volume: number;
  platform: string;
}

export interface DashboardProps {
  userId?: string;
}

// Also export the AWS types with clearer names
export type { 
  AWSSpotOffer,
  EnrichedAWSSpotOffer,
  AWSSpotDataResponse 
} from './aws-spot';