import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Zap,
  TrendingUp,
  DollarSign,
  Activity,
  RefreshCw,
  Settings,
  Download,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  Cloud,
  Server,
  Cpu,
  HardDrive,
  Wifi,
  BarChart3,
  PieChart,
  Users,
  Shield,
  Globe,
  Eye,
  EyeOff
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Hooks and Utils
import { useAWSSpotData } from '@/hooks/useAWSSpotData';
import { 
  enrichAWSSpotOffer, 
  ensureEnrichedOffer,
  calculateOfferYieldMetrics,
  calculateInterruptionRisk,
  calculateFreshness,
  AWS_REGION_DISPLAY, 
  REGION_POWER_COSTS, 
  GPU_TDP_WATTS,
  AWS_INSTANCE_METADATA 
} from '@/lib/awsUtils';

// Types
import { 
  AWSSpotOffer, 
  EnrichedAWSSpotOffer,
  GPUData,
  MarketData,
  DashboardProps
} from '@/types';

// Chart components - you might need to install these
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Cell,
  BarChart,
  Bar
} from 'recharts';

// Dashboard specific interfaces
interface GPUData {
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

interface MarketData {
  timestamp: string;
  price: number;
  volume: number;
  platform: string;
}

interface DashboardProps {
  userId?: string;
}

// AWS Components
const InterruptionRiskIndicator: React.FC<{ availability: number }> = ({ availability }) => {
  const risk = calculateInterruptionRisk(availability); // This will now work
  const colors = {
    low: 'bg-green-500',
    medium: 'bg-yellow-500',
    high: 'bg-red-500'
  };
  
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className={`h-2 w-4 rounded ${
              i === 0 || (i === 1 && risk !== 'high') || (i === 2 && risk === 'low')
                ? colors[risk]
                : 'bg-gray-600'
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-gray-400 capitalize">{risk}</span>
    </div>
  );
};

const FreshnessIndicator: React.FC<{ timestamp?: string }> = ({ timestamp }) => {
  const freshness = calculateFreshness(timestamp); // This will now work
  const colors = {
    live: 'text-green-400',
    recent: 'text-yellow-400',
    stale: 'text-red-400'
  };
  
  return (
    <span className={`text-xs ${colors[freshness]} capitalize`}>
      {freshness}
    </span>
  );
};

const InstanceDetailsTooltip: React.FC<{ instanceType: string; className?: string }> = ({ 
  instanceType, 
  className = "" 
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const metadata = AWS_INSTANCE_METADATA[instanceType];

  if (!metadata) return <span className={className}>{instanceType}</span>;

  return (
    <div className="relative inline-block">
      <button
        className={`underline decoration-dotted hover:decoration-solid ${className}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {instanceType}
      </button>
      
      {showTooltip && (
        <div className="absolute z-10 w-64 p-3 bg-gray-900 border border-white/20 rounded-lg shadow-lg bottom-full left-0 mb-2">
          <div className="space-y-2 text-sm text-white">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gray-400" />
              <span>{metadata.vcpu} vCPUs</span>
            </div>
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-gray-400" />
              <span>{metadata.ram_gb} GB RAM</span>
            </div>
            <div className="flex items-center gap-2">
              <Wifi className="w-4 h-4 text-gray-400" />
              <span>{metadata.network}</span>
            </div>
            {metadata.storage_gb && (
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-gray-400" />
                <span>{metadata.storage_gb} GB NVMe</span>
              </div>
            )}
          </div>
          <div className="absolute w-3 h-3 bg-gray-900 border-b border-r border-white/20 transform rotate-45 -bottom-1.5 left-6"></div>
        </div>
      )}
    </div>
  );
};

const Dashboard: React.FC<DashboardProps> = ({ userId }) => {
  const [gpuData, setGpuData] = useState<GPUData[]>([]);
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [awsSpotData, setAwsSpotData] = useState<AWSSpotOffer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState('24h');
  const [selectedGPU, setSelectedGPU] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showAWSData, setShowAWSData] = useState(false);

