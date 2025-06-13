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
    const handleOAuthSuccess = async () => {
      const { token, provider, user } = router.query;

      console.log('OAuth success page loaded:', { 
        token: !!token, 
        provider, 
        user: !!user 
      });

      if (token && typeof token === 'string') {
        try {
          // Store token
          localStorage.setItem('access_token', token);
          console.log('Token stored successfully');

          // Parse user data with better error handling
          if (user && typeof user === 'string') {
            try {
              const decodedUser = decodeURIComponent(user);
              console.log('Decoded user data:', decodedUser);
              
              const parsedUser = JSON.parse(decodedUser);
              console.log('Parsed user data:', parsedUser);
              setUserInfo(parsedUser);
            } catch (parseError) {
              console.warn('Could not parse user data (non-critical):', parseError);
              // Don't fail the entire flow if user data parsing fails
            }
          }

          // Refresh user data from server (this is the important part)
          console.log('Refreshing user data from server...');
          await refreshUser();
          
          console.log('OAuth success processing complete');
          setIsProcessing(false);
          
          // Start countdown to redirect
          const timer = setInterval(() => {
            setCountdown((prev) => {
              if (prev <= 1) {
                clearInterval(timer);
                
                // Redirect to intended page
                const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
                sessionStorage.removeItem('auth_return_to');
                
                // Use replace to prevent back button issues
                router.replace(returnTo);
                return 0;
              }
              return prev - 1;
            });
          }, 1000);

          return () => clearInterval(timer);
          
        } catch (error) {
          console.error('OAuth success processing error:', error);
          
          // Clean up and redirect to login
          localStorage.removeItem('access_token');
          router.replace('/login?error=oauth_processing_failed');
        }
      } else {
        console.error('No token found in OAuth success callback');
        router.replace('/login?error=no_token');
      }
    };

    // Only run if router is ready and we have query params
    if (router.isReady && (router.query.token || router.query.error)) {
      handleOAuthSuccess();
    }
  }, [router.isReady, router.query, refreshUser]);
  const handleContinue = () => {
    const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
    sessionStorage.removeItem('auth_return_to');
    router.replace(returnTo);
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