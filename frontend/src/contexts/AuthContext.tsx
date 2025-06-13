import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/router';

// Types
interface User {
  id: number;
  email: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  auth_provider: 'email' | 'google' | 'twitter' | 'discord';
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  gpu_models_interested?: string[];
  min_profit_threshold?: number;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginWithOAuth: (provider: string) => Promise<void>;
  logout: () => Promise<void>;
  signup: (email: string, password: string, username?: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
  sendVerificationEmail: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  isAuthenticated: boolean;
  clearError: () => void;
}

interface AuthProviderProps {
  children: ReactNode;
}

interface LoginAttempt {
  timestamp: number;
  success: boolean;
}

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth Provider Component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [oauthCallbackProcessed, setOauthCallbackProcessed] = useState(false);
  const router = useRouter();

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Handle route protection
  useEffect(() => {
    if (!loading) {
      handleRouteProtection();
    }
  }, [user, loading, router.pathname]);

  // Clear error when route changes
  useEffect(() => {
    setError(null);
  }, [router.pathname]);

  // API Helper function
  const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const token = localStorage.getItem('access_token');
    
    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    if (response.status === 401) {
      // Token expired or invalid
      handleTokenExpiry();
      throw new Error('Authentication required');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    return response.json();
  };

  // Handle token expiry
  const handleTokenExpiry = () => {
    localStorage.removeItem('access_token');
    setUser(null);
    if (!isPublicRoute(router.pathname)) {
      router.push('/login?expired=true');
    }
  };

  // Check if route is public
  const isPublicRoute = (pathname: string): boolean => {
    const publicRoutes = [
      '/',
      '/login',
      '/signup',
      '/forgot-password',
      '/reset-password',
      '/auth/success',
      '/auth/error',
      '/auth/callback',
      '/privacy',
      '/terms',
      '/support',
      '/about'
    ];
    
    return publicRoutes.some(route => {
      if (route === '/') return pathname === '/';
      return pathname.startsWith(route);
    });
  };

  // Handle route protection
  const handleRouteProtection = () => {
    const isPublic = isPublicRoute(router.pathname);
    const isAuthRoute = ['/login', '/signup'].includes(router.pathname);

    if (!isPublic && !user) {
      // Protected route without authentication
      router.push('/login');
    } else if (isAuthRoute && user) {
      // Auth route with authenticated user
      router.push('/dashboard');
    }
  };

  // Check authentication status
  const checkAuthStatus = async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      console.log('No token found');
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      console.log('Checking auth status with token...');
      setLoading(true);
      
