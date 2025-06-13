import React, { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  Mail,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  Loader2,
  Clock
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ForgotPasswordPage: React.FC = () => {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setIsSubmitted(true);
      } else {
        setError(data.detail || 'Failed to send reset email');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendEmail = () => {
    setIsSubmitted(false);
    setEmail('');
  };

  return (
    <>
      <Head>
        <title>Forgot Password - GPU Yield</title>
        <meta name="description" content="Reset your GPU Yield password" />
      </Head>

      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          {/* Header */}
          <div className="text-center">
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
              {isSubmitted ? 'Check your email' : 'Forgot your password?'}
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              {isSubmitted 
                ? "We've sent a password reset link to your email"
                : "No worries, we'll send you reset instructions"
              }
            </p>
          </div>

          <Card>
            <CardHeader className="text-center">
              {isSubmitted ? (
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              ) : (
                <Mail className="w-16 h-16 text-blue-500 mx-auto mb-4" />
              )}
              <CardTitle>
                {isSubmitted ? 'Email Sent' : 'Reset Password'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Error Message */}
              {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
                </div>
              )}

              {isSubmitted ? (
                /* Success State */
                <div className="space-y-4">
                  <div className="text-center space-y-2">
                    <p className="text-gray-600 dark:text-gray-400">
                      We've sent a password reset link to:
                    </p>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {email}
                    </p>
                  </div>

                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
                    <div className="flex items-start">
                      <Clock className="w-5 h-5 text-blue-500 mr-2 mt-0.5" />
                      <div className="text-sm">
                        <p className="text-blue-700 dark:text-blue-400 font-medium">
                          Link expires in 1 hour
                        </p>
                        <p className="text-blue-600 dark:text-blue-400 mt-1">
                          If you don't see the email, check your spam folder or try again.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Button
                      onClick={handleResendEmail}
                      variant="outline"
                      className="w-full"
                    >
                      Send another email
                    </Button>
                    
                    <Button
                      onClick={() => router.push('/login')}
                      className="w-full"
                    >
                      Back to Sign In
                    </Button>
                  </div>
                </div>
              ) : (
                /* Form State */
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Email address
                    </label>
                    <div className="mt-1 relative">
                      <Mail className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                      <input
                        id="email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="pl-10 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                        placeholder="Enter your email address"
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting || !email}
                    className="w-full"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      'Send Reset Link'
                    )}
                  </Button>

                  <div className="text-center">
                    <Link
                      href="/login"
                      className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500"
                    >
                      <ArrowLeft className="w-4 h-4 mr-1" />
                      Back to Sign In
                    </Link>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Help Section */}
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Still having trouble?{' '}
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

export default ForgotPasswordPage;