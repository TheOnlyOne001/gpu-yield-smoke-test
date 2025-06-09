import React, { useState, useEffect, FormEvent } from 'react';
import Head from 'next/head';
import useSWR from 'swr';
import { 
  Zap, 
  Calculator, 
  Mail, 
  X, 
  TrendingUp, 
  DollarSign, 
  Clock, 
  ChevronRight,
  Sparkles,
  BarChart3,
  Shield,
  Globe,
  ArrowRight,
  Check,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// API configuration
const API_BASE_URL = (() => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (apiUrl.startsWith('http')) {
    return apiUrl;
  }
  return `https://${apiUrl}`;
})();

// Type definitions
interface GPUPriceDelta {
  gpu_model: string;
  best_source: string;
  price_usd_hr: number;
}

interface DeltaResponse {
  deltas: GPUPriceDelta[];
}

interface ROIResponse {
  potential_monthly_profit: number;
}

const HomePage: React.FC = () => {
  // Fetcher function for SWR
  const fetcher = async (url: string): Promise<DeltaResponse> => {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
  };

  // SWR hook for fetching delta data
  const { data, error, isLoading } = useSWR<DeltaResponse>(
    `${API_BASE_URL}/delta`,
    fetcher,
    { 
      refreshInterval: 30000,
      errorRetryCount: 3,
      errorRetryInterval: 5000
    }
  );

  // State management
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [gpuModel, setGpuModel] = useState('');
  const [hoursPerDay, setHoursPerDay] = useState('');
  const [powerCost, setPowerCost] = useState('');
  const [roiResult, setRoiResult] = useState<number | null>(null);
  const [roiLoading, setRoiLoading] = useState(false);
  const [signupStatus, setSignupStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [signupMessage, setSignupMessage] = useState('');

  // Find the best deal from the data
  const getBestDeal = (): GPUPriceDelta | null => {
    if (!data?.deltas || !Array.isArray(data.deltas) || data.deltas.length === 0) {
      return null;
    }
    
    return data.deltas.reduce((prev, current) => 
      (current.price_usd_hr > prev.price_usd_hr) ? current : prev
    );
  };

  const bestDeal = getBestDeal();

  // Handle signup form submission
  const handleSignupSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    
    setSignupStatus('loading');
    setSignupMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          hcaptcha_response: "development-test-key"
        }),
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setSignupStatus('success');
        setSignupMessage('Successfully signed up! Check your email for confirmation.');
        setEmail('');
      } else {
        throw new Error(result.detail || 'Signup failed');
      }
    } catch (error) {
      setSignupStatus('error');
      setSignupMessage(error instanceof Error ? error.message : 'Failed to sign up. Please try again.');
      console.error('Signup error:', error);
    }
  };

  // Handle ROI calculation
  const handleRoiCalc = async (e: FormEvent) => {
    e.preventDefault();
    setRoiResult(null);
    setRoiLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/roi`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          gpu_model: gpuModel.trim(),
          hours_per_day: parseFloat(hoursPerDay),
          power_cost_kwh: parseFloat(powerCost)
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'ROI calculation failed');
      }
      
      const data: ROIResponse = await response.json();
      setRoiResult(data.potential_monthly_profit);
    } catch (error) {
      console.error('ROI calculation error:', error);
      setRoiResult(null);
    } finally {
      setRoiLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>GPU Yield Calculator - Maximize Your GPU Earnings</title>
        <meta name="description" content="Find the most profitable GPU rental platform in real-time. Calculate your potential earnings and get profit alerts." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        {/* Navigation */}
        <nav className="border-b border-white/10 bg-black/20 backdrop-blur-xl">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">GPU Yield</span>
              </div>
              <div className="hidden md:flex items-center space-x-6">
                <a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a>
                <a href="#pricing" className="text-gray-300 hover:text-white transition-colors">Pricing</a>
                <Button variant="outline" className="border-white/20 text-white hover:bg-white/10">
                  Sign In
                </Button>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative overflow-hidden">
          {/* Background Effects */}
          <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:50px_50px]" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-full blur-3xl" />
          
          <div className="container mx-auto px-4 py-20 relative">
            <div className="max-w-6xl mx-auto">
              <div className="text-center mb-16">
                <Badge className="mb-6 bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20">
                  <Sparkles className="w-3 h-3 mr-1" />
                  Real-time GPU profit tracking
                </Badge>
                
                <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent leading-tight">
                  Turn Your GPU Into a
                  <span className="block bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    Profit Machine
                  </span>
                </h1>
                
                <p className="text-xl md:text-2xl text-gray-300 mb-12 max-w-3xl mx-auto leading-relaxed">
                  Stop guessing which platform pays the most. Get real-time data on GPU rental rates and maximize your earnings with smart automation.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
                  <Button 
                    size="lg" 
                    onClick={() => setIsModalOpen(true)}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold px-8 py-4 rounded-xl shadow-2xl shadow-blue-500/25 transition-all transform hover:scale-105"
                  >
                    <Calculator className="w-5 h-5 mr-2" />
                    Calculate My Profit
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    size="lg"
                    className="border-white/20 text-white hover:bg-white/10 px-8 py-4 rounded-xl"
                  >
                    <BarChart3 className="w-5 h-5 mr-2" />
                    View Live Data
                  </Button>
                </div>
              </div>

              {/* Live Data Display */}
              <Card className="bg-black/40 border-white/10 backdrop-blur-xl shadow-2xl">
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-white flex items-center justify-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    Live Market Data
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {isLoading && (
                    <div className="flex items-center justify-center space-x-3 py-8">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
                      <p className="text-gray-300">Fetching latest rates...</p>
                    </div>
                  )}
                  
                  {error && (
                    <div className="flex items-center justify-center space-x-2 py-8">
                      <AlertCircle className="w-5 h-5 text-red-400" />
                      <p className="text-red-400">Unable to fetch live pricing data</p>
                    </div>
                  )}
                  
                  {bestDeal && !isLoading && (
                    <div className="text-center py-6">
                      <div className="inline-flex items-center space-x-4 bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/20 rounded-2xl px-6 py-4">
                        <TrendingUp className="w-6 h-6 text-green-400" />
                        <div>
                          <p className="text-sm text-gray-400 mb-1">Best Rate Right Now</p>
                          <p className="text-xl font-bold text-white">
                            {bestDeal.gpu_model} on {bestDeal.best_source}
                          </p>
                          <p className="text-2xl font-bold text-green-400">
                            ${bestDeal.price_usd_hr.toFixed(3)}/hour
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-20 bg-black/20">
          <div className="container mx-auto px-4">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Everything You Need to
                <span className="block bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                  Maximize Profits
                </span>
              </h2>
              <p className="text-xl text-gray-300 max-w-3xl mx-auto">
                Our platform combines real-time market data with intelligent automation to help you earn more from your GPU hardware.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
              {/* Feature Cards */}
              <Card className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4">
                    <Zap className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Real-Time Monitoring</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Continuously track GPU rental rates across all major platforms including Vast.ai, RunPod, and Lambda Labs.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-4">
                    <Calculator className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Smart ROI Calculator</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Factor in electricity costs, hardware depreciation, and market rates to get accurate profit projections.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-4">
                    <Mail className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Intelligent Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Get notified instantly when profitable opportunities match your criteria and hardware configuration.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border-orange-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mb-4">
                    <BarChart3 className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Market Analytics</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Deep insights into market trends, seasonal patterns, and demand forecasting for better decision making.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-cyan-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center mb-4">
                    <Shield className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Risk Management</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Advanced algorithms to help you minimize risks and optimize your GPU rental strategy across multiple platforms.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border-yellow-500/20 backdrop-blur-sm hover:scale-105 transition-all duration-300">
                <CardHeader>
                  <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center mb-4">
                    <Globe className="w-6 h-6 text-white" />
                  </div>
                  <CardTitle className="text-white">Global Coverage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-300">
                    Monitor opportunities across different regions and time zones to maximize your earning potential 24/7.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            <div className="grid md:grid-cols-4 gap-8 max-w-6xl mx-auto">
              <div className="text-center">
                <div className="text-4xl font-bold text-white mb-2">$2.4M+</div>
                <div className="text-gray-400">Total earnings tracked</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-white mb-2">15,000+</div>
                <div className="text-gray-400">Active GPUs monitored</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-white mb-2">99.9%</div>
                <div className="text-gray-400">Uptime reliability</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-white mb-2">24/7</div>
                <div className="text-gray-400">Real-time monitoring</div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to Optimize Your GPU Earnings?
            </h2>
            <p className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto">
              Join thousands of users who are already maximizing their GPU profits with our platform.
            </p>

            <Card className="max-w-md mx-auto bg-black/40 border-white/10 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-white text-center">Get Profit Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSignupSubmit} className="space-y-4">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email address"
                    required
                    disabled={signupStatus === 'loading'}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all"
                  />
                  <Button
                    type="submit"
                    disabled={signupStatus === 'loading' || !email.trim()}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50"
                  >
                    {signupStatus === 'loading' ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Signing Up...
                      </>
                    ) : (
                      <>
                        <Mail className="w-4 h-4 mr-2" />
                        Get Started Free
                      </>
                    )}
                  </Button>
                </form>
                {signupMessage && (
                  <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
                    signupStatus === 'success' 
                      ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                      : 'bg-red-500/10 border border-red-500/20 text-red-400'
                  }`}>
                    {signupStatus === 'success' ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <AlertCircle className="w-4 h-4" />
                    )}
                    <span className="text-sm">{signupMessage}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 bg-black/20">
          <div className="container mx-auto px-4 py-12">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <div className="flex items-center space-x-2 mb-4 md:mb-0">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">GPU Yield</span>
              </div>
              <div className="text-gray-400 text-sm">
                © 2024 GPU Yield. All rights reserved.
              </div>
            </div>
          </div>
        </footer>

        {/* ROI Calculator Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div 
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setIsModalOpen(false)}
            />
            
            <Card className="relative bg-gray-900/95 border-white/10 backdrop-blur-xl max-w-md w-full shadow-2xl">
              <CardHeader className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsModalOpen(false)}
                  className="absolute top-0 right-0 text-gray-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </Button>
                <CardTitle className="text-white flex items-center gap-2">
                  <Calculator className="w-5 h-5" />
                  ROI Calculator
                </CardTitle>
              </CardHeader>
              
              <CardContent>
                <form onSubmit={handleRoiCalc} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      GPU Model
                    </label>
                    <input
                      type="text"
                      value={gpuModel}
                      onChange={(e) => setGpuModel(e.target.value)}
                      placeholder="e.g., RTX 4090, RTX 3080"
                      required
                      disabled={roiLoading}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Hours per Day
                    </label>
                    <input
                      type="number"
                      value={hoursPerDay}
                      onChange={(e) => setHoursPerDay(e.target.value)}
                      placeholder="24"
                      min="0"
                      max="24"
                      step="0.5"
                      required
                      disabled={roiLoading}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Power Cost ($/kWh)
                    </label>
                    <input
                      type="number"
                      value={powerCost}
                      onChange={(e) => setPowerCost(e.target.value)}
                      placeholder="0.12"
                      min="0"
                      step="0.01"
                      required
                      disabled={roiLoading}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all"
                    />
                  </div>
                  
                  <Button
                    type="submit"
                    disabled={!gpuModel.trim() || !hoursPerDay || !powerCost || roiLoading}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50"
                  >
                    {roiLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Calculating...
                      </>
                    ) : (
                      <>
                        <Calculator className="w-4 h-4 mr-2" />
                        Calculate Profit
                      </>
                    )}
                  </Button>
                </form>
                
                {roiResult !== null && (
                  <div className={`mt-6 p-6 rounded-xl border ${
                    roiResult > 0 
                      ? 'bg-green-500/10 border-green-500/20' 
                      : 'bg-red-500/10 border-red-500/20'
                  }`}>
                    <div className="text-center">
                      <DollarSign className={`w-8 h-8 mx-auto mb-2 ${
                        roiResult > 0 ? 'text-green-400' : 'text-red-400'
                      }`} />
                      <h3 className={`text-2xl font-bold mb-2 ${
                        roiResult > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        ${Math.abs(roiResult).toFixed(2)}/month
                      </h3>
                      <p className="text-sm text-gray-400">
                        {roiResult > 0 
                          ? 'Potential monthly profit' 
                          : 'Projected monthly loss'
                        }
                      </p>
                      {roiResult <= 0 && (
                        <p className="text-xs text-gray-500 mt-2">
                          Consider reducing power costs or increasing rental hours
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </>
  );
};

export default HomePage;