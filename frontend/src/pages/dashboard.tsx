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
  PieChart as PieChartIcon, // Rename to avoid conflict
  Users,
  Shield,
  Globe,
  Eye,
  EyeOff,
  Filter,
  ChevronDown,
  Search,
  ExternalLink,
  AlertCircle,
  Info,
  Gauge,
  Timer,
  DollarSign as Dollar,
  Power,
  Thermometer,
  Network
} from 'lucide-react';
import { useRouter } from 'next/router';
import useSWR from 'swr';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Hooks and Utils
import { useAWSSpotData, useAWSRegions, useAWSModels } from '@/hooks/useAWSSpotData';
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
import { formatTimeAgo, getDataFreshness } from '@/lib/fetcher';
import SyncStatusBadge from '@/components/SyncStatusBadge';

// Types
import { 
  AWSSpotOffer, 
  EnrichedAWSSpotOffer,
  DashboardGPUData as GPUData,
  DashboardMarketData as MarketData,
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
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from '@/components/charts/DynamicCharts';

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Fetcher for SWR
const fetcher = (url: string) => fetch(url).then(res => res.json());

// AWS Components
const InterruptionRiskIndicator: React.FC<{ availability: number }> = ({ availability }) => {
  const risk = calculateInterruptionRisk(availability);
  const config = {
    low: { color: 'bg-green-500', text: 'text-green-400', label: 'Low Risk' },
    medium: { color: 'bg-yellow-500', text: 'text-yellow-400', label: 'Medium Risk' },
    high: { color: 'bg-red-500', text: 'text-red-400', label: 'High Risk' }
  };
  
  const { color, text, label } = config[risk];
  
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className={`h-2 w-4 rounded transition-colors ${
              i === 0 || (i === 1 && risk !== 'high') || (i === 2 && risk === 'low')
                ? color
                : 'bg-gray-600'
            }`}
          />
        ))}
      </div>
      <span className={`text-xs ${text} capitalize`}>{label}</span>
    </div>
  );
};

const FreshnessIndicator: React.FC<{ timestamp?: string }> = ({ timestamp }) => {
  const freshness = calculateFreshness(timestamp);
  const config = {
    live: { icon: <Activity className="w-3 h-3" />, color: 'text-green-400', pulse: true },
    recent: { icon: <Clock className="w-3 h-3" />, color: 'text-yellow-400', pulse: false },
    stale: { icon: <AlertTriangle className="w-3 h-3" />, color: 'text-red-400', pulse: false }
  };
  
  const { icon, color, pulse } = config[freshness];
  
  return (
    <div className={`flex items-center gap-1 ${color}`}>
      <div className={pulse ? 'animate-pulse' : ''}>{icon}</div>
      <span className="text-xs capitalize">{freshness}</span>
    </div>
  );
};

