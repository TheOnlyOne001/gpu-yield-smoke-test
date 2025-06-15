import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  XCircle,
  RefreshCw,
  ArrowLeft,
  HelpCircle,
  Shield,
  Chrome,
  Twitter,
  MessageCircle
} from 'lucide-react';

const AuthErrorPage = () => {
  const router = useRouter();
  const [errorDetails, setErrorDetails] = useState({
    message: 'Authentication failed',
    provider: '',
    code: ''
  });

  useEffect(() => {
    if (router.isReady) {
      const { message, provider, error, error_description } = router.query;
      
      setErrorDetails({
        message: (error_description || message || 'Authentication failed') as string,
        provider: (provider || '') as string,
        code: (error || '') as string
      });
    }
  }, [router.isReady, router.query]);

  const getProviderIcon = (provider: string) => {
    switch (provider?.toLowerCase()) {
      case 'google':
        return Chrome;
      case 'twitter':
        return Twitter;
      case 'discord':
        return MessageCircle;
      default:
        return Shield;
    }
  };

  const getProviderName = (provider: string) => {
    switch (provider?.toLowerCase()) {
      case 'google':
        return 'Google';
      case 'twitter':
        return 'Twitter';
      case 'discord':
        return 'Discord';
      default:
        return 'OAuth Provider';
    }
  };

  const commonErrors = [
    {
      code: 'access_denied',
      title: 'Access Denied',
      description: 'You declined the authentication request.',
      solution: 'Click "Try Again" and accept the permissions to continue.'
    },
    {
      code: 'server_error',
      title: 'Server Error',
      description: 'The authentication server encountered an error.',
      solution: 'Please wait a moment and try again.'
    },
    {
      code: 'temporarily_unavailable',
      title: 'Service Unavailable',
      description: 'The authentication service is temporarily unavailable.',
      solution: 'Please try again in a few minutes.'
    }
  ];

  const getErrorInfo = () => {
    const errorInfo = commonErrors.find(e => errorDetails.code.includes(e.code));
    return errorInfo || {
      title: 'Authentication Failed',
      description: errorDetails.message,
      solution: 'Please try again or use a different sign-in method.'
    };
  };

  const errorInfo = getErrorInfo();
  const ProviderIcon = getProviderIcon(errorDetails.provider);

  const handleTryAgain = () => {
    router.push('/login');
  };

  const handleSupport = () => {
    router.push('/support');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex items-center justify-center p-4">
      {/* Animated background */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ff00000a_1px,transparent_1px),linear-gradient(to_bottom,#ff00000a_1px,transparent_1px)] bg-[size:14px_24px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl p-8 shadow-2xl border border-red-500/20">
          {/* Error icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
            className="text-center mb-6"
          >
            <div className="w-20 h-20 bg-red-500/20 rounded-full mx-auto mb-4 flex items-center justify-center relative">
              <XCircle className="w-10 h-10 text-red-500" />
              {errorDetails.provider && (
                <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center border-2 border-red-500/50">
                  <ProviderIcon className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">{errorInfo.title}</h1>
            {errorDetails.provider && (
              <p className="text-sm text-gray-400">
                with {getProviderName(errorDetails.provider)}
              </p>
            )}
          </motion.div>

          {/* Error details */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-4 mb-6"
          >
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-gray-300 text-sm">{errorInfo.description}</p>
                  {errorDetails.code && (
                    <p className="text-xs text-gray-500 mt-1">Error code: {errorDetails.code}</p>
                  )}
                </div>
              </div>
            </div>

            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <div className="flex items-start gap-3">
                <HelpCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-white mb-1">What to do?</p>
                  <p className="text-gray-300 text-sm">{errorInfo.solution}</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Actions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="space-y-3"
          >
            <button
              onClick={handleTryAgain}
              className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-medium rounded-xl hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              Try Again
            </button>

            <button
              onClick={() => router.push('/login')}
              className="w-full py-3 bg-gray-700/50 text-white font-medium rounded-xl hover:bg-gray-700/70 transition-all duration-200 flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Login
            </button>
          </motion.div>

          {/* Help link */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-center mt-6"
          >
            <p className="text-sm text-gray-400">
              Still having issues?{' '}
              <button
                onClick={handleSupport}
                className="text-blue-400 hover:text-blue-300 font-medium"
              >
                Contact Support
              </button>
            </p>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};

export default AuthErrorPage;