import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
  CheckCircle,
  Sparkles,
  Gift,
  Zap,
  Trophy,
  Star,
  ArrowRight,
  Loader2,
  User
} from 'lucide-react';

const AuthSuccessPage = () => {
  const router = useRouter();
  const [countdown, setCountdown] = useState(5);
  const [userInfo, setUserInfo] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const [showRewards, setShowRewards] = useState(false);

  useEffect(() => {
    const handleOAuthSuccess = async () => {
      const { token, provider, user: userDataEncoded, error } = router.query;

      if (error) {
        router.replace(`/login?error=${error}`);
        return;
      }

      if (token) {
        try {
          // Store token
          localStorage.setItem('access_token', token as string);
          
          // Decode user data if provided
          if (userDataEncoded) {
            try {
              const userData = JSON.parse(decodeURIComponent(userDataEncoded as string));
              setUserInfo(userData);
            } catch (e) {
              console.error('Failed to parse user data:', e);
            }
          }

          // Trigger celebration
          setTimeout(() => {
            setIsProcessing(false);
            setShowRewards(true);
            triggerCelebration();
          }, 1000);

          // Start countdown
          const timer = setInterval(() => {
            setCountdown((prev) => {
              if (prev <= 1) {
                clearInterval(timer);
                
                // Redirect to dashboard
                const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
                sessionStorage.removeItem('auth_return_to');
                router.replace(returnTo);
                return 0;
              }
              return prev - 1;
            });
          }, 1000);

          return () => clearInterval(timer);
          
        } catch (error) {
          console.error('OAuth success processing error:', error);
          router.replace('/login?error=oauth_processing_failed');
        }
      } else {
        router.replace('/login?error=no_token');
      }
    };

    if (router.isReady) {
      handleOAuthSuccess();
    }
  }, [router.isReady, router.query]);

  const triggerCelebration = () => {
    // Multiple confetti bursts
    const count = 200;
    const defaults = {
      origin: { y: 0.7 },
      zIndex: 1000
    };

    function fire(particleRatio: number, opts: any) {
      confetti({
        ...defaults,
        ...opts,
        particleCount: Math.floor(count * particleRatio)
      });
    }

    fire(0.25, {
      spread: 26,
      startVelocity: 55,
    });
    fire(0.2, {
      spread: 60,
    });
    fire(0.35, {
      spread: 100,
      decay: 0.91,
      scalar: 0.8
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 25,
      decay: 0.92,
      scalar: 1.2
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 45,
    });
  };

  const rewards = [
    { icon: Gift, text: "30 days Pro features unlocked", color: "text-purple-500" },
    { icon: Zap, text: "Instant access to all features", color: "text-yellow-500" },
    { icon: Trophy, text: "Welcome bonus applied", color: "text-blue-500" },
    { icon: Star, text: "Priority support activated", color: "text-green-500" }
  ];

  const handleContinue = () => {
    const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
    sessionStorage.removeItem('auth_return_to');
    router.replace(returnTo);
  };

  if (isProcessing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Loader2 className="w-12 h-12 animate-spin text-blue-400 mx-auto mb-4" />
          <p className="text-white text-lg">Setting up your account...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4 overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0">
        <div className="absolute top-20 left-20 w-96 h-96 bg-blue-500 rounded-full filter blur-3xl opacity-20 animate-pulse" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-purple-500 rounded-full filter blur-3xl opacity-20 animate-pulse animation-delay-2000" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-2xl"
      >
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-2xl border border-white/20">
          {/* Success header */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
            className="text-center mb-8"
          >
            <div className="w-24 h-24 bg-gradient-to-r from-green-400 to-blue-500 rounded-full mx-auto mb-4 flex items-center justify-center">
              <CheckCircle className="w-12 h-12 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-white mb-2">Welcome to GPU Yield!</h1>
            <p className="text-xl text-gray-300">Your account is ready to rock 🚀</p>
          </motion.div>

          {/* User info */}
          {userInfo && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex items-center justify-center space-x-4 mb-8 p-4 bg-white/10 rounded-xl"
            >
              {userInfo.avatar_url ? (
                <img 
                  src={userInfo.avatar_url} 
                  alt="Profile" 
                  className="w-16 h-16 rounded-full border-2 border-white/50"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                  <User className="w-8 h-8 text-white" />
                </div>
              )}
              <div className="text-left">
                <p className="text-lg font-semibold text-white">
                  {userInfo.full_name || userInfo.username || 'GPU Miner'}
                </p>
                <p className="text-sm text-gray-300">{userInfo.email}</p>
              </div>
            </motion.div>
          )}

          {/* Rewards */}
          <AnimatePresence>
            {showRewards && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-3 mb-8"
              >
                <h3 className="text-lg font-semibold text-white text-center mb-4">
                  🎉 Your Welcome Rewards
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {rewards.map((reward, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                      className="flex items-center gap-3 p-3 bg-white/10 rounded-lg backdrop-blur-sm"
                    >
                      <div className={`w-10 h-10 rounded-full bg-white/20 flex items-center justify-center ${reward.color}`}>
                        <reward.icon className="w-5 h-5" />
                      </div>
                      <span className="text-white">{reward.text}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between text-sm text-gray-300 mb-2">
              <span>Redirecting to your dashboard...</span>
              <span>{countdown}s</span>
            </div>
            <div className="w-full bg-white/20 rounded-full h-2 overflow-hidden">
              <motion.div
                initial={{ width: "100%" }}
                animate={{ width: "0%" }}
                transition={{ duration: 5, ease: "linear" }}
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
              />
            </div>
          </div>

          {/* Continue button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleContinue}
            className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold rounded-xl hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2"
          >
            Continue to Dashboard
            <ArrowRight className="w-5 h-5" />
          </motion.button>

          {/* Fun fact */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-6 text-center"
          >
            <p className="text-sm text-gray-400">
              <Sparkles className="inline w-4 h-4 mr-1" />
              Fun fact: You're joining at the perfect time - GPU yields are up 23% this month!
            </p>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};

export default AuthSuccessPage;