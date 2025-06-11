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
  EyeOff,
  Filter  // Add missing Filter import
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

// Types - Use renamed types to avoid conflicts
import { 
  AWSSpotOffer, 
  EnrichedAWSSpotOffer,
  DashboardGPUData as GPUData,  // Use renamed type
  DashboardMarketData as MarketData,  // Use renamed type
  DashboardProps
} from '@/types';

// Chart components
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

// AWS Components
const InterruptionRiskIndicator: React.FC<{ availability: number }> = ({ availability }) => {
  const risk = calculateInterruptionRisk(availability);
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
  const freshness = calculateFreshness(timestamp);
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
    averagePrice: awsAvgPrice,
    refetch: refetchAWS
  } = useAWSSpotData({
    autoRefresh: autoRefresh,
    refreshInterval: 30000
  });

  // Mock AWS Spot data generation
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
      {
        model: "K80",
        usd_hr: 0.0900 + (Math.random() - 0.5) * 0.02,
        region: "ap-southeast-1",
        availability: 1,
        instance_type: "p2.xlarge",
        provider: "aws_spot" as const,
        timestamp: new Date(Date.now() - Math.random() * 45 * 60 * 1000).toISOString(),
        synthetic: true,
      },
    ];

    return baseOffers;
  }, []);

  // Regular mock data generation
  useEffect(() => {
    const generateMockData = () => {
      const gpuModels = ['RTX 4090', 'RTX 4080', 'RTX 3090', 'RTX 3080', 'A100', 'H100'];
      const platforms = ['Vast.ai', 'RunPod', 'Lambda Labs', 'Genesis Cloud', 'AWS Spot'];
      
      const mockGPUs: GPUData[] = gpuModels.map((model, index) => {
        const platform = platforms[index % platforms.length];
        const isAWS = platform === 'AWS Spot';
        
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

  // AWS metrics calculation with proper typing
  const awsSpotMetrics = useMemo(() => {
    const totalOffers = awsOffers.length;
    const avgPrice = totalOffers > 0 ? awsOffers.reduce((sum, offer) => sum + offer.usd_hr, 0) / totalOffers : 0;
    
    let lowRiskOffers = 0;
    let liveOffers = 0;
    
    awsOffers.forEach((offer: EnrichedAWSSpotOffer) => {
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
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              {showAWSData ? <EyeOff className="w-4 h-4 mr-2" /> : <Eye className="w-4 h-4 mr-2" />}
              AWS Data
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              Auto-refresh
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Total Earnings</CardTitle>
              <DollarSign className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">${totalEarnings.toFixed(2)}</div>
              <p className="text-xs text-gray-400">
                +20.1% from last month
              </p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Active GPUs</CardTitle>
              <Zap className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{activeGPUs}</div>
              <p className="text-xs text-gray-400">
                of {gpuData.length} total
              </p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Avg Utilization</CardTitle>
              <Activity className="h-4 w-4 text-yellow-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{averageUtilization.toFixed(1)}%</div>
              <p className="text-xs text-gray-400">
                +5.2% from yesterday
              </p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Power Draw</CardTitle>
              <Zap className="h-4 w-4 text-red-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{totalPowerDraw.toFixed(0)}W</div>
              <p className="text-xs text-gray-400">
                Average load
              </p>
            </CardContent>
          </Card>
        </div>

        {/* AWS Spot Data Section */}
        {showAWSData && (
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Cloud className="w-5 h-5 text-orange-400" />
                AWS Spot GPU Pricing
                {awsLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {awsError ? (
                <div className="text-red-400 p-4 bg-red-500/10 rounded-lg">
                  Error loading AWS data: {awsError}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* AWS Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <div className="text-2xl font-bold text-white">{awsSpotMetrics.totalOffers}</div>
                      <div className="text-sm text-gray-400">Total Offers</div>
                    </div>
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <div className="text-2xl font-bold text-green-400">${awsSpotMetrics.avgPrice.toFixed(3)}</div>
                      <div className="text-sm text-gray-400">Avg Price/hr</div>
                    </div>
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <div className="text-2xl font-bold text-blue-400">{awsSpotMetrics.lowRiskOffers}</div>
                      <div className="text-sm text-gray-400">Low Risk</div>
                    </div>
                    <div className="text-center p-3 bg-white/5 rounded-lg">
                      <div className="text-2xl font-bold text-yellow-400">{awsSpotMetrics.liveOffers}</div>
                      <div className="text-sm text-gray-400">Live Data</div>
                    </div>
                  </div>

                  {/* AWS Offers Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10">
                          <th className="text-left text-gray-400 pb-2">GPU Model</th>
                          <th className="text-left text-gray-400 pb-2">Region</th>
                          <th className="text-left text-gray-400 pb-2">Price/hr</th>
                          <th className="text-left text-gray-400 pb-2">Instance Type</th>
                          <th className="text-left text-gray-400 pb-2">Availability</th>
                          <th className="text-left text-gray-400 pb-2">Risk</th>
                          <th className="text-left text-gray-400 pb-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {awsOffers.slice(0, 10).map((offer: EnrichedAWSSpotOffer, index: number) => {
                          const yieldData = calculateOfferYieldMetrics(offer);
                          const enriched = ensureEnrichedOffer(offer);
                          
                          return (
                            <tr 
                              key={`${offer.model}-${offer.region}-${index}`} 
                              className="border-b border-white/5 hover:bg-white/5 transition-colors"
                            >
                              <td className="py-2 text-white font-medium">{offer.model}</td>
                              <td className="py-2 text-gray-300">
                                {AWS_REGION_DISPLAY[offer.region] || offer.region}
                              </td>
                              <td className="py-2 text-green-400 font-mono">
                                ${offer.usd_hr.toFixed(4)}
                              </td>
                              <td className="py-2">
                                <InstanceDetailsTooltip 
                                  instanceType={offer.instance_type}
                                  className="text-blue-400"
                                />
                              </td>
                              <td className="py-2 text-gray-300">{offer.availability}</td>
                              <td className="py-2">
                                <InterruptionRiskIndicator availability={offer.availability} />
                              </td>
                              <td className="py-2">
                                <FreshnessIndicator timestamp={offer.timestamp} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {awsLastUpdated && (
                    <div className="text-xs text-gray-500 mt-2">
                      Last updated: {new Date(awsLastUpdated).toLocaleString()}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Charts and additional content would go here */}
      </div>
    </div>
  );
};

export default Dashboard;