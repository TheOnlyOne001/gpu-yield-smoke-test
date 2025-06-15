import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';

// Types
interface User {
  id: string;
  email: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  auth_provider: 'email' | 'google' | 'twitter' | 'discord';
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  loginWithOAuth: (provider: 'google' | 'twitter' | 'discord') => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Helper to check if a route is public
const isPublicRoute = (pathname: string): boolean => {
  const publicRoutes = [
    '/',
    '/login',
    '/signup',
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

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [oauthCallbackProcessed, setOauthCallbackProcessed] = useState(false);

  const isAuthenticated = !!user;

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // API call helper with authentication
  const apiCall = async (endpoint: string, config: RequestInit = {}) => {
    const token = localStorage.getItem('access_token');
    
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...config.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...config,
      headers,
    });
    
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

  // OAuth login
  const loginWithOAuth = async (provider: 'google' | 'twitter' | 'discord') => {
    try {
      setError(null);
      
      // Store return URL
      const returnTo = router.pathname !== '/login' && router.pathname !== '/signup' 
        ? router.asPath 
        : '/dashboard';
      sessionStorage.setItem('auth_return_to', returnTo);
      
      // Track provider preference
      localStorage.setItem('lastAuthProvider', provider);
      
      // Redirect to OAuth provider
      window.location.href = `${API_BASE_URL}/auth/${provider}/login`;
    } catch (error) {
      console.error(`${provider} login error:`, error);
      setError(`Failed to initiate ${provider} login`);
      throw error;
    }
  };

  // Logout
  const logout = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Call logout endpoint
      await apiCall('/auth/logout', { method: 'POST' });
      
      // Clear local state
      localStorage.removeItem('access_token');
      localStorage.removeItem('lastAuthProvider');
      sessionStorage.removeItem('auth_return_to');
      setUser(null);
      
      // Redirect to login
      router.push('/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Even if logout fails, clear local state
      localStorage.removeItem('access_token');
      setUser(null);
      router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  // Update user profile
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

  // Refresh user data
  const refreshUser = async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const data = await apiCall('/auth/user');
      setUser(data);
    } catch (error) {
      console.error('Failed to refresh user:', error);
      handleTokenExpiry();
    } finally {
      setLoading(false);
    }
  };

  // Check authentication status on mount
  useEffect(() => {
    refreshUser();
  }, []);

  // Handle OAuth callback
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const { token, error, provider, user: userDataEncoded } = router.query;

      if (token) {
        try {
          // Store token
          localStorage.setItem('access_token', token as string);
          
          // Decode user data if provided
          if (userDataEncoded) {
            try {
              const userData = JSON.parse(decodeURIComponent(userDataEncoded as string));
              setUser(userData);
            } catch (e) {
              console.error('Failed to parse user data:', e);
            }
          }
          
          // Fetch full user data
          await refreshUser();
          
          // Clear URL parameters
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Get return URL or default to dashboard
          const returnTo = sessionStorage.getItem('auth_return_to') || '/dashboard';
          sessionStorage.removeItem('auth_return_to');
          
          // Redirect after a small delay to ensure state updates
          setTimeout(() => {
            router.push(returnTo);
          }, 100);
          
        } catch (error) {
          console.error('OAuth callback error:', error);
          localStorage.removeItem('access_token');
          setError('Authentication failed');
          router.push('/login');
        }
      } else if (error) {
        console.error('OAuth error:', error);
        setError(`${provider} authentication failed: ${error}`);
        
        // Clear URL and redirect to login
        window.history.replaceState({}, document.title, '/login');
        router.push('/login');
      }
    };

    // Check if this is an OAuth callback
    const isOAuthCallback = (
      router.pathname.includes('/auth/success') || 
      router.pathname.includes('/auth/error')
    ) && router.isReady;

    if (isOAuthCallback && !oauthCallbackProcessed) {
      setOauthCallbackProcessed(true);
      handleOAuthCallback();
    }
  }, [router.pathname, router.query, router.isReady, oauthCallbackProcessed]);

  // Handle route protection
  useEffect(() => {
    if (!loading) {
      const isPublic = isPublicRoute(router.pathname);
      const isAuthRoute = ['/login', '/signup'].includes(router.pathname);

      if (!isPublic && !user) {
        // Protected route without authentication
        router.push('/login');
      } else if (isAuthRoute && user) {
        // Auth route with authenticated user
        router.push('/dashboard');
      }
    }
  }, [router.pathname, user, loading]);

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!user) return;

    const refreshInterval = setInterval(() => {
      refreshUser();
    }, 15 * 60 * 1000); // Refresh every 15 minutes

    return () => clearInterval(refreshInterval);
  }, [user]);

  const value = {
    user,
    loading,
    error,
    isAuthenticated,
    loginWithOAuth,
    logout,
    updateProfile,
    refreshUser,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};