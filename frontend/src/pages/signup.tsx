import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
  Chrome,
  Twitter,
  MessageCircle,
  Sparkles,
  Zap,
  Shield,
  CheckCircle,
  ArrowRight,
  Users,
  TrendingUp,
  Star,
  Gift
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

const SignupPage = () => {
  const { loginWithOAuth, isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [hoveredProvider, setHoveredProvider] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [showBenefits, setShowBenefits] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !loading) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    // Show benefits after a delay
    const timer = setTimeout(() => setShowBenefits(true), 500);
    return () => clearTimeout(timer);
  }, []);

  const providers = [
    {
      id: 'google',
      name: 'Google',
      icon: Chrome,
      color: 'bg-white hover:bg-gray-50 border-2 border-gray-200 hover:border-blue-500',
      textColor: 'text-gray-800',
      gradient: 'from-blue-500 to-red-500',
      description: 'Quick and secure with your Google account'
    },
    {
      id: 'twitter',
      name: 'Twitter',
      icon: Twitter,
      color: 'bg-black hover:bg-gray-900 border-2 border-transparent',
      textColor: 'text-white',
      gradient: 'from-blue-400 to-blue-600',
      description: 'Connect with your Twitter community'
    },
    {
      id: 'discord',
      name: 'Discord',
      icon: MessageCircle,
      color: 'bg-[#5865F2] hover:bg-[#4752C4] border-2 border-transparent',
      textColor: 'text-white',
      gradient: 'from-[#5865F2] to-[#7289DA]',
      description: 'Join our Discord community instantly'
    }
  ];

  const benefits = [
    { icon: Zap, text: "Instant access to GPU yield tracking", delay: 0.1 },
    { icon: Shield, text: "Enterprise-grade security", delay: 0.2 },
    { icon: Users, text: "Join 10,000+ GPU miners", delay: 0.3 },
    { icon: TrendingUp, text: "Real-time profitability analytics", delay: 0.4 }
  ];

  const handleSignup = async (provider: string) => {
    setSelectedProvider(provider);
    
    // Trigger celebration animation
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#3B82F6', '#10B981', '#F59E0B']
    });

    // Small delay for visual feedback
    setTimeout(() => {
      loginWithOAuth(provider);
    }, 300);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4 overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500 rounded-full filter blur-3xl opacity-20 animate-pulse" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-500 rounded-full filter blur-3xl opacity-20 animate-pulse animation-delay-2000" />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-blue-500 to-purple-500 rounded-full filter blur-3xl opacity-10 animate-pulse animation-delay-4000" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-5xl flex flex-col lg:flex-row items-center gap-12"
      >
        {/* Left side - Benefits */}
        <div className="flex-1 text-center lg:text-left">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl lg:text-6xl font-bold text-white mb-6">
              Start Mining
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
                Smarter Today
              </span>
            </h1>
            <p className="text-xl text-gray-300 mb-8">
              Join thousands of miners maximizing their GPU profits with real-time yield analytics.
            </p>
          </motion.div>

          <AnimatePresence>
            {showBenefits && (
              <motion.div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: benefit.delay }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                      <benefit.icon className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-gray-300">{benefit.text}</span>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Social proof */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="mt-8 flex items-center gap-4"
          >
            <div className="flex -space-x-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-400 to-purple-400 border-2 border-gray-900 flex items-center justify-center text-white text-xs font-bold"
                >
                  {String.fromCharCode(65 + i)}
                </div>
              ))}
            </div>
            <div>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Star key={i} className="w-4 h-4 fill-yellow-500 text-yellow-500" />
                ))}
              </div>
              <p className="text-sm text-gray-400">10,000+ miners trust GPU Yield</p>
            </div>
          </motion.div>
        </div>

        {/* Right side - Signup card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-2xl border border-white/20">
            {/* Header */}
            <div className="text-center mb-8">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
                className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto mb-4 flex items-center justify-center"
              >
                <Sparkles className="w-10 h-10 text-white" />
              </motion.div>
              <h2 className="text-3xl font-bold text-white mb-2">Get Started Free</h2>
              <p className="text-gray-300">Choose your preferred sign-in method</p>
            </div>

            {/* Limited time offer */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mb-6 p-4 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-xl border border-yellow-500/30"
            >
              <div className="flex items-center gap-2 text-yellow-300">
                <Gift className="w-5 h-5" />
                <span className="font-semibold">Limited Time: Get Pro features free for 30 days!</span>
              </div>
            </motion.div>

            {/* OAuth providers */}
            <div className="space-y-3">
              {providers.map((provider, index) => (
                <motion.button
                  key={provider.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 * index }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleSignup(provider.id)}
                  onMouseEnter={() => setHoveredProvider(provider.id)}
                  onMouseLeave={() => setHoveredProvider(null)}
                  disabled={selectedProvider !== null}
                  className={`relative w-full p-4 rounded-xl font-medium transition-all duration-200 ${provider.color} ${provider.textColor} ${
                    selectedProvider === provider.id ? 'ring-4 ring-offset-2 ring-offset-gray-900 ring-blue-500' : ''
                  } disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden group`}
                >
                  <div className="relative z-10 flex items-center justify-center gap-3">
                    <provider.icon className="w-5 h-5" />
                    <span>Continue with {provider.name}</span>
                    {selectedProvider === provider.id && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="ml-2"
                      >
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      </motion.div>
                    )}
                  </div>
                  
                  {/* Hover effect */}
                  <motion.div
                    initial={{ x: '-100%' }}
                    animate={{ x: hoveredProvider === provider.id ? '0%' : '-100%' }}
                    transition={{ duration: 0.3 }}
                    className={`absolute inset-0 bg-gradient-to-r ${provider.gradient} opacity-10`}
                  />
                </motion.button>
              ))}
            </div>

            {/* Security badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="mt-8 flex items-center justify-center gap-6 text-gray-400"
            >
              <div className="flex items-center gap-1">
                <Shield className="w-4 h-4" />
                <span className="text-xs">SSL Secured</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle className="w-4 h-4" />
                <span className="text-xs">GDPR Compliant</span>
              </div>
            </motion.div>

            {/* Terms */}
            <p className="text-xs text-center text-gray-400 mt-6">
              By signing up, you agree to our{' '}
              <a href="/terms" className="text-blue-400 hover:text-blue-300 underline">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="/privacy" className="text-blue-400 hover:text-blue-300 underline">
                Privacy Policy
              </a>
            </p>
          </div>

          {/* Login link */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9 }}
            className="text-center mt-6"
          >
            <p className="text-gray-300">
              Already have an account?{' '}
              <a href="/login" className="text-blue-400 hover:text-blue-300 font-medium">
                Sign in
                <ArrowRight className="inline w-4 h-4 ml-1" />
              </a>
            </p>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default SignupPage;