  // Use the AWS Spot data hook - this handles WebSocket automatically
  const { 
    offers: awsOffers, 
    loading: awsLoading, 
    error: awsError,
    lastUpdated: awsLastUpdated,
    hasLiveData,
    averagePrice: awsAvgPrice
  } = useAWSSpotData({
    autoRefresh: autoRefresh,
    refreshInterval: 30000
  });

  // Mock AWS Spot data generation (keep this as is)
  const generateAWSSpotData = useCallback((): AWSSpotOffer[] => {
    const baseOffers: AWSSpotOffer[] = [
      {
        model: "A100",
        usd_hr: 1.2290 + (Math.random() - 0.5) * 0.2,
        region: "us-east-1",
        availability: 8,
        instance_type: "p4d.24xlarge",
        provider: "aws_spot" as const,
        total_instance_price: 9.832,
        gpu_memory_gb: 40,
        timestamp: new Date(Date.now() - Math.random() * 60 * 60 * 1000).toISOString(),
        synthetic: true,
      },
      {
        model: "T4",
        usd_hr: 0.1578 + (Math.random() - 0.5) * 0.05,
        region: "us-west-2",
        availability: 1,
        instance_type: "g4dn.xlarge",
        provider: "aws_spot" as const,
        total_instance_price: 0.1578,
        gpu_memory_gb: 16,
        timestamp: new Date(Date.now() - Math.random() * 2 * 60 * 60 * 1000).toISOString(),
        synthetic: true,
      },
      {
        model: "A10G",
        usd_hr: 0.3360 + (Math.random() - 0.5) * 0.1,
        region: "us-east-1",
        availability: 1,
        instance_type: "g5.xlarge",
        provider: "aws_spot" as const,
        total_instance_price: 0.3360,
        gpu_memory_gb: 24,
        timestamp: new Date(Date.now() - Math.random() * 30 * 60 * 1000).toISOString(),
        synthetic: true,
      },
      {
        model: "V100",
        usd_hr: 0.9180 + (Math.random() - 0.5) * 0.15,
        region: "eu-west-1",
        availability: 4,
        instance_type: "p3.8xlarge",
        provider: "aws_spot" as const,
        total_instance_price: 3.672,
        gpu_memory_gb: 16,
        timestamp: new Date(Date.now() - Math.random() * 10 * 60 * 1000).toISOString(),
        synthetic: true,
      },
      // Add more variety to test different scenarios
      {
        model: "H100",
        usd_hr: 2.1500 + (Math.random() - 0.5) * 0.3,
        region: "us-west-2",
        availability: 2,
        instance_type: "p5.48xlarge",
        provider: "aws_spot" as const,
        total_instance_price: 17.200,
        gpu_memory_gb: 80,
        timestamp: new Date(Date.now() - Math.random() * 15 * 60 * 1000).toISOString(),
        synthetic: true,
      },
      // Example with minimal optional fields
      {
        model: "K80",
        usd_hr: 0.0900 + (Math.random() - 0.5) * 0.02,
        region: "ap-southeast-1",
        availability: 1,
        instance_type: "p2.xlarge",
        provider: "aws_spot" as const,
        // Only include timestamp, omit other optional fields
        timestamp: new Date(Date.now() - Math.random() * 45 * 60 * 1000).toISOString(),
        synthetic: true,
      },
    ];

    return baseOffers; // Add this return statement
  }, []);

