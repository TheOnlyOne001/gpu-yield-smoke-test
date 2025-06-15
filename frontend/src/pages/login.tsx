import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Chrome,
  Twitter,
  MessageCircle,
  ArrowRight,
  LogIn,
  Zap,
  Lock,
  Clock,
  ChevronRight,
  Sparkles,
  CheckCircle
} from 'lucide-react';

// Simulated auth hook - replace with your actual auth context
const useAuth = () => {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const loginWithOAuth = async (provider: string) => {
    // Simulate OAuth redirect
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    window.location.href = `${API_BASE_URL}/auth/${provider}/login`;
  };

  return { loginWithOAuth, isAuthenticated, loading };
};

const LoginPage = () => {
  const { loginWithOAuth, isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [lastUsedProvider, setLastUsedProvider] = useState<string | null>(null);
  const [hoveredProvider, setHoveredProvider] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [showBenefits, setShowBenefits] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !loading) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    // Get last used provider from localStorage
    const lastProvider = localStorage.getItem('lastAuthProvider');
    if (lastProvider) {
      setLastUsedProvider(lastProvider);
    }
  }, []);

  const providers = [
    {
      id: 'google',
      name: 'Google',
      icon: Chrome,
      color: 'bg-white hover:bg-gray-50 border-2 border-gray-200 hover:border-blue-500',
      textColor: 'text-gray-800',
      activeColor: 'from-blue-500 to-red-500',
      stats: '5.2M users'
    },
    {
      id: 'twitter',
      name: 'Twitter',
      icon: Twitter,
      color: 'bg-black hover:bg-gray-900 border-2 border-transparent',
      textColor: 'text-white',
      activeColor: 'from-blue-400 to-blue-600',
      stats: '3.8M users'
    },
    {
      id: 'discord',
      name: 'Discord',
      icon: MessageCircle,
      color: 'bg-[#5865F2] hover:bg-[#4752C4] border-2 border-transparent',
      textColor: 'text-white',
      activeColor: 'from-[#5865F2] to-[#7289DA]',
      stats: '2.1M users'
    }
  ];

  // Fix line 84 - add type annotation for provider parameter  
  const handleLogin = async (provider: string) => {
    setSelectedProvider(provider);
    localStorage.setItem('lastAuthProvider', provider);
    
    // Small delay for visual feedback
    setTimeout(() => {
      loginWithOAuth(provider);
    }, 300);
  };

  const features = [
    "Real-time GPU profitability tracking",
    "Advanced mining analytics",
    "Multi-pool optimization",
    "24/7 monitoring & alerts"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated grid background */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff0a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff0a_1px,transparent_1px)] bg-[size:14px_24px]" />
      </div>

      {/* Floating elements */}
      <motion.div
        animate={{
          y: [0, -20, 0],
          rotate: [0, 5, 0]
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute top-20 right-20 w-32 h-32 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full filter blur-xl"
      />
      <motion.div
        animate={{
          y: [0, 20, 0],
          rotate: [0, -5, 0]
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute bottom-20 left-20 w-40 h-40 bg-gradient-to-br from-green-500/20 to-blue-500/20 rounded-full filter blur-xl"
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl p-8 shadow-2xl border border-gray-700/50">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-4">
              <LogIn className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
            <p className="text-gray-400">Sign in to access your dashboard</p>
          </motion.div>

          {/* Quick stats */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="grid grid-cols-3 gap-2 mb-6"
          >
            <div className="text-center p-3 bg-gray-700/30 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">$2.4M</div>
              <div className="text-xs text-gray-400">Daily Volume</div>
            </div>
            <div className="text-center p-3 bg-gray-700/30 rounded-lg">
              <div className="text-2xl font-bold text-green-400">98.5%</div>
              <div className="text-xs text-gray-400">Uptime</div>
            </div>
            <div className="text-center p-3 bg-gray-700/30 rounded-lg">
              <div className="text-2xl font-bold text-purple-400">10K+</div>
              <div className="text-xs text-gray-400">Active Users</div>
            </div>
          </motion.div>

          {/* OAuth providers */}
          <div className="space-y-3 mb-6">
            {providers.map((provider, index) => {
              const isLastUsed = lastUsedProvider === provider.id;
              const isSelected = selectedProvider === provider.id;
              
              return (
                <motion.div
                  key={provider.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="relative"
                >
                  {isLastUsed && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 z-10"
                    >
                      <Clock className="w-3 h-3" />
                      Last used
                    </motion.div>
                  )}
                  
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleLogin(provider.id)}
                    onMouseEnter={() => setHoveredProvider(provider.id)}
                    onMouseLeave={() => setHoveredProvider(null)}
                    disabled={selectedProvider !== null}
                    className={`relative w-full p-4 rounded-xl font-medium transition-all duration-200 ${provider.color} ${provider.textColor} ${
                      isSelected ? 'ring-4 ring-offset-2 ring-offset-gray-800 ring-blue-500' : ''
                    } disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden group`}
                  >
                    <div className="relative z-10 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <provider.icon className="w-5 h-5" />
                        <span>Continue with {provider.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs opacity-60">{provider.stats}</span>
                        {isSelected ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <ChevronRight className="w-5 h-5 opacity-60 group-hover:opacity-100 transition-opacity" />
                        )}
                      </div>
                    </div>
                    
                    {/* Hover gradient */}
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: hoveredProvider === provider.id ? 0.1 : 0 }}
                      className={`absolute inset-0 bg-gradient-to-r ${provider.activeColor}`}
                    />
                  </motion.button>
                </motion.div>
              );
            })}
          </div>

          {/* Security notice */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-2 text-xs text-gray-500 mb-4"
          >
            <Lock className="w-3 h-3" />
            <span>Secure authentication powered by OAuth 2.0</span>
          </motion.div>

          {/* Features reminder */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="border-t border-gray-700 pt-4"
          >
            <p className="text-xs text-gray-400 mb-2">What you'll get access to:</p>
            <div className="grid grid-cols-2 gap-2">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 + index * 0.1 }}
                  className="flex items-start gap-1"
                >
                  <Zap className="w-3 h-3 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-xs text-gray-300">{feature}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Sign up link */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-center mt-6"
        >
          <p className="text-gray-400">
            Don't have an account?{' '}
            <a href="/signup" className="text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1">
              Sign up for free
              <Sparkles className="w-4 h-4" />
            </a>
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default LoginPage;