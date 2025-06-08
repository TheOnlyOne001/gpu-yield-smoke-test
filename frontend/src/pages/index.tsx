import React, { useState, useEffect, FormEvent } from 'react';
import Head from 'next/head';
import useSWR from 'swr';
import { Zap, Calculator, Mail, X } from 'lucide-react';

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
      refreshInterval: 30000, // Refresh every 30 seconds
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
    
    // Find the deal with the highest price
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
      // You might want to show an error message to the user here
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

      <div className="min-h-screen bg-gray-900 text-white">
        {/* Hero Section */}
        <section className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
              Stop Guessing, Start Earning
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-8">
              Find the most profitable GPU rental platform in real-time.
            </p>

            {/* Live Data Display */}
            <div className="bg-gray-800 rounded-lg p-6 mb-8 shadow-xl">
              {isLoading && (
                <div className="flex items-center justify-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  <p className="text-gray-400">Loading best prices...</p>
                </div>
              )}
              {error && (
                <p className="text-red-400">Unable to fetch live pricing data. Please try again later.</p>
              )}
              {bestDeal && !isLoading && (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <p className="text-lg font-semibold">
                    Live Deal: Rent your {bestDeal.gpu_model} on {bestDeal.best_source} for ${bestDeal.price_usd_hr.toFixed(3)}/hr
                  </p>
                </div>
              )}
              {!bestDeal && !isLoading && !error && (
                <p className="text-gray-400">No pricing data available at the moment.</p>
              )}
            </div>

            {/* CTA Button */}
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-lg text-lg transition-all transform hover:scale-105 shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900"
            >
              Calculate My Profit
            </button>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="container mx-auto px-4 py-16 border-t border-gray-800">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12">
            Real-Time Profit, Simplified
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="bg-gray-800 rounded-lg p-6 text-center hover:bg-gray-750 transition-colors">
              <Zap className="w-12 h-12 mx-auto mb-4 text-yellow-400" />
              <h3 className="text-xl font-bold mb-2">1. Real-Time Scrape</h3>
              <p className="text-gray-400">
                We continuously monitor GPU rental prices across all major platforms.
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-6 text-center hover:bg-gray-750 transition-colors">
              <Calculator className="w-12 h-12 mx-auto mb-4 text-green-400" />
              <h3 className="text-xl font-bold mb-2">2. Instant Calculation</h3>
              <p className="text-gray-400">
                Calculate your exact profit based on your GPU and electricity costs.
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-6 text-center hover:bg-gray-750 transition-colors">
              <Mail className="w-12 h-12 mx-auto mb-4 text-blue-400" />
              <h3 className="text-xl font-bold mb-2">3. Profit Alerts</h3>
              <p className="text-gray-400">
                Get notified when profitable opportunities match your criteria.
              </p>
            </div>
          </div>
        </section>

        {/* Signup Form Section */}
        <section className="container mx-auto px-4 py-16">
          <div className="max-w-md mx-auto bg-gray-800 rounded-lg p-8 shadow-xl">
            <h2 className="text-2xl font-bold mb-6 text-center">
              Get Profit Alerts
            </h2>
            <form onSubmit={handleSignupSubmit}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                disabled={signupStatus === 'loading'}
                className="w-full px-4 py-3 bg-gray-700 text-white rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={signupStatus === 'loading' || !email.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {signupStatus === 'loading' ? 'Signing Up...' : 'Sign Up for Alerts'}
              </button>
            </form>
            {signupMessage && (
              <p className={`mt-4 text-center ${
                signupStatus === 'success' ? 'text-green-400' : 'text-red-400'
              }`}>
                {signupMessage}
              </p>
            )}
          </div>
        </section>

        {/* ROI Calculator Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div 
              className="absolute inset-0 bg-black bg-opacity-50"
              onClick={() => setIsModalOpen(false)}
            ></div>
            
            {/* Modal Panel */}
            <div className="relative bg-gray-800 rounded-lg p-8 max-w-md w-full shadow-2xl">
              <button
                onClick={() => setIsModalOpen(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white focus:outline-none"
              >
                <X className="w-6 h-6" />
              </button>
              
              <h2 className="text-2xl font-bold mb-6">ROI Calculator</h2>
              
              <form onSubmit={handleRoiCalc}>
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">GPU Model</label>
                  <input
                    type="text"
                    value={gpuModel}
                    onChange={(e) => setGpuModel(e.target.value)}
                    placeholder="e.g., RTX 4090"
                    required
                    disabled={roiLoading}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                </div>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">Hours per Day</label>
                  <input
                    type="number"
                    value={hoursPerDay}
                    onChange={(e) => setHoursPerDay(e.target.value)}
                    placeholder="e.g., 24"
                    min="0"
                    max="24"
                    step="0.5"
                    required
                    disabled={roiLoading}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                </div>
                
                <div className="mb-6">
                  <label className="block text-sm font-medium mb-2">Power Cost ($/kWh)</label>
                  <input
                    type="number"
                    value={powerCost}
                    onChange={(e) => setPowerCost(e.target.value)}
                    placeholder="e.g., 0.12"
                    min="0"
                    step="0.01"
                    required
                    disabled={roiLoading}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                </div>
                
                <button
                  type="submit"
                  disabled={!gpuModel.trim() || !hoursPerDay || !powerCost || roiLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {roiLoading ? 'Calculating...' : 'Calculate'}
                </button>
              </form>
              
              {roiResult !== null && (
                <div className="mt-6 p-4 bg-gray-700 rounded-lg text-center">
                  <h3 className={`text-xl font-bold ${roiResult > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Potential Monthly Profit: ${roiResult.toFixed(2)}
                  </h3>
                  {roiResult <= 0 && (
                    <p className="text-sm text-gray-400 mt-2">
                      Consider reducing power costs or increasing rental hours
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default HomePage;