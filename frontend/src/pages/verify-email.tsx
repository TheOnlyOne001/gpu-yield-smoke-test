import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '@/contexts/AuthContext';
import {
  Mail,
  CheckCircle,
  AlertCircle,
  Loader2,
  Clock,
  RefreshCw,
  ArrowRight,
  Send
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const VerifyEmailPage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const { sent } = router.query; // Check if redirected after sending verification
  
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState('');
  const [resendError, setResendError] = useState('');
  const [canResend, setCanResend] = useState(true);
  const [countdown, setCountdown] = useState(0);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  // Redirect if already verified
  useEffect(() => {
    if (isAuthenticated && user?.is_verified) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, user, router]);

  // Handle countdown for resend button
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setCanResend(true);
    }
  }, [countdown]);

  const handleResendVerification = async () => {
    if (!canResend || isResending) return;

    setIsResending(true);
    setResendError('');
    setResendMessage('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setResendError('Please sign in again');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (response.ok) {
        setResendMessage('Verification email sent successfully!');
        setCanResend(false);
        setCountdown(60); // 60 second cooldown
      } else {
        if (response.status === 429) {
          setResendError('Too many emails sent. Please wait before requesting another.');
          setCanResend(false);
          setCountdown(300); // 5 minute cooldown for rate limiting
        } else {
          setResendError(data.detail || 'Failed to send verification email');
        }
      }
    } catch (err) {
      setResendError('Network error. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Verify Email - GPU Yield</title>
        <meta name="description" content="Verify your email address to complete your GPU Yield account setup" />
      </Head>

      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          {/* Header */}
          <div className="text-center">
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
              Verify your email
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Check your inbox and click the verification link
            </p>
          </div>

          <Card>
            <CardHeader className="text-center">
              <Mail className="w-16 h-16 text-blue-500 mx-auto mb-4" />
              <CardTitle>Email Verification Required</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Success message if redirected after sending */}
              {sent && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                  <span className="text-sm text-green-700 dark:text-green-400">
                    Verification email sent successfully!
                  </span>
                </div>
              )}

              {/* Resend success message */}
              {resendMessage && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                  <span className="text-sm text-green-700 dark:text-green-400">
                    {resendMessage}
                  </span>
                </div>
              )}

              {/* Resend error message */}
              {resendError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-sm text-red-700 dark:text-red-400">
                    {resendError}
                  </span>
                </div>
              )}

              <div className="text-center space-y-4">
                <div className="space-y-2">
                  <p className="text-gray-600 dark:text-gray-400">
                    We've sent a verification email to:
                  </p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {user.email}
                  </p>
                </div>

                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
                  <div className="flex items-start">
                    <Clock className="w-5 h-5 text-blue-500 mr-2 mt-0.5" />
                    <div className="text-sm text-left">
                      <p className="text-blue-700 dark:text-blue-400 font-medium">
                        Check your email
                      </p>
                      <p className="text-blue-600 dark:text-blue-400 mt-1">
                        Click the verification link in your email to complete your account setup. 
                        The link expires in 24 hours.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <p>Didn't receive the email?</p>
                  <ul className="mt-2 space-y-1 text-left">
                    <li>• Check your spam or junk folder</li>
                    <li>• Make sure {user.email} is correct</li>
                    <li>• Wait a few minutes for the email to arrive</li>
                  </ul>
                </div>

                <div className="space-y-2">
                  <Button
                    onClick={handleResendVerification}
                    disabled={!canResend || isResending}
                    variant="outline"
                    className="w-full"
                  >
                    {isResending ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : !canResend && countdown > 0 ? (
                      <>
                        <Clock className="w-4 h-4 mr-2" />
                        Resend in {countdown}s
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Resend verification email
                      </>
                    )}
                  </Button>

                  <Button
                    onClick={() => router.push('/dashboard')}
                    className="w-full"
                  >
                    Continue to Dashboard
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Help Section */}
          <div className="text-center space-y-4">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-yellow-500 mr-2 mt-0.5" />
                <div className="text-sm text-left">
                  <p className="text-yellow-700 dark:text-yellow-400 font-medium">
                    Why verify your email?
                  </p>
                  <p className="text-yellow-600 dark:text-yellow-400 mt-1">
                    Email verification helps secure your account and ensures you receive important 
                    notifications about your GPU yield activities.
                  </p>
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400">
              Need help?{' '}
              <Link href="/support" className="font-medium text-blue-600 hover:text-blue-500">
                Contact Support
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default VerifyEmailPage;