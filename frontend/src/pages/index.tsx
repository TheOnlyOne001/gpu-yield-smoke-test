import React, { useState, useEffect, FormEvent } from 'react';
import Head from 'next/head';
import Link from 'next/link';
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
  Check,
  AlertCircle,
  Cpu,
  Activity,
  Menu,
  LogIn,
  UserPlus,
  Star,
  ArrowUpRight,
  User
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import EmailCTA from '../components/EmailCTA';
import ScrollCue from '../components/ScrollCue';
import MiniROIPreview from '../components/MiniROIPreview';
import LogoBar from '../components/LogoBar';
import GpuCounter, { GpuCounterInline } from '../components/GpuCounter';
import { fetcherWithTimestamp, FetchResult } from '../lib/fetcher';
import SyncStatusBadge from '../components/SyncStatusBadge';
import AuthDropdown from '../components/AuthDropdown';

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

function formatYieldDelta(delta: number | undefined) {
  if (delta === undefined) return '—';
  return delta >= 0 ? `+$${delta.toFixed(2)}/hr` : `-$${Math.abs(delta).toFixed(2)}/hr`;
}

const HomePage: React.FC = () => {
  // Enhanced SWR with timestamp tracking
  const { data: fetchResult, error, isLoading } = useSWR<FetchResult<DeltaResponse>>(
    `${API_BASE_URL}/delta`,
    fetcherWithTimestamp,
    {
      refreshInterval: 30000,
      errorRetryCount: 3,
      errorRetryInterval: 5000
    }
  );

  // Extract data and timestamp from enhanced fetcher
  const data = fetchResult?.data;
  const timestamp = fetchResult?.timestamp;

  // Fix: Add proper null checks for data.deltas
  const targetGpu = data?.deltas && Array.isArray(data.deltas) 
    ? data.deltas.find((d) => d.gpu_model === 'RTX 4090') ?? data.deltas[0]
    : undefined;
  const delta = targetGpu?.price_usd_hr;

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

  // Find the best deal from the data - also fix this function
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
        <title>GPU Yield Calculator - Live RTX 4090 Yield</title>
        <meta name="description" content="Find the most profitable GPU rental platform in real-time. Calculate your potential earnings and get profit alerts." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">        {/* Design System Navigation */}
        <nav 
          className="fixed top-0 left-0 right-0 z-50 border-b"
          style={{
            background: 'var(--surface-1)',
            backdropFilter: 'blur(24px)',
            borderColor: 'var(--stroke)'
          }}
        >
          {/* Ambient background glow */}
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-cyan-500/5 to-purple-500/5" />
          
          <div className="relative container mx-auto px-4">
            <div className="flex items-center justify-between h-20">
              
              {/* Logo - Enhanced with Design System */}
              <Link href="/" className="group flex items-center space-x-3 focus-ring keyboard-focus rounded-xl p-2 -m-2">
                <div className="relative">
                  <div 
                    className="w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg group-hover:shadow-purple-500/25 transition-all duration-200"
                    style={{ background: 'var(--accent-gradient)' }}
                  >
                    <Zap className="w-6 h-6 text-white" />
                  </div>
                  {/* Hover glow effect */}
                  <div 
                    className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-20 blur-lg transition-all duration-200"
                    style={{ background: 'var(--accent-gradient)' }}
                  />
                </div>
                <div className="flex flex-col">
                  <span className="text-lg font-semibold text-white group-hover:text-purple-100 transition-colors">
                    GPU Yield
                  </span>
                  <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Mining Platform
                  </span>
                </div>
              </Link>
              
              {/* Desktop Navigation */}
              <div className="hidden lg:flex items-center space-x-3">
                
                {/* Navigation Links - Design System Pills */}
                <div 
                  className="flex items-center space-x-1 p-1 rounded-2xl border"
                  style={{ 
                    background: 'rgba(255, 255, 255, 0.04)',
                    borderColor: 'var(--stroke)'
                  }}
                >                  <a 
                    href="#features" 
                    className="px-4 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 ease-out focus-ring keyboard-focus hover:bg-white/8"
                    style={{ color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { (e.target as HTMLElement).style.color = 'var(--text-primary)' }}
                    onMouseLeave={(e) => { (e.target as HTMLElement).style.color = 'var(--text-secondary)' }}
                  >
                    Features
                  </a>
                  <a 
                    href="#pricing" 
                    className="px-4 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 ease-out focus-ring keyboard-focus hover:bg-white/8"
                    style={{ color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { (e.target as HTMLElement).style.color = 'var(--text-primary)' }}
                    onMouseLeave={(e) => { (e.target as HTMLElement).style.color = 'var(--text-secondary)' }}
                  >
                    Pricing
                  </a>
                  <a 
                    href="#docs" 
                    className="px-4 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 ease-out focus-ring keyboard-focus hover:bg-white/8"
                    style={{ color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { (e.target as HTMLElement).style.color = 'var(--text-primary)' }}
                    onMouseLeave={(e) => { (e.target as HTMLElement).style.color = 'var(--text-secondary)' }}
                  >
                    Docs
                  </a>
                </div>
                
                {/* GPU Counter - Design System Enhanced */}
                <div className="mx-3">
                  <div 
                    className="px-4 py-2.5 rounded-xl border"
                    style={{
                      background: 'rgba(34, 197, 94, 0.1)',
                      borderColor: 'rgba(34, 197, 94, 0.2)'
                    }}
                  >
                    <GpuCounterInline className="text-emerald-300 text-sm font-medium" />
                  </div>
                </div>
                
                {/* Auth Dropdown */}
                <AuthDropdown />
                
                {/* Sync Status - Design System */}
                <div 
                  className="px-3 py-2.5 rounded-xl border text-xs font-medium"
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    borderColor: 'var(--stroke)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <SyncStatusBadge 
                    timestamp={timestamp} 
                    isLoading={isLoading}
                  />
                </div>
              </div>

              {/* Mobile Menu Button - Design System */}
              <div className="lg:hidden">
                <button 
                  className="w-10 h-10 rounded-xl border transition-all duration-200 ease-out focus-ring keyboard-focus hover:bg-white/8 active:scale-97"
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    borderColor: 'var(--stroke)',
                    color: 'var(--text-primary)'
                  }}
                >
                  <Menu className="w-5 h-5 mx-auto" />
                </button>
              </div>
            </div>

            {/* Mobile Navigation - Design System Compliant */}
            <div className="lg:hidden border-t" style={{ borderColor: 'var(--stroke)' }}>
              <div className="py-6 space-y-4">
                
                {/* Mobile Navigation Links */}
                <div className="space-y-2">
                  <a 
                    href="#features" 
                    className="block px-4 py-3 rounded-xl font-medium transition-all duration-200 focus-ring keyboard-focus hover:bg-white/5"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Features
                  </a>
                  <a 
                    href="#pricing" 
                    className="block px-4 py-3 rounded-xl font-medium transition-all duration-200 focus-ring keyboard-focus hover:bg-white/5"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Pricing
                  </a>
                  <a 
                    href="#docs" 
                    className="block px-4 py-3 rounded-xl font-medium transition-all duration-200 focus-ring keyboard-focus hover:bg-white/5"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Documentation
                  </a>
                </div>

                {/* Mobile GPU Counter */}
                <div className="px-4">
                  <div 
                    className="p-3 rounded-xl border"
                    style={{
                      background: 'rgba(34, 197, 94, 0.1)',
                      borderColor: 'rgba(34, 197, 94, 0.2)'
                    }}
                  >
                    <GpuCounterInline />
                  </div>
                </div>
                
                {/* Mobile Auth Buttons - Design System */}
                <div className="px-4 pt-4 border-t" style={{ borderColor: 'var(--stroke)' }}>
                  <div className="grid grid-cols-2 gap-3">
                    <Link href="/login">
                      <button className="btn-secondary w-full h-12 rounded-xl font-medium focus-ring keyboard-focus flex items-center justify-center gap-2">
                        <LogIn className="w-4 h-4" />
                        <span>Sign In</span>
                      </button>
                    </Link>
                    <Link href="/signup">
                      <button 
                        className="btn-primary w-full h-12 rounded-xl font-medium focus-ring keyboard-focus flex items-center justify-center gap-2"
                        style={{ background: 'var(--accent-gradient)' }}
                      >
                        <UserPlus className="w-4 h-4" />
                        <span>Sign Up</span>
                      </button>
                    </Link>
                  </div>
                  
                  {/* Mobile sync status */}
                  <div className="mt-4 flex justify-center">
                    <div 
                      className="px-3 py-2 rounded-xl border text-xs"
                      style={{
                        background: 'rgba(255, 255, 255, 0.04)',
                        borderColor: 'var(--stroke)',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      <SyncStatusBadge 
                        timestamp={timestamp} 
                        isLoading={isLoading}
                      />
                    </div>
                  </div>
                </div>              </div>
            </div>
          </div>
        </nav>

        {/* Enhanced Hero Section */}
        <section className="relative overflow-hidden pt-20">
          {/* Modern Background Effects */}
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900/50 to-slate-900" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[1000px] bg-gradient-to-r from-blue-600/20 via-purple-600/20 to-cyan-600/20 rounded-full blur-3xl" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(120,119,198,0.1),transparent)] opacity-70" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(168,85,247,0.1),transparent)] opacity-70" />
          </div>
          
          <div className="relative container mx-auto px-4 py-20">
            <div className="max-w-6xl mx-auto">
              <div className="text-center mb-16">
                {/* Modern Badge */}
                <div className="inline-flex items-center gap-2 px-4 py-2 mb-8 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-500/10 border border-blue-500/20 rounded-full backdrop-blur-sm">
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full animate-pulse" />
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-blue-100">Real-time GPU profit tracking</span>
                  <div className="px-2 py-0.5 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-md">
                    <span className="text-xs font-bold text-emerald-400">Live</span>
                  </div>
                </div>
                
                {/* Modern Heading with Gradient Text */}
                <h1 className="text-5xl md:text-7xl font-bold mb-8 leading-tight">
                  <span className="bg-gradient-to-r from-white via-blue-100 to-white bg-clip-text text-transparent">
                    Turn Your GPU Into a
                  </span>
                  <br />
                  <span className="bg-gradient-to-r from-blue-400 via-purple-500 to-cyan-400 bg-clip-text text-transparent">
                    Profit Machine
                  </span>
                </h1>

                {/* Enhanced Yield Delta Display */}
                <div className="mb-8">
                  <div className={`
                    inline-flex items-center gap-3 px-6 py-3 rounded-2xl backdrop-blur-2xl border
                    ${delta !== undefined && delta < 0 
                      ? 'bg-red-500/10 border-red-500/20 text-red-400' 
                      : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    }
                  `}>
                    <div className="w-3 h-3 rounded-full bg-current animate-pulse" />
                    <Cpu className="w-5 h-5" />
                    <span className="font-bold text-lg">RTX 4090 yield delta {formatYieldDelta(delta)}</span>
                    <div className="px-2 py-1 bg-current/20 rounded-lg">
                      <span className="text-xs font-bold">Live</span>
                    </div>
                  </div>
                </div>
                
                {/* Enhanced Description */}
                <p className="text-xl md:text-2xl text-gray-300 mb-12 max-w-4xl mx-auto leading-relaxed">
                  Stop guessing which platform pays the most. Get <span className="text-blue-400 font-semibold">real-time data</span> on GPU rental rates and maximize your earnings with <span className="text-purple-400 font-semibold">smart automation</span>.
                </p>

                {/* Modern CTA Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
                  <Link href="/signup">
                    <Button className="group relative px-8 py-4 bg-gradient-to-r from-blue-600 via-purple-600 to-cyan-600 hover:from-blue-700 hover:via-purple-700 hover:to-cyan-700 text-white font-semibold rounded-2xl shadow-2xl hover:shadow-blue-500/25 transition-all duration-300 overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                      <span className="relative flex items-center gap-2">
                        <Sparkles className="w-5 h-5" />
                        Start Earning Free
                        <ArrowUpRight className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-300" />
                      </span>
                    </Button>
                  </Link>
                  
                  <Link href="/login">
                    <Button variant="outline" className="px-8 py-4 border-white/20 bg-white/5 backdrop-blur-sm text-white hover:bg-white/10 hover:border-white/30 font-semibold rounded-2xl transition-all duration-300">
                      <User className="w-5 h-5 mr-2" />
                      Sign In
                    </Button>
                  </Link>                </div>
              </div>
            </div>
          </div>
        </section>

        {/* GPU Counter and Data Section */}
        <section className="relative py-20">
          <div className="container mx-auto px-4">
            <div className="max-w-6xl mx-auto">
              <div className="text-center mb-16">
                {/* Add GpuCounter component here */}
                <GpuCounter 
                  showDetails={true} 
                  animate={true}
                  className="justify-center"
                />

                <div className="mt-8 w-full flex justify-center">
                  <EmailCTA onSuccess={() => setIsModalOpen(true)} />
                </div>
              </div>

              {/* Live Data Display */}
              <Card className="bg-black/40 border-white/10 backdrop-blur-xl shadow-2xl">
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-white flex items-center justify-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    Live Market Data
                    {/* Add sync status badge */}
                    <SyncStatusBadge 
                      timestamp={timestamp} 
                      isLoading={isLoading}
                      className="ml-auto text-xs"
                    />
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

              {/* Add MiniROIPreview here */}
              <MiniROIPreview onClick={() => setIsModalOpen(true)} />
            </div>
          </div>
          <ScrollCue />
        </section>

        {/* Features Section */}
        <section id="features" className="pt-24 pb-20 bg-black/20">
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

        {/* Add LogoBar component here - between Features and Stats */}
        <LogoBar />

        {/* Enhanced Stats Section with GpuCounter */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            {/* Add another GpuCounter instance with different styling */}
            <div className="text-center mb-12">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Real-Time
                <span className="block bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                  Market Intelligence
                </span>
              </h2>
              <GpuCounter 
                showDetails={true} 
                animate={true}
                className="justify-center"
              />
            </div>

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