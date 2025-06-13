import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { AlertCircle, RefreshCw, ArrowLeft, Home, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const AuthErrorPage: React.FC = () => {
  const router = useRouter();
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [errorDetails, setErrorDetails] = useState<string>('');
  const [provider, setProvider] = useState<string>('');

  useEffect(() => {
    const { message, error, error_description, provider: queryProvider } = router.query;
    
    // Set provider
    if (queryProvider && typeof queryProvider === 'string') {
      setProvider(queryProvider);
    }
    
    // Set error message from query parameters
    if (message && typeof message === 'string') {
      setErrorMessage(message);
    } else if (error && typeof error === 'string') {
      setErrorMessage(getErrorMessage(error));
      if (error_description && typeof error_description === 'string') {
        setErrorDetails(error_description);
      }
    } else {
      setErrorMessage('Authentication failed');
    }
  }, [router.query]);

  const getErrorMessage = (error: string): string => {
    const errorMessages: Record<string, string> = {
      'access_denied': 'Access was denied. You may have cancelled the authentication process.',
      'invalid_request': 'The authentication request was invalid.',
      'unauthorized_client': 'The application is not authorized to perform this request.',
      'unsupported_response_type': 'The authorization server does not support this response type.',
      'invalid_scope': 'The requested scope is invalid, unknown, or malformed.',
      'server_error': 'The authorization server encountered an unexpected condition.',
      'temporarily_unavailable': 'The authorization server is temporarily overloaded or under maintenance.',
      'invalid_client': 'Client authentication failed.',
      'invalid_grant': 'The provided authorization grant is invalid.',
      'unsupported_grant_type': 'The authorization grant type is not supported.',
      'email_already_exists': 'An account with this email already exists. Try signing in instead.',
      'provider_error': 'The authentication provider encountered an error.',
      'callback_timeout': 'The authentication process timed out.',
      'no_token': 'No authentication token was received.',
    };

    return errorMessages[error] || `Authentication error: ${error}`;
  };

  const handleRetry = () => {
    router.push('/login');
  };

  const handleGoHome = () => {
    router.push('/');
  };

  const getSuggestedActions = () => {
    const suggestions = [];
    
    if (errorMessage.includes('cancelled')) {
      suggestions.push('Try the authentication process again');
    }
    
    if (errorMessage.includes('email already exists')) {
      suggestions.push('Try signing in with your existing account');
      suggestions.push('Use the "Forgot Password" option if needed');
    }
    
    if (errorMessage.includes('temporarily unavailable')) {
      suggestions.push('Wait a few minutes and try again');
    }
    
    if (provider) {
      suggestions.push(`Check your ${provider} account permissions`);
    }
    
    return suggestions;
  };

  const suggestions = getSuggestedActions();

  return (
    <>
      <Head>
        <title>Authentication Error - GPU Yield</title>
        <meta name="description" content="Authentication error occurred" />
        <meta name="robots" content="noindex" />
      </Head>

      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <CardTitle className="text-2xl text-red-600">
              Authentication Failed
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center">
              <p className="text-gray-600 dark:text-gray-400 mb-2">
                {errorMessage}
              </p>
              
              {provider && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Provider: {provider.charAt(0).toUpperCase() + provider.slice(1)}
                </p>
              )}
              
              {errorDetails && (
                <div className="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-3 rounded-md mt-3">
                  <strong>Details:</strong> {errorDetails}
                </div>
              )}
            </div>

            {suggestions.length > 0 && (
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md">
                <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
                  Suggested Actions:
                </h4>
                <ul className="text-sm text-blue-700 dark:text-blue-300 list-disc list-inside space-y-1">
                  {suggestions.map((suggestion, index) => (
                    <li key={index}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-2">
              <Button onClick={handleRetry} className="w-full">
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              
              <Button onClick={handleGoHome} variant="outline" className="w-full">
                <Home className="w-4 h-4 mr-2" />
                Go to Homepage
              </Button>
            </div>

            <div className="text-center pt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                Still having trouble?
              </p>
              <div className="flex justify-center space-x-4">
                <Link 
                  href="/support" 
                  className="text-sm text-blue-600 hover:text-blue-500 font-medium flex items-center"
                >
                  <Mail className="w-3 h-3 mr-1" />
                  Contact Support
                </Link>
                <Link 
                  href="/login" 
                  className="text-sm text-gray-600 hover:text-gray-500 font-medium flex items-center"
                >
                  <ArrowLeft className="w-3 h-3 mr-1" />
                  Back to Login
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default AuthErrorPage;