  // Regular mock data generation (no WebSocket handling needed here)
  useEffect(() => {
    const generateMockData = () => {
      const gpuModels = ['RTX 4090', 'RTX 4080', 'RTX 3090', 'RTX 3080', 'A100', 'H100'];
      const platforms = ['Vast.ai', 'RunPod', 'Lambda Labs', 'Genesis Cloud', 'AWS Spot'];
      
      const mockGPUs: GPUData[] = gpuModels.map((model, index) => {
        const platform = platforms[index % platforms.length];
        const isAWS = platform === 'AWS Spot';
        
        // Base GPU data with all required fields
        const baseGPU: GPUData = {
          model,
          platform,
          price: Math.random() * 2 + 0.5,
          utilization: Math.random() * 100,
          status: ['active', 'idle', 'error'][Math.floor(Math.random() * 3)] as 'active' | 'idle' | 'error',
          earnings: Math.random() * 500 + 100,
          powerDraw: Math.random() * 400 + 200,
          temperature: Math.random() * 30 + 50,
          lastUpdate: new Date().toISOString(),
        };
        
        // Add AWS-specific optional fields only if it's an AWS platform
        if (isAWS) {
          return {
            ...baseGPU,
            region: ['us-east-1', 'us-west-2', 'eu-west-1'][Math.floor(Math.random() * 3)],
            instanceType: ['p4d.24xlarge', 'g4dn.xlarge', 'g5.xlarge'][Math.floor(Math.random() * 3)],
            interruptionRisk: calculateInterruptionRisk(Math.floor(Math.random() * 8) + 1),
            netYield: Math.random() * 1.5 + 0.5,
            margin: Math.random() * 80 + 20
          };
        }
        
        return baseGPU;
      });

      const mockMarket: MarketData[] = Array.from({ length: 24 }, (_, i) => ({
        timestamp: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
        price: Math.random() * 0.5 + 1.0,
        volume: Math.random() * 1000 + 500,
        platform: platforms[Math.floor(Math.random() * platforms.length)]
      }));

      const awsSpot = generateAWSSpotData();

      setGpuData(mockGPUs);
      setMarketData(mockMarket);
      setAwsSpotData(awsSpot);
      setIsLoading(false);
    };

    generateMockData();
    
    if (autoRefresh) {
      const interval = setInterval(generateMockData, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, generateAWSSpotData]);

  // Computed values with AWS data
  const totalEarnings = useMemo(() => 
    gpuData.reduce((sum, gpu) => sum + gpu.earnings, 0), 
    [gpuData]
  );

  const totalPowerDraw = useMemo(() => 
    gpuData.reduce((sum, gpu) => sum + gpu.powerDraw, 0), 
    [gpuData]
  );

  const averageUtilization = useMemo(() => 
    gpuData.length > 0 ? gpuData.reduce((sum, gpu) => sum + gpu.utilization, 0) / gpuData.length : 0, 
    [gpuData]
  );

  const activeGPUs = useMemo(() => 
    gpuData.filter(gpu => gpu.status === 'active').length, 
    [gpuData]
  );

  // Update AWS metrics calculation to use type guards
  const awsSpotMetrics = useMemo(() => {
    const totalOffers = awsOffers.length;
    const avgPrice = totalOffers > 0 ? awsOffers.reduce((sum, offer) => sum + offer.usd_hr, 0) / totalOffers : 0;
    
    let lowRiskOffers = 0;
    let liveOffers = 0;
    
    awsOffers.forEach((offer: EnrichedAWSSpotOffer) => { // Explicit type
      if (offer.interruption_risk === 'low') {
        lowRiskOffers++;
      }
      if (offer.freshness === 'live') {
        liveOffers++;
      }
    });
    
    return { totalOffers, avgPrice, lowRiskOffers, liveOffers };
  }, [awsOffers]);

  const chartData = useMemo(() => {
    return marketData.map(data => ({
      time: new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      price: parseFloat(data.price.toFixed(3)),
      volume: Math.round(data.volume)
    }));
  }, [marketData]);

  const pieData = useMemo(() => {
    const platformEarnings = gpuData.reduce((acc, gpu) => {
      acc[gpu.platform] = (acc[gpu.platform] || 0) + gpu.earnings;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(platformEarnings).map(([platform, earnings]) => ({
      name: platform,
      value: earnings,
      fill: platform === 'AWS Spot' ? '#FF6B35' : `hsl(${Math.random() * 360}, 70%, 50%)`
    }));
  }, [gpuData]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-400 bg-green-500/10 border-green-500/20';
      case 'idle': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
      case 'error': return 'text-red-400 bg-red-500/10 border-red-500/20';
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="w-4 h-4" />;
      case 'idle': return <Clock className="w-4 h-4" />;
      case 'error': return <XCircle className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">GPU Dashboard</h1>
            <p className="text-gray-400">Monitor your GPU performance and earnings in real-time</p>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAWSData(!showAWSData)}
              className="border-white/20 text-white hover:bg-white/10"
            >
              <Cloud className="w-4 h-4 mr-2" />
              {showAWSData ? 'Hide' : 'Show'} AWS Spot
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="border-white/20 text-white hover:bg-white/10"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Auto' : 'Manual'}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              className="border-white/20 text-white hover:bg-white/10"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              className="border-white/20 text-white hover:bg-white/10"
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        {/* Key Metrics - Enhanced with AWS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm font-medium">Total Earnings</p>
                  <p className="text-3xl font-bold text-white">${totalEarnings.toFixed(2)}</p>
                  <div className="flex items-center mt-2">
                    <TrendingUp className="w-4 h-4 text-green-400 mr-1" />
                    <span className="text-green-400 text-sm">+12.5%</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm font-medium">Active GPUs</p>
                  <p className="text-3xl font-bold text-white">{activeGPUs}</p>
                  <div className="flex items-center mt-2">
                    <Activity className="w-4 h-4 text-blue-400 mr-1" />
                    <span className="text-blue-400 text-sm">of {gpuData.length} total</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <Server className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm font-medium">AWS Spot Offers</p>
                  <p className="text-3xl font-bold text-white">{awsSpotMetrics.totalOffers}</p>
                  <div className="flex items-center mt-2">
                    <Cloud className="w-4 h-4 text-orange-400 mr-1" />
                    <span className="text-orange-400 text-sm">
                      ${awsSpotMetrics.avgPrice.toFixed(3)} avg
                      {hasLiveData && <span className="ml-2 text-green-400">● LIVE</span>}
                    </span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-600 rounded-xl flex items-center justify-center">
                  <Cloud className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm font-medium">Power Draw</p>
                  <p className="text-3xl font-bold text-white">{totalPowerDraw.toFixed(0)}W</p>
                  <div className="flex items-center mt-2">
                    <Zap className="w-4 h-4 text-yellow-400 mr-1" />
                    <span className="text-yellow-400 text-sm">-5.3%</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-600 rounded-xl flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* AWS Spot Data Table - Conditional Display */}
        {showAWSData && (
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white flex items-center gap-2">
                  <Cloud className="w-5 h-5" />
                  AWS Spot GPU Pricing
                  {awsLoading && <Loader2 className="w-4 h-4 animate-spin ml-2" />}
                </CardTitle>
                {awsLastUpdated && (
                  <span className="text-sm text-gray-400">
                    Updated: {new Date(awsLastUpdated).toLocaleTimeString()}
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {awsError && (
                <div className="text-red-400 mb-4 p-3 bg-red-500/10 rounded">
                  Error loading AWS data: {awsError}
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left text-gray-400 font-medium py-3 px-4">GPU Model</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">$/hr per GPU</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">Net Yield</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">Region</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">Risk</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">Instance</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">VRAM</th>
                      <th className="text-left text-gray-400 font-medium py-3 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {awsOffers.slice(0, 10).map((offer: EnrichedAWSSpotOffer, index: number) => { // Explicit types
                      const yieldData = calculateOfferYieldMetrics(offer);
                      const enriched = ensureEnrichedOffer(offer);
                      
                      return (
                        <tr 
                          key={`${offer.model}-${offer.region}-${index}`} 
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        >
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                                <Cloud className="w-4 h-4 text-white" />
                              </div>
                              <span className="text-white font-medium">{offer.model}</span>
                              {offer.synthetic && (
                                <Badge className="bg-gray-500/10 text-gray-400 border-gray-500/20 text-xs">
                                  MOCK
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-green-400 font-mono text-lg">
                              ${offer.usd_hr.toFixed(4)}
                            </span>
                            {yieldData.totalInstancePrice > 0 && (
                              <div className="text-xs text-gray-500">
                                Total: ${yieldData.totalInstancePrice.toFixed(4)}
                              </div>
                            )}
                          </td>
                          <td className="py-4 px-4">
                            <div>
                              <span className={yieldData.netYield > 0 ? 'text-green-400' : 'text-red-400'}>
                                ${yieldData.netYield.toFixed(4)}
                              </span>
                              <div className="text-xs text-gray-500">
                                Power: ${yieldData.powerCostPerHour.toFixed(3)}
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                              {AWS_REGION_DISPLAY[offer.region] ?? offer.region}
                            </Badge>
                          </td>
                          <td className="py-4 px-4">
                            <InterruptionRiskIndicator availability={offer.availability} />
                          </td>
                          <td className="py-4 px-4">
                            <InstanceDetailsTooltip 
                              instanceType={offer.instance_type} 
                              className="text-blue-400 hover:text-blue-300"
                            />
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-white">{yieldData.gpuMemory} GB</span>
                          </td>
                          <td className="py-4 px-4">
                            <FreshnessIndicator timestamp={offer.timestamp} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Charts Row - Enhanced with AWS data in pie chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Price Chart */}
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Price Trends (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#9CA3AF"
                    fontSize={12}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    fontSize={12}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#fff'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="price" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Platform Distribution */}
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Earnings by Platform
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#fff'
                    }}
                    formatter={(value: number) => [`${value.toFixed(2)}`, 'Earnings']}
                  />
                  <Legend 
                    wrapperStyle={{ color: '#9CA3AF', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* GPU List */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <Server className="w-5 h-5" />
                GPU Overview
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/20 text-white hover:bg-white/10"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filter
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/20 text-white hover:bg-white/10"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  View All
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left text-gray-400 font-medium py-3 px-4">GPU</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Platform</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Status</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Price/hr</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Utilization</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Earnings</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Region</th>
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gpuData.map((gpu, index) => (
                    <tr 
                      key={index} 
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 ${
                            gpu.platform === 'AWS Spot' 
                              ? 'bg-gradient-to-r from-orange-500 to-red-600' 
                              : 'bg-gradient-to-r from-blue-500 to-purple-600'
                          } rounded-lg flex items-center justify-center`}>
                            {gpu.platform === 'AWS Spot' ? (
                              <Cloud className="w-5 h-5 text-white" />
                            ) : (
                              <Server className="w-5 h-5 text-white" />
                            )}
                          </div>
                          <div>
                            <p className="text-white font-medium">{gpu.model}</p>
                            <p className="text-gray-400 text-sm">ID: GPU-{index + 1}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={`${
                          gpu.platform === 'AWS Spot'
                            ? 'bg-orange-500/10 text-orange-400 border-orange-500/20'
                            : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                        }`}>
                          {gpu.platform}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={`${getStatusColor(gpu.status)} flex items-center gap-1 w-fit`}>
                          {getStatusIcon(gpu.status)}
                          {gpu.status}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-white font-mono">
                          ${gpu.price.toFixed(3)}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all"
                              style={{ width: `${gpu.utilization}%` }}
                            />
                          </div>
                          <span className="text-white text-sm font-mono">
                            {gpu.utilization.toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-1">
                          <DollarSign className="w-4 h-4 text-green-400" />
                          <span className="text-white font-mono">
                            {gpu.earnings.toFixed(2)}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        {gpu.region ? (
                          <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                            {gpu.region}
                          </Badge>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-gray-400 hover:text-white hover:bg-white/10"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-gray-400 hover:text-white hover:bg-white/10"
                          >
                            <Settings className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* AWS Spot Insights Panel */}
        {showAWSData && (
          <Card className="bg-gradient-to-r from-orange-500/10 to-red-500/10 border-orange-500/20 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Cloud className="w-5 h-5 text-orange-400" />
                AWS Spot Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <h3 className="font-medium mb-2 text-orange-400">Cost Efficiency</h3>
                  <ul className="text-sm space-y-1 text-gray-300">
                    <li>• Net yield accounts for regional power costs</li>
                    <li>• EU regions have higher power costs</li>
                    <li>• US West typically offers best margins</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium mb-2 text-orange-400">Interruption Risk</h3>
                  <ul className="text-sm space-y-1 text-gray-300">
                    <li>• Multi-GPU instances = lower risk</li>
                    <li>• Monitor capacity trends</li>
                    <li>• Have fallback instances ready</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium mb-2 text-orange-400">Best Practices</h3>
                  <ul className="text-sm space-y-1 text-gray-300">
                    <li>• Use spot fleets for resilience</li>
                    <li>• Set competitive max prices</li>
                    <li>• Diversify across regions</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Dashboard;