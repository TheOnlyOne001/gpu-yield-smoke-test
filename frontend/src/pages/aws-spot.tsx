import React, { useState, useMemo, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import {
  Cloud,
  Filter,
  Download,
  RefreshCw,
  TrendingUp,
  Shield,
  DollarSign,
  Globe,
  Cpu,
  AlertCircle,
  ChevronLeft,
  Search,
  ExternalLink,
  Copy,
  Check,
  Info,
  BarChart3,
  Zap,
  Clock,
  Server
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Layout from '@/components/layout/layout';

// Hooks and utilities
import { useAWSSpotData, useAWSRegions, useAWSModels } from '@/hooks/useAWSSpotData';
import { 
  calculateOfferYieldMetrics,
  AWS_REGION_DISPLAY,
  REGION_POWER_COSTS,
  AWS_INSTANCE_METADATA
} from '@/lib/awsUtils';
import { formatTimeAgo } from '@/lib/fetcher';
import SyncStatusBadge from '@/components/SyncStatusBadge';

// Types
import { EnrichedAWSSpotOffer } from '@/types/aws-spot';

// Chart components
import dynamic from 'next/dynamic';
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const AreaChart = dynamic(() => import('recharts').then(mod => mod.AreaChart), { ssr: false });
const Area = dynamic(() => import('recharts').then(mod => mod.Area), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });

const AWSSpotPage: React.FC = () => {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [minAvailability, setMinAvailability] = useState(1);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'price' | 'yield' | 'risk'>('yield');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Fetch data
  const { 
    offers, 
    loading, 
    error,
    lastUpdated,
    metadata,
    refetch,
    hasLiveData,
    averagePrice,
    uniqueModels,
    uniqueRegions
  } = useAWSSpotData({
    region: selectedRegion,
    model: selectedModel,
    minAvailability,
    viewType: 'operator',
    autoRefresh: true,
    refreshInterval: 30000
  });

  const { regions } = useAWSRegions();
  const { models } = useAWSModels();

  // Filter and sort offers
  const processedOffers = useMemo(() => {
    let filtered = offers;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(offer => 
        offer.model.toLowerCase().includes(query) ||
        offer.region.toLowerCase().includes(query) ||
        offer.instance_type.toLowerCase().includes(query) ||
        (AWS_REGION_DISPLAY[offer.region] || '').toLowerCase().includes(query)
      );
    }

    // Price filter
    if (maxPrice !== undefined) {
      filtered = filtered.filter(offer => offer.usd_hr <= maxPrice);
    }

    // Sort
    filtered.sort((a, b) => {
      let compareValue = 0;
      
      switch (sortBy) {
        case 'price':
          compareValue = a.usd_hr - b.usd_hr;
          break;
        case 'yield':
          const aYield = calculateOfferYieldMetrics(a).netYield;
          const bYield = calculateOfferYieldMetrics(b).netYield;
          compareValue = aYield - bYield;
          break;
        case 'risk':
          const riskOrder = { low: 0, medium: 1, high: 2 };
          compareValue = riskOrder[a.interruption_risk] - riskOrder[b.interruption_risk];
          break;
      }
      
      return sortOrder === 'asc' ? compareValue : -compareValue;
    });

    return filtered;
  }, [offers, searchQuery, maxPrice, sortBy, sortOrder]);

  // Calculate statistics
  const statistics = useMemo(() => {
    const modelStats: Record<string, { count: number; avgPrice: number; minPrice: number; maxPrice: number }> = {};
    const regionStats: Record<string, { count: number; avgPrice: number }> = {};
    
    processedOffers.forEach(offer => {
      // Model stats
      if (!modelStats[offer.model]) {
        modelStats[offer.model] = { count: 0, avgPrice: 0, minPrice: Infinity, maxPrice: 0 };
      }
      modelStats[offer.model].count++;
      modelStats[offer.model].avgPrice += offer.usd_hr;
      modelStats[offer.model].minPrice = Math.min(modelStats[offer.model].minPrice, offer.usd_hr);
      modelStats[offer.model].maxPrice = Math.max(modelStats[offer.model].maxPrice, offer.usd_hr);
      
      // Region stats
      if (!regionStats[offer.region]) {
        regionStats[offer.region] = { count: 0, avgPrice: 0 };
      }
      regionStats[offer.region].count++;
      regionStats[offer.region].avgPrice += offer.usd_hr;
    });
    
    // Calculate averages
    Object.keys(modelStats).forEach(model => {
      modelStats[model].avgPrice /= modelStats[model].count;
    });
    Object.keys(regionStats).forEach(region => {
      regionStats[region].avgPrice /= regionStats[region].count;
    });
    
    return { modelStats, regionStats };
  }, [processedOffers]);

  // Export functionality
  const exportData = useCallback(() => {
    const headers = [
      'Model', 'Region', 'Region Name', 'Price/hr', 'Instance Type', 
      'vCPUs', 'RAM (GB)', 'GPUs', 'GPU Memory (GB)', 'Network', 
      'Storage (GB)', 'Interruption Risk', 'Net Yield/hr', 'Margin %', 
      'Power Cost/hr', 'Break Even', 'Timestamp'
    ];
    
    const rows = processedOffers.map(offer => {
      const yieldMetrics = calculateOfferYieldMetrics(offer);
      const metadata = AWS_INSTANCE_METADATA[offer.instance_type] || {};
      
      return [
        offer.model,
        offer.region,
        AWS_REGION_DISPLAY[offer.region] || offer.region,
        offer.usd_hr.toFixed(4),
        offer.instance_type,
        metadata.vcpu || '',
        metadata.ram_gb || '',
        offer.availability,
        offer.gpu_memory_gb || '',
        metadata.network || '',
        metadata.storage_gb || '',
        offer.interruption_risk,
        yieldMetrics.netYield.toFixed(4),
        yieldMetrics.margin.toFixed(2),
        yieldMetrics.powerCostPerHour.toFixed(4),
        yieldMetrics.breakEven ? 'Yes' : 'No',
        offer.timestamp || new Date().toISOString()
      ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aws-spot-gpu-prices-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }, [processedOffers]);

  // Copy to clipboard
  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Render offer card for grid view
  const renderOfferCard = (offer: EnrichedAWSSpotOffer, index: number) => {
    const yieldMetrics = calculateOfferYieldMetrics(offer);
    const metadata = AWS_INSTANCE_METADATA[offer.instance_type] || {};
    const offerId = `${offer.model}-${offer.region}-${offer.instance_type}-${index}`;
    
    return (
      <Card key={offerId} className="bg-black/40 border-white/10 backdrop-blur-xl hover:border-white/20 transition-all">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-blue-400" />
                {offer.model}
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                {AWS_REGION_DISPLAY[offer.region] || offer.region}
              </p>
            </div>
            <Badge className={`${offer.freshness === 'live' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
              {offer.freshness}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Pricing */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400">GPU Price</p>
              <p className="text-xl font-bold text-green-400">${offer.usd_hr.toFixed(3)}/hr</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Net Yield</p>
              <p className={`text-xl font-bold ${yieldMetrics.netYield > 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${yieldMetrics.netYield.toFixed(3)}/hr
              </p>
            </div>
          </div>
          
          {/* Instance details */}
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between text-gray-300">
              <span className="flex items-center gap-1">
                <Server className="w-3 h-3 text-gray-500" />
                Instance
              </span>
              <span className="text-blue-400">{offer.instance_type}</span>
            </div>
            <div className="flex items-center justify-between text-gray-300">
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-gray-500" />
                Availability
              </span>
              <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-xs">
                {offer.availability} GPUs
              </Badge>
            </div>
            <div className="flex items-center justify-between text-gray-300">
              <span className="flex items-center gap-1">
                <Shield className="w-3 h-3 text-gray-500" />
                Risk Level
              </span>
              <Badge className={`text-xs ${
                offer.interruption_risk === 'low' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                offer.interruption_risk === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                'bg-red-500/10 text-red-400 border-red-500/20'
              }`}>
                {offer.interruption_risk} risk
              </Badge>
            </div>
          </div>
          
          {/* Specs */}
          {metadata.vcpu && (
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10 text-xs text-gray-400">
              <span>{metadata.vcpu} vCPUs</span>
              <span>{metadata.ram_gb} GB RAM</span>
              <span>{offer.gpu_memory_gb || 16} GB VRAM</span>
              <span>{metadata.network}</span>
            </div>
          )}
          
          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => window.open(
                `https://console.aws.amazon.com/ec2/v2/home?region=${offer.region}#LaunchInstances:`,
                '_blank'
              )}
            >
              <ExternalLink className="w-4 h-4 mr-1" />
              Launch
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="border-gray-600 text-gray-300 hover:bg-gray-700"
              onClick={() => copyToClipboard(
                `${offer.model} - ${offer.instance_type} - ${offer.region} - $${offer.usd_hr}/hr`,
                offerId
              )}
            >
              {copiedId === offerId ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <Layout>
      <Head>
        <title>AWS Spot GPU Pricing - GPU Yield</title>
        <meta name="description" content="Real-time AWS Spot GPU instance pricing and availability" />
      </Head>

      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-8">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="text-gray-400 hover:text-white"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Cloud className="w-8 h-8 text-orange-400" />
                AWS Spot GPU Pricing
                <Badge className={`${hasLiveData ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
                  {hasLiveData ? 'Live Data' : 'Demo Data'}
                </Badge>
              </h1>
              <p className="text-gray-400 mt-1">
                {processedOffers.length} offers • Updated {lastUpdated ? formatTimeAgo(new Date(lastUpdated).getTime()) : 'recently'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <SyncStatusBadge 
              timestamp={lastUpdated ? new Date(lastUpdated).getTime() : undefined}
              isLoading={loading}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={refetch}
              disabled={loading}
              className="text-gray-300 border-gray-600 hover:bg-gray-700"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              size="sm"
              onClick={exportData}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>

        {/* Statistics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Total Offers</CardTitle>
              <Cloud className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{processedOffers.length}</div>
              <p className="text-xs text-gray-400">
                {uniqueModels.length} models, {uniqueRegions.length} regions
              </p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Average Price</CardTitle>
              <DollarSign className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">${averagePrice.toFixed(3)}</div>
              <p className="text-xs text-gray-400">per GPU hour</p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Low Risk</CardTitle>
              <Shield className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {processedOffers.filter(o => o.interruption_risk === 'low').length}
              </div>
              <p className="text-xs text-gray-400">
                {((processedOffers.filter(o => o.interruption_risk === 'low').length / processedOffers.length) * 100).toFixed(1)}% of offers
              </p>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-300">Profitable</CardTitle>
              <TrendingUp className="h-4 w-4 text-purple-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {processedOffers.filter(o => calculateOfferYieldMetrics(o).netYield > 0).length}
              </div>
              <p className="text-xs text-gray-400">
                positive net yield
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl mb-8">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              {/* Search */}
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

              {/* Region Filter */}
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

              {/* Model Filter */}
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

              {/* Max Price Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Max Price</label>
                <input
                  type="number"
                  value={maxPrice || ''}
                  onChange={(e) => setMaxPrice(e.target.value ? parseFloat(e.target.value) : undefined)}
                  placeholder="No limit"
                  step="0.01"
                  className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'price' | 'yield' | 'risk')}
                  className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="yield">Net Yield</option>
                  <option value="price">Price</option>
                  <option value="risk">Risk Level</option>
                </select>
              </div>

              {/* Sort Order & View Mode */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-300">View</label>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={sortOrder === 'desc' ? 'default' : 'outline'}
                    onClick={() => setSortOrder('desc')}
                    className="flex-1"
                  >
                    ↓
                  </Button>
                  <Button
                    size="sm"
                    variant={sortOrder === 'asc' ? 'default' : 'outline'}
                    onClick={() => setSortOrder('asc')}
                    className="flex-1"
                  >
                    ↑
                  </Button>
                </div>
              </div>
            </div>

            {/* View Mode Toggle */}
            <div className="flex justify-between items-center mt-4 pt-4 border-t border-white/10">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={viewMode === 'table' ? 'default' : 'outline'}
                  onClick={() => setViewMode('table')}
                  className="text-gray-300 border-gray-600"
                >
                  Table
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  onClick={() => setViewMode('grid')}
                  className="text-gray-300 border-gray-600"
                >
                  Cards
                </Button>
              </div>
              <div className="text-sm text-gray-400">
                Showing {processedOffers.length} offers
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Content */}
        {error ? (
          <Card className="bg-red-500/10 border-red-500/20 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 text-red-400">
                <AlertCircle className="w-5 h-5" />
                <span>Error loading AWS Spot data: {error}</span>
              </div>
            </CardContent>
          </Card>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {processedOffers.map((offer, index) => renderOfferCard(offer, index))}
          </div>
        ) : (
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left text-gray-400 p-4">GPU Model</th>
                      <th className="text-left text-gray-400 p-4">Region</th>
                      <th className="text-left text-gray-400 p-4">Price/hr</th>
                      <th className="text-left text-gray-400 p-4">Net Yield</th>
                      <th className="text-left text-gray-400 p-4">Instance</th>
                      <th className="text-center text-gray-400 p-4">GPUs</th>
                      <th className="text-left text-gray-400 p-4">Risk</th>
                      <th className="text-left text-gray-400 p-4">Status</th>
                      <th className="text-left text-gray-400 p-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processedOffers.map((offer, index) => {
                      const yieldMetrics = calculateOfferYieldMetrics(offer);
                      const offerId = `${offer.model}-${offer.region}-${offer.instance_type}-${index}`;
                      
                      return (
                        <tr 
                          key={offerId}
                          className="border-b border-white/5 hover:bg-white/5 transition-colors group"
                        >
                          <td className="p-4">
                            <div className="flex items-center gap-3">
                              <Cpu className="w-4 h-4 text-gray-500" />
                              <div>
                                <div className="text-white font-medium">{offer.model}</div>
                                {offer.gpu_memory_gb && (
                                  <div className="text-xs text-gray-500">{offer.gpu_memory_gb}GB VRAM</div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="p-4">
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
                          <td className="p-4">
                            <div className="text-green-400 font-mono font-medium">
                              ${offer.usd_hr.toFixed(4)}
                            </div>
                            {offer.total_instance_price && (
                              <div className="text-xs text-gray-500">
                                ${offer.total_instance_price.toFixed(2)} total
                              </div>
                            )}
                          </td>
                          <td className="p-4">
                            <div className={`font-mono ${yieldMetrics.netYield > 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ${yieldMetrics.netYield.toFixed(3)}/hr
                            </div>
                            <div className="text-xs text-gray-500">
                              {yieldMetrics.margin.toFixed(1)}% margin
                            </div>
                          </td>
                          <td className="p-4">
                            <span className="text-blue-400">{offer.instance_type}</span>
                          </td>
                          <td className="p-4 text-center">
                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                              {offer.availability}
                            </Badge>
                          </td>
                          <td className="p-4">
                            <Badge className={`text-xs ${
                              offer.interruption_risk === 'low' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                              offer.interruption_risk === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                              'bg-red-500/10 text-red-400 border-red-500/20'
                            }`}>
                              {offer.interruption_risk}
                            </Badge>
                          </td>
                          <td className="p-4">
                            <Badge className={`${offer.freshness === 'live' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}`}>
                              {offer.freshness}
                            </Badge>
                          </td>
                          <td className="p-4">
                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 p-1"
                                onClick={() => window.open(
                                  `https://console.aws.amazon.com/ec2/v2/home?region=${offer.region}#LaunchInstances:`,
                                  '_blank'
                                )}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-gray-400 hover:text-gray-300 hover:bg-gray-500/10 p-1"
                                onClick={() => copyToClipboard(
                                  `${offer.model} - ${offer.instance_type} - ${offer.region} - $${offer.usd_hr}/hr`,
                                  offerId
                                )}
                              >
                                {copiedId === offerId ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                              </Button>
                            </div>
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

        {processedOffers.length === 0 && !loading && (
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardContent className="p-12 text-center">
              <Info className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No offers found</h3>
              <p className="text-gray-400 mb-6">
                Try adjusting your filters or refresh the data to see available offers.
              </p>
              <Button
                onClick={() => {
                  setSelectedRegion('');
                  setSelectedModel('');
                  setMaxPrice(undefined);
                  setSearchQuery('');
                }}
                variant="outline"
                className="text-gray-300 border-gray-600 hover:bg-gray-700"
              >
                Clear Filters
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default AWSSpotPage;