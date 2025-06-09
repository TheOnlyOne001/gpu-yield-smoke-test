import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  Clock,
  Server,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  Download,
  Settings,
  Bell,
  Filter,
  Calendar,
  Eye,
  BarChart3,
  X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

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

const Dashboard: React.FC<DashboardProps> = ({ userId }) => {
  const [gpuData, setGpuData] = useState<GPUData[]>([]);
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState('24h');
  const [selectedGPU, setSelectedGPU] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Mock data generation
  useEffect(() => {
    const generateMockData = () => {
      const gpuModels = ['RTX 4090', 'RTX 4080', 'RTX 3090', 'RTX 3080', 'A100', 'H100'];
      const platforms = ['Vast.ai', 'RunPod', 'Lambda Labs', 'Genesis Cloud'];
      
      const mockGPUs: GPUData[] = gpuModels.map((model, index) => ({
        model,
        platform: platforms[index % platforms.length],
        price: Math.random() * 2 + 0.5,
        utilization: Math.random() * 100,
        status: ['active', 'idle', 'error'][Math.floor(Math.random() * 3)] as any,
        earnings: Math.random() * 500 + 100,
        powerDraw: Math.random() * 400 + 200,
        temperature: Math.random() * 30 + 50,
        lastUpdate: new Date().toISOString()
      }));

      const mockMarket: MarketData[] = Array.from({ length: 24 }, (_, i) => ({
        timestamp: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
        price: Math.random() * 0.5 + 1.0,
        volume: Math.random() * 1000 + 500,
        platform: platforms[Math.floor(Math.random() * platforms.length)]
      }));

      setGpuData(mockGPUs);
      setMarketData(mockMarket);
      setIsLoading(false);
    };

    generateMockData();
    
    if (autoRefresh) {
      const interval = setInterval(generateMockData, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // Computed values
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
      fill: `hsl(${Math.random() * 360}, 70%, 50%)`
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
      {/* Remove the background and padding since Layout handles it */}
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

        {/* Key Metrics */}
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
                  <p className="text-gray-400 text-sm font-medium">Avg Utilization</p>
                  <p className="text-3xl font-bold text-white">{averageUtilization.toFixed(1)}%</p>
                  <div className="flex items-center mt-2">
                    <BarChart3 className="w-4 h-4 text-purple-400 mr-1" />
                    <span className="text-purple-400 text-sm">+3.2%</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
                  <Activity className="w-6 h-6 text-white" />
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

        {/* Charts Row */}
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
                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Earnings']}
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
                    <th className="text-left text-gray-400 font-medium py-3 px-4">Temp</th>
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
                          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <Server className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <p className="text-white font-medium">{gpu.model}</p>
                            <p className="text-gray-400 text-sm">ID: GPU-{index + 1}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
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
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${
                            gpu.temperature > 80 ? 'bg-red-500' : 
                            gpu.temperature > 70 ? 'bg-yellow-500' : 'bg-green-500'
                          }`} />
                          <span className="text-white font-mono">
                            {gpu.temperature.toFixed(0)}°C
                          </span>
                        </div>
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

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { time: '2 minutes ago', action: 'GPU RTX 4090 started earning', type: 'success' },
                  { time: '15 minutes ago', action: 'Price alert triggered for RTX 3080', type: 'warning' },
                  { time: '1 hour ago', action: 'Maintenance completed on H100', type: 'info' },
                  { time: '2 hours ago', action: 'New high profit opportunity detected', type: 'success' },
                  { time: '3 hours ago', action: 'Power consumption optimized', type: 'info' },
                ].map((activity, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-white/5">
                    <div className={`w-2 h-2 rounded-full ${
                      activity.type === 'success' ? 'bg-green-500' :
                      activity.type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                    }`} />
                    <div className="flex-1">
                      <p className="text-white text-sm">{activity.action}</p>
                      <p className="text-gray-400 text-xs">{activity.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Active Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { 
                    title: 'High Temperature Warning', 
                    message: 'RTX 3090 temperature above 85°C',
                    type: 'error',
                    time: '5 min ago'
                  },
                  { 
                    title: 'Profit Opportunity', 
                    message: 'New high-paying job available on Vast.ai',
                    type: 'success',
                    time: '12 min ago'
                  },
                  { 
                    title: 'Low Utilization', 
                    message: 'RTX 4080 utilization below 30%',
                    type: 'warning',
                    time: '25 min ago'
                  },
                  { 
                    title: 'Market Update', 
                    message: 'GPU rental prices increased by 15%',
                    type: 'info',
                    time: '1 hour ago'
                  },
                ].map((alert, index) => (
                  <div key={index} className={`p-4 rounded-lg border ${
                    alert.type === 'error' ? 'bg-red-500/10 border-red-500/20' :
                    alert.type === 'success' ? 'bg-green-500/10 border-green-500/20' :
                    alert.type === 'warning' ? 'bg-yellow-500/10 border-yellow-500/20' :
                    'bg-blue-500/10 border-blue-500/20'
                  }`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className={`font-medium ${
                          alert.type === 'error' ? 'text-red-400' :
                          alert.type === 'success' ? 'text-green-400' :
                          alert.type === 'warning' ? 'text-yellow-400' :
                          'text-blue-400'
                        }`}>
                          {alert.title}
                        </h4>
                        <p className="text-gray-300 text-sm mt-1">{alert.message}</p>
                        <p className="text-gray-500 text-xs mt-2">{alert.time}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-gray-400 hover:text-white hover:bg-white/10"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Performance Metrics */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Performance Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={gpuData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="model" 
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
                <Bar 
                  dataKey="utilization" 
                  fill="url(#colorGradient)" 
                  radius={[4, 4, 0, 0]}
                />
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.9}/>
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0.9}/>
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;