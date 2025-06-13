import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { CheckCircle, Loader2, ArrowRight, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';

const AuthSuccessPage: React.FC = () => {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [countdown, setCountdown] = useState(3);
  const [isProcessing, setIsProcessing] = useState(true);
  const [userInfo, setUserInfo] = useState<any>(null);

  useEffect(() => {
    // Handle OAuth token from URL
    const { token, provider, user } = router.query;
    
    if (token && typeof token === 'string') {
      // Store token in localStorage
      localStorage.setItem('access_token', token);
      
      // Parse user info if available
      if (user && typeof user === 'string') {
        try {
          setUserInfo(JSON.parse(decodeURIComponent(user)));
        } catch (error) {
          console.error('Error parsing user info:', error);
        }
      }
      
      // Refresh user context
      refreshUser().then(() => {
        setIsProcessing(false);
        
        // Start countdown to redirect
        const timer = setInterval(() => {
          setCountdown((prev) => {
            if (prev <= 1) {
              clearInterval(timer);
              router.push('/dashboard');
              return 0;
            }
            return prev - 1;
          });
        }, 1000);

        return () => clearInterval(timer);
      });
    } else {
      // No token found, redirect to login
      router.push('/login?error=no_token');
    }
  }, [router, refreshUser]);

  const handleContinue = () => {
    router.push('/dashboard');
  };

  if (isProcessing) {
    return (
      <>
        <Head>
          <title>Processing Authentication - GPU Yield</title>
          <meta name="robots" content="noindex" />
        </Head>
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Processing authentication...</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>Authentication Successful - GPU Yield</title>
        <meta name="description" content="Authentication successful" />
        <meta name="robots" content="noindex" />
      </Head>

      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <CardTitle className="text-2xl text-green-600">
              Welcome to GPU Yield!
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            {userInfo && (
              <div className="flex items-center justify-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                {userInfo.avatar_url ? (
                  <img 
                    src={userInfo.avatar_url} 
                    alt="Profile" 
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <User className="w-10 h-10 text-gray-400" />
                )}
                <div className="text-left">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {userInfo.full_name || userInfo.username || userInfo.email}
                  </p>
                  {userInfo.email && (
                    <p className="text-sm text-gray-500">{userInfo.email}</p>
                  )}
                </div>
              </div>
            )}
            
            <p className="text-gray-600 dark:text-gray-400">
              Your account has been successfully authenticated and you're ready to start tracking GPU yields!
            </p>
            
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
              <span>Redirecting to dashboard in</span>
              <span className="font-mono font-bold text-blue-600">{countdown}</span>
              <span>seconds...</span>
            </div>

            <Button onClick={handleContinue} className="w-full">
              Continue to Dashboard
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default AuthSuccessPage;