      // ✅ CORRECT ENDPOINT
      const data = await apiCall('/auth/users/me');
      console.log('User data received:', data);
      setUser(data);
      setError(null);
      
    } catch (error) {
      console.error('Auth check error:', error);
      
      // Only remove token if we're not in OAuth callback
      if (!window.location.pathname.includes('/auth/success')) {
        localStorage.removeItem('access_token');
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  };

  // Refresh user data
  const refreshUser = async () => {
    if (!localStorage.getItem('access_token')) return;

    try {
      // ✅ CORRECT ENDPOINT
      const data = await apiCall('/auth/users/me');
      setUser(data);
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  };

  // Email/Password Login
  const login = async (email: string, password: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const formData = new FormData();
      formData.append('username', email.toLowerCase().trim());
      formData.append('password', password);

      const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Store token
      localStorage.setItem('access_token', data.access_token);
      
      // Set user data
      if (data.user) {
        setUser(data.user);
      } else {
        // Fetch user data separately
        await checkAuthStatus();
      }
      
      // Record successful login
      recordLoginAttempt(true);
      
      // Redirect to dashboard or intended page
      const returnTo = router.query.returnTo as string;
      router.push(returnTo || '/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      recordLoginAttempt(false);
      setError(error instanceof Error ? error.message : 'Login failed');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // OAuth Login
  const loginWithOAuth = async (provider: string) => {
    try {
      setError(null);
      
      // Store current path for redirect after auth
      const returnTo = router.asPath !== '/login' ? router.asPath : '/dashboard';
      sessionStorage.setItem('auth_return_to', returnTo);
      
      // Redirect to OAuth provider
      window.location.href = `${API_BASE_URL}/auth/${provider}/login`;
    } catch (error) {
      console.error(`${provider} login error:`, error);
      setError(`Failed to initiate ${provider} login`);
      throw error;
    }
  };

  // Signup
  const signup = async (email: string, password: string, username?: string) => {
    try {
      setLoading(true);
      setError(null);

      const signupData = {
        email: email.toLowerCase().trim(),
        password,
        username: username?.trim(),
        hcaptcha_response: 'development-test-key', // Replace with actual hCaptcha in production
      };

      const data = await apiCall('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(signupData),
      });
      
      // Auto-login after successful signup
      if (data.status === 'success') {
        await login(email, password);
      } else {
        // Redirect to verification page if needed
        router.push('/verify-email');
      }
    } catch (error) {
      console.error('Signup error:', error);
      setError(error instanceof Error ? error.message : 'Signup failed');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Update Profile
  const updateProfile = async (updates: Partial<User>) => {
    try {
      setError(null);
      
      const data = await apiCall('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(updates),
      });
      
      setUser(prev => prev ? { ...prev, ...data } : null);
    } catch (error) {
      console.error('Profile update error:', error);
      setError(error instanceof Error ? error.message : 'Failed to update profile');
      throw error;
    }
  };

  // Send Verification Email
  const sendVerificationEmail = async () => {
    try {
      setError(null);
      
      await apiCall('/auth/send-verification-email', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Send verification email error:', error);
      setError(error instanceof Error ? error.message : 'Failed to send verification email');
      throw error;
    }
  };

  // Change Password
  const changePassword = async (currentPassword: string, newPassword: string) => {
    try {
      setError(null);
      
      await apiCall('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
    } catch (error) {
      console.error('Change password error:', error);
      setError(error instanceof Error ? error.message : 'Failed to change password');
      throw error;
    }
  };

  // Logout
  const logout = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        await apiCall('/auth/logout', { method: 'POST' });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state regardless of API call success
      localStorage.removeItem('access_token');
      sessionStorage.removeItem('auth_return_to');
      setUser(null);
      setError(null);
      router.push('/login');
    }
  };

  // Record login attempts for rate limiting
  const recordLoginAttempt = (success: boolean) => {
    const attempts = JSON.parse(localStorage.getItem('login_attempts') || '[]') as LoginAttempt[];
    const now = Date.now();
    
    // Keep only attempts from last hour
    const recentAttempts = attempts.filter(attempt => now - attempt.timestamp < 3600000);
    recentAttempts.push({ timestamp: now, success });
    
    localStorage.setItem('login_attempts', JSON.stringify(recentAttempts));
  };

  // Get recent failed login attempts
  const getRecentFailedAttempts = (): number => {
    const attempts = JSON.parse(localStorage.getItem('login_attempts') || '[]') as LoginAttempt[];
    const now = Date.now();
    
    return attempts.filter(
      attempt => !attempt.success && now - attempt.timestamp < 900000 // 15 minutes
    ).length;
  };

  // Handle OAuth callback
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const error = urlParams.get('error');
      const provider = urlParams.get('provider');

      console.log('OAuth callback detected:', { token: !!token, error, provider });

      if (token) {
        try {
          // Store token first
          localStorage.setItem('access_token', token);
          
          // Set loading state to prevent flickering
          setLoading(true);
          
          // Check auth status with the new token
          await checkAuthStatus();
          recordLoginAttempt(true);
          
          console.log('OAuth login successful, redirecting...');
          
          // Clear the URL parameters to prevent re-execution
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Redirect to intended page
          const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
          sessionStorage.removeItem('auth_return_to');
          
          // Use setTimeout to ensure state updates complete
          setTimeout(() => {
            router.push(returnTo);
          }, 100);
          
        } catch (error) {
          console.error('OAuth callback error:', error);
          localStorage.removeItem('access_token'); // Clean up on failure
          setError('Authentication failed');
          router.push('/login');
        } finally {
          setLoading(false);
        }
      } else if (error) {
        console.error('OAuth error:', error);
        recordLoginAttempt(false);
        setError(`${provider} authentication failed: ${error}`);
        
        // Clear URL and redirect to login
        window.history.replaceState({}, document.title, '/login');
        router.push('/login');
      }
    };

    // Check if this is an OAuth callback - be more specific
    const isOAuthCallback = (
      router.pathname.includes('/auth/success') || 
      router.pathname.includes('/auth/error')
    ) && router.isReady;

    if (isOAuthCallback && !oauthCallbackProcessed) {
      console.log('Processing OAuth callback...');
      setOauthCallbackProcessed(true);
      handleOAuthCallback();
    }
  }, [router.pathname, router.query, router.isReady, oauthCallbackProcessed]); // Add router.isReady and oauthCallbackProcessed

  // Auto-refresh token
  useEffect(() => {
    let refreshInterval: NodeJS.Timeout;

    if (user) {
      // Refresh user data every 5 minutes
      refreshInterval = setInterval(() => {
        refreshUser();
      }, 5 * 60 * 1000);
    }

    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, [user]);

  // Clear error function
  const clearError = () => {
    setError(null);
  };

  // Show loading screen for initial auth check
  if (loading && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    loginWithOAuth,
    logout,
    signup,
    refreshUser,
    updateProfile,
    sendVerificationEmail,
    changePassword,
    isAuthenticated: !!user,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Helper hook for protected routes
export const useRequireAuth = () => {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  return { user, loading };
};

// Helper hook for OAuth providers
export const useOAuthProviders = () => {
  const [providers, setProviders] = useState<Array<{
    provider: string;
    display_name: string;
    login_url: string;
  }>>([]);

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/providers`);
        const data = await response.json();
        setProviders(data.providers || []);
      } catch (error) {
        console.error('Failed to fetch OAuth providers:', error);
      }
    };

    fetchProviders();
  }, []);

  return providers;
};