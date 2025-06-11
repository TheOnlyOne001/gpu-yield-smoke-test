// Re-export all AWS Spot types
export * from './aws-spot';

// Dashboard specific types
export interface GPUData {
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

export interface MarketData {
  timestamp: string;
  price: number;
  volume: number;
  platform: string;
}

export interface DashboardProps {
  userId?: string;
}