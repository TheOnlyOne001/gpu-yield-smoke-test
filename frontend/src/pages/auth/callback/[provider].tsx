import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Loader2, AlertCircle } from 'lucide-react';
import Head from 'next/head';

const OAuthCallbackPage: React.FC = () => {
  const router = useRouter();
  const { provider } = router.query;
  const [timeLeft, setTimeLeft] = useState(10);
  const [hasTimedOut, setHasTimedOut] = useState(false);

  useEffect(() => {
    let timeoutTimer: NodeJS.Timeout;
    let countdownTimer: NodeJS.Timeout;

    const handleCallback = async () => {
      try {
        // Start countdown
        countdownTimer = setInterval(() => {
          setTimeLeft((prev) => {
            if (prev <= 1) {
              clearInterval(countdownTimer);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);

        // Set timeout for callback processing
        timeoutTimer = setTimeout(() => {
          if (router.pathname.includes('/auth/callback/')) {
            setHasTimedOut(true);
            clearInterval(countdownTimer);
          }
        }, 10000);
        
      } catch (error) {
        console.error('OAuth callback error:', error);
        router.push('/auth/error?message=Callback processing failed');
      }
    };

    if (provider) {
      handleCallback();
    }

    return () => {
      if (timeoutTimer) clearTimeout(timeoutTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    };
  }, [provider, router]);

  const handleRetry = () => {
    router.push('/login');
  };

  const getProviderDisplayName = (provider: string | string[]): string => {
    if (Array.isArray(provider)) provider = provider[0];
    
    switch (provider?.toLowerCase()) {
      case 'google': return 'Google';
      case 'twitter': return 'Twitter';
      case 'discord': return 'Discord';
      default: return provider || 'OAuth';
    }
  };

  if (hasTimedOut) {
    return (
      <>
        <Head>
          <title>Authentication Timeout - GPU Yield</title>
          <meta name="robots" content="noindex" />
        </Head>
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <div className="text-center max-w-md">
            <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Authentication Timeout
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              The authentication process is taking longer than expected.
            </p>
            <button 
              onClick={handleRetry}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>Completing Authentication - GPU Yield</title>
        <meta name="robots" content="noindex" />
      </Head>
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <div className="text-center max-w-md">
          <div className="mb-6">
            <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
              Completing Authentication
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              {provider && typeof provider === 'string' 
                ? `Processing ${getProviderDisplayName(provider)} authentication...`
                : 'Processing authentication...'}
            </p>
          </div>
          
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
              <span>This may take a few moments</span>
              {timeLeft > 0 && (
                <>
                  <span>•</span>
                  <span>{timeLeft}s remaining</span>
                </>
              )}
            </div>
          </div>
          
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
            Please don't close this window while we complete your authentication.
          </p>
        </div>
      </div>
    </>
  );
};

export default OAuthCallbackPage;