const InstanceDetailsPopover: React.FC<{ instanceType: string }> = ({ instanceType }) => {
  const [showDetails, setShowDetails] = useState(false);
  const metadata = AWS_INSTANCE_METADATA[instanceType];

  if (!metadata) return <span className="text-blue-400">{instanceType}</span>;

  return (
    <div className="relative">
      <button
        className="text-blue-400 underline decoration-dotted hover:decoration-solid transition-all"
        onMouseEnter={() => setShowDetails(true)}
        onMouseLeave={() => setShowDetails(false)}
      >
        {instanceType}
      </button>
      
      {showDetails && (
        <div className="absolute z-20 w-72 p-4 bg-gray-900 border border-white/20 rounded-lg shadow-xl bottom-full left-0 mb-2">
          <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
            <Server className="w-4 h-4" />
            Instance Details
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-2 text-gray-300">
              <Cpu className="w-3 h-3 text-gray-500" />
              <span>{metadata.vcpu} vCPUs</span>
            </div>
            <div className="flex items-center gap-2 text-gray-300">
              <Server className="w-3 h-3 text-gray-500" />
              <span>{metadata.ram_gb} GB RAM</span>
            </div>
            <div className="flex items-center gap-2 text-gray-300">
              <Wifi className="w-3 h-3 text-gray-500" />
              <span>{metadata.network}</span>
            </div>
            {metadata.storage_gb && metadata.storage_gb > 0 && (
              <div className="flex items-center gap-2 text-gray-300">
                <HardDrive className="w-3 h-3 text-gray-500" />
                <span>{metadata.storage_gb} GB SSD</span>
              </div>
            )}
          </div>
          {metadata.ebs_optimized && (
            <Badge className="mt-2 bg-blue-500/10 text-blue-400 border-blue-500/20 text-xs">
              EBS Optimized
            </Badge>
          )}
          <div className="absolute w-3 h-3 bg-gray-900 border-b border-r border-white/20 transform rotate-45 -bottom-1.5 left-6"></div>
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
const Dashboard: React.FC<DashboardProps> = ({ userId }) => {
  const router = useRouter();
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [minAvailability, setMinAvailability] = useState<number>(1);
  const [viewType, setViewType] = useState<'operator' | 'renter'>('operator');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch live AWS Spot data
  const { 
    offers: awsOffers, 
    loading: awsLoading, 
    error: awsError,
    lastUpdated: awsLastUpdated,
    totalCount,
    metadata,
    refetch: refetchAWS,
    hasLiveData,
    hasSyntheticData,
    averagePrice: awsAvgPrice,
    uniqueModels,
    uniqueRegions
  } = useAWSSpotData({
    region: selectedRegion,
    model: selectedModel,
    minAvailability,
    viewType,
    autoRefresh,
    refreshInterval: 30000
  });

  // Fetch regions and models for filters
  const { regions, loading: regionsLoading } = useAWSRegions();
  const { models, loading: modelsLoading } = useAWSModels();

  // Fetch general stats
  const { data: statsData } = useSWR(`${API_BASE_URL}/stats`, fetcher, {
    refreshInterval: 60000
  });

  // Calculate metrics
  const metrics = useMemo(() => {
    const totalOffers = awsOffers.length;
    const avgPrice = totalOffers > 0 ? awsOffers.reduce((sum, offer) => sum + offer.usd_hr, 0) / totalOffers : 0;
    
    let lowRiskCount = 0;
    let highYieldCount = 0;
    let liveDataCount = 0;
    
    awsOffers.forEach((offer: EnrichedAWSSpotOffer) => {
      if (offer.interruption_risk === 'low') lowRiskCount++;
      if (offer.freshness === 'live') liveDataCount++;
      
      const yieldMetrics = calculateOfferYieldMetrics(offer);
      if (yieldMetrics.netYield > 1.0) highYieldCount++;
    });
    
    return {
      totalOffers,
      avgPrice,
      lowRiskCount,
      highYieldCount,
      liveDataCount,
      lowRiskPercentage: totalOffers > 0 ? (lowRiskCount / totalOffers) * 100 : 0,
      highYieldPercentage: totalOffers > 0 ? (highYieldCount / totalOffers) * 100 : 0
    };
  }, [awsOffers]);

  // Price history data for charts
  const priceHistoryData = useMemo(() => {
    const modelPrices: Record<string, number[]> = {};
    
    awsOffers.forEach(offer => {
      if (!modelPrices[offer.model]) {
        modelPrices[offer.model] = [];
      }
      modelPrices[offer.model].push(offer.usd_hr);
    });

    return Object.entries(modelPrices).map(([model, prices]) => ({
      model,
      avgPrice: prices.reduce((a, b) => a + b, 0) / prices.length,
      minPrice: Math.min(...prices),
      maxPrice: Math.max(...prices),
      count: prices.length
    }));
  }, [awsOffers]);

  // Regional distribution data
  const regionalData = useMemo(() => {
    const regionCounts: Record<string, number> = {};
    const regionPrices: Record<string, number[]> = {};
    
    awsOffers.forEach(offer => {
      const region = offer.region;
      regionCounts[region] = (regionCounts[region] || 0) + 1;
      if (!regionPrices[region]) regionPrices[region] = [];
      regionPrices[region].push(offer.usd_hr);
    });

    return Object.entries(regionCounts).map(([region, count]) => ({
      region: AWS_REGION_DISPLAY[region] || region,
      count,
      avgPrice: regionPrices[region].reduce((a, b) => a + b, 0) / regionPrices[region].length
    }));
  }, [awsOffers]);

  // Filter offers based on search
  const filteredOffers = useMemo(() => {
    if (!searchQuery) return awsOffers;
    
    const query = searchQuery.toLowerCase();
    return awsOffers.filter(offer => 
      offer.model.toLowerCase().includes(query) ||
      offer.region.toLowerCase().includes(query) ||
      offer.instance_type.toLowerCase().includes(query)
    );
  }, [awsOffers, searchQuery]);

  // Export data function
  const exportToCSV = useCallback(() => {
    const headers = ['Model', 'Region', 'Price/hr', 'Instance Type', 'Availability', 'Risk', 'Net Yield', 'Timestamp'];
    const rows = filteredOffers.map(offer => {
      const yieldMetrics = calculateOfferYieldMetrics(offer);
      return [
        offer.model,
        offer.region,
        `$${offer.usd_hr.toFixed(4)}`,
        offer.instance_type,
        offer.availability,
        offer.interruption_risk,
        `$${yieldMetrics.netYield.toFixed(4)}`,
        offer.timestamp || new Date().toISOString()
      ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aws-spot-prices-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }, [filteredOffers]);

  // Loading state
  if (awsLoading && awsOffers.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Loading live AWS Spot data...</p>
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
            <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
              AWS Spot GPU Dashboard
              <Badge className={`${hasLiveData ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
                {hasLiveData ? 'Live Data' : hasSyntheticData ? 'Demo Data' : 'No Data'}
              </Badge>
            </h1>
            <p className="text-gray-400">Real-time AWS Spot instance pricing and availability</p>
          </div>
          
          <div className="flex items-center gap-3">
            <SyncStatusBadge 
              timestamp={awsLastUpdated ? new Date(awsLastUpdated).getTime() : undefined} 
              isLoading={awsLoading}
            />
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters {showFilters ? <ChevronDown className="w-4 h-4 ml-1 rotate-180" /> : <ChevronDown className="w-4 h-4 ml-1" />}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Auto' : 'Manual'}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={refetchAWS}
              disabled={awsLoading}
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              <RefreshCw className={`w-4 h-4 ${awsLoading ? 'animate-spin' : ''}`} />
            </Button>
            
            <Button
              size="sm"
              onClick={exportToCSV}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Filters Section */}
        {showFilters && (
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Search</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search models, regions..."
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Region</label>
                  <select
                    value={selectedRegion}
                    onChange={(e) => setSelectedRegion(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Regions</option>
                    {regions.map(region => (
                      <option key={region.code} value={region.code}>{region.name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">GPU Model</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Models</option>
                    {models.map(model => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Min Availability</label>
                  <input
                    type="number"
                    value={minAvailability}
                    onChange={(e) => setMinAvailability(parseInt(e.target.value) || 1)}
                    min="1"
                    max="8"
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Total Offers</CardTitle>
              <Cloud className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{metrics.totalOffers}</div>
              <p className="text-xs text-gray-400">
                {uniqueModels.length} models, {uniqueRegions.length} regions
              </p>
              <div className="mt-2">
                <Badge className={`text-xs ${metadata.dataSource === 'live' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
                  {metadata.dataSource === 'live' ? 'Live Data' : 'Synthetic Data'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Average Price</CardTitle>
              <DollarSign className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">${metrics.avgPrice.toFixed(3)}</div>
              <p className="text-xs text-gray-400">
                per GPU hour
              </p>
              <div className="mt-2 flex items-center gap-2">
                <Gauge className="w-3 h-3 text-blue-400" />
                <span className="text-xs text-gray-400">Market average</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Low Risk Offers</CardTitle>
              <Shield className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{metrics.lowRiskCount}</div>
              <p className="text-xs text-gray-400">
                {metrics.lowRiskPercentage.toFixed(1)}% of total
              </p>
              <div className="mt-2">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${metrics.lowRiskPercentage}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">High Yield</CardTitle>
              <TrendingUp className="h-4 w-4 text-purple-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{metrics.highYieldCount}</div>
              <p className="text-xs text-gray-400">
                &gt;$1/hr net profit
              </p>
              <div className="mt-2">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${metrics.highYieldPercentage}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Price by Model Chart */}
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-400" />
                Price by GPU Model
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={priceHistoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="model" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                  <Bar dataKey="avgPrice" fill="#3B82F6" />
                  <Bar dataKey="minPrice" fill="#10B981" />
                  <Bar dataKey="maxPrice" fill="#EF4444" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Regional Distribution */}
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Globe className="w-5 h-5 text-purple-400" />
                Regional Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={regionalData}
                    dataKey="count"
                    nameKey="region"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label
                  >
                    {regionalData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={`hsl(${index * 45}, 70%, 50%)`} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* AWS Spot Offers Table */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cloud className="w-5 h-5 text-orange-400" />
                Live AWS Spot GPU Offers
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-400">Showing {filteredOffers.length} of {totalCount}</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {awsError ? (
              <div className="text-red-400 p-4 bg-red-500/10 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Error loading AWS data: {awsError}
              </div>
            ) : filteredOffers.length === 0 ? (
              <div className="text-gray-400 p-8 text-center">
                <Info className="w-8 h-8 mx-auto mb-2 text-gray-500" />
                <p>No offers match your current filters.</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSelectedRegion('');
                    setSelectedModel('');
                    setMinAvailability(1);
                    setSearchQuery('');
                  }}
                  className="mt-4 text-gray-300 border-gray-600 hover:bg-gray-700"
                >
                  Clear Filters
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left text-gray-400 pb-3 px-2">GPU Model</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Region</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Price/hr</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Instance</th>
                      <th className="text-center text-gray-400 pb-3 px-2">GPUs</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Risk</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Net Yield</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Status</th>
                      <th className="text-left text-gray-400 pb-3 px-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOffers.slice(0, 20).map((offer: EnrichedAWSSpotOffer, index: number) => {
                      const yieldData = calculateOfferYieldMetrics(offer);
                      const enriched = ensureEnrichedOffer(offer);
                      
                      return (
                        <tr 
                          key={`${offer.model}-${offer.region}-${offer.instance_type}-${index}`} 
                          className="border-b border-white/5 hover:bg-white/5 transition-colors group"
                        >
                          <td className="py-3 px-2">
                            <div className="flex items-center gap-2">
                              <Cpu className="w-4 h-4 text-gray-500" />
                              <div>
                                <div className="text-white font-medium">{offer.model}</div>
                                {offer.gpu_memory_gb && (
                                  <div className="text-xs text-gray-500">{offer.gpu_memory_gb}GB VRAM</div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-2">
                            <div className="flex items-center gap-2">
                              <Globe className="w-4 h-4 text-gray-500" />
                              <div>
                                <div className="text-gray-300">
                                  {AWS_REGION_DISPLAY[offer.region] || offer.region}
                                </div>
                                <div className="text-xs text-gray-500">{offer.region}</div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-2">
                            <div>
                              <div className="text-green-400 font-mono font-medium">
                                ${offer.usd_hr.toFixed(4)}
                              </div>
                              {offer.total_instance_price && (
                                <div className="text-xs text-gray-500">
                                  ${offer.total_instance_price.toFixed(2)} total
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-2">
                            <InstanceDetailsPopover instanceType={offer.instance_type} />
                          </td>
                          <td className="py-3 px-2 text-center">
                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                              {offer.availability}
                            </Badge>
                          </td>
                          <td className="py-3 px-2">
                            <InterruptionRiskIndicator availability={offer.availability} />
                          </td>
                          <td className="py-3 px-2">
                            <div className={`font-mono ${yieldData.netYield > 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ${yieldData.netYield.toFixed(3)}/hr
                              <div className="text-xs text-gray-500">
                                {yieldData.margin.toFixed(1)}% margin
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-2">
                            <FreshnessIndicator timestamp={offer.timestamp} />
                          </td>
                          <td className="py-3 px-2">
                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 p-1"
                                onClick={() => {
                                  window.open(
                                    `https://console.aws.amazon.com/ec2/v2/home?region=${offer.region}#LaunchInstances:`,
                                    '_blank'
                                  );
                                }}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-gray-400 hover:text-gray-300 hover:bg-gray-500/10 p-1"
                                onClick={() => {
                                  navigator.clipboard.writeText(
                                    `${offer.model} - ${offer.region} - ${offer.usd_hr}/hr - ${offer.instance_type}`
                                  );
                                }}
                              >
                                <Info className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                
                {filteredOffers.length > 20 && (
                  <div className="mt-4 text-center">
                    <p className="text-sm text-gray-400 mb-2">
                      Showing 20 of {filteredOffers.length} offers
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push('/aws-spot')}
                      className="text-blue-400 border-blue-500/20 hover:bg-blue-500/10"
                    >
                      View All AWS Spot Offers
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Last Updated Info */}
            {awsLastUpdated && (
              <div className="mt-4 flex items-center justify-between text-xs text-gray-500 border-t border-white/10 pt-4">
                <div className="flex items-center gap-2">
                  <Clock className="w-3 h-3" />
                  Last updated: {formatTimeAgo(new Date(awsLastUpdated).getTime())}
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Live data</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span>Recent</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span>Stale</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Additional Insights Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Best Deals Card */}
          <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                Best Deals Right Now
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {awsOffers
                .sort((a, b) => {
                  const aYield = calculateOfferYieldMetrics(a).netYield;
                  const bYield = calculateOfferYieldMetrics(b).netYield;
                  return bYield - aYield;
                })
                .slice(0, 3)
                .map((offer, idx) => {
                  const yieldData = calculateOfferYieldMetrics(offer);
                  return (
                    <div key={idx} className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-white font-medium">{offer.model}</span>
                        <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-xs">
                          ${yieldData.netYield.toFixed(2)}/hr profit
                        </Badge>
                      </div>
                      <div className="text-xs text-gray-400 space-y-1">
                        <div className="flex justify-between">
                          <span>{AWS_REGION_DISPLAY[offer.region] || offer.region}</span>
                          <span>${offer.usd_hr.toFixed(3)}/hr</span>
                        </div>
                        <div className="flex justify-between">
                          <span>{offer.instance_type}</span>
                          <InterruptionRiskIndicator availability={offer.availability} />
                        </div>
                      </div>
                    </div>
                  );
                })}
            </CardContent>
          </Card>

          {/* Power Cost Analysis */}
          <Card className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border-yellow-500/20 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Power className="w-5 h-5 text-yellow-400" />
                Power Cost Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(REGION_POWER_COSTS)
                  .sort(([, a], [, b]) => a - b)
                  .slice(0, 5)
                  .map(([region, cost]) => (
                    <div key={region} className="flex items-center justify-between p-2 bg-white/5 rounded-lg">
                      <span className="text-gray-300">{AWS_REGION_DISPLAY[region] || region}</span>
                      <div className="flex items-center gap-2">
                        <Zap className="w-3 h-3 text-yellow-400" />
                        <span className="text-white font-mono">${cost.toFixed(3)}/kWh</span>
                      </div>
                    </div>
                  ))}
              </div>
              <div className="mt-3 p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                <p className="text-xs text-blue-400">
                  💡 Tip: Choose regions with lower power costs to maximize profit margins
                </p>
              </div>
            </CardContent>
          </Card>

          {/* System Health */}
          <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-purple-400" />
                System Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-300 flex items-center gap-2">
                    <Wifi className="w-4 h-4 text-gray-500" />
                    API Status
                  </span>
                  <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                    Operational
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-300 flex items-center gap-2">
                    <Server className="w-4 h-4 text-gray-500" />
                    Data Pipeline
                  </span>
                  <Badge className={`${hasLiveData ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
                    {hasLiveData ? 'Live' : 'Synthetic'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-300 flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-gray-500" />
                    Update Rate
                  </span>
                  <span className="text-white font-mono text-sm">30s</span>
                </div>
              </div>
              
              {statsData && (
                <div className="pt-3 border-t border-white/10">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Total GPUs Tracked</span>
                    <span className="text-purple-400 font-bold">{statsData.gpu_count?.toLocaleString() || '—'}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Footer Info */}
        <div className="text-center text-xs text-gray-500 mt-8">
          <p>AWS Spot prices are subject to change. Always verify current pricing before launching instances.</p>
          <p className="mt-1">
            Data freshness: {metrics.liveDataCount} live • {awsOffers.length - metrics.liveDataCount} cached
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;