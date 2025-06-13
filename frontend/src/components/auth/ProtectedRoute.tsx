import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2, Shield, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireVerification?: boolean;
  requireAdmin?: boolean;
  fallbackRoute?: string;
  loadingComponent?: React.ReactNode;
  unauthorizedComponent?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireVerification = false,
  requireAdmin = false,
  fallbackRoute = '/login',
  loadingComponent,
  unauthorizedComponent
}) => {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    if (!loading) {
      // Check authentication
      if (!isAuthenticated) {
        router.push(fallbackRoute);
        return;
      }

      // Check verification requirement
      if (requireVerification && user && !user.is_verified) {
        setIsAuthorized(false);
        return;
      }

      // Check admin requirement (you'd need to add admin field to user model)
      if (requireAdmin && user && !(user as any).is_admin) {
        setIsAuthorized(false);
        return;
      }

      setIsAuthorized(true);
    }
  }, [user, loading, isAuthenticated, requireVerification, requireAdmin, router, fallbackRoute]);

  // Show loading component
  if (loading || isAuthorized === null) {
    if (loadingComponent) {
      return <>{loadingComponent}</>;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (!isAuthorized) {
    if (unauthorizedComponent) {
      return <>{unauthorizedComponent}</>;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <CardTitle className="text-xl text-red-600">Access Denied</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            {requireVerification && user && !user.is_verified && (
              <div className="space-y-2">
                <AlertCircle className="w-6 h-6 text-yellow-500 mx-auto" />
                <p className="text-gray-600 dark:text-gray-400">
                  Please verify your email address to access this page.
                </p>
                <Button 
                  onClick={() => router.push('/verify-email')}
                  className="w-full"
                >
                  Verify Email
                </Button>
              </div>
            )}
            
            {requireAdmin && (
              <div className="space-y-2">
                <p className="text-gray-600 dark:text-gray-400">
                  You need administrator privileges to access this page.
                </p>
                <Button 
                  onClick={() => router.push('/dashboard')}
                  variant="outline"
                  className="w-full"
                >
                  Return to Dashboard
                </Button>
              </div>
            )}
            
            {!requireVerification && !requireAdmin && (
              <div className="space-y-2">
                <p className="text-gray-600 dark:text-gray-400">
                  You don't have permission to access this page.
                </p>
                <Button 
                  onClick={() => router.push('/dashboard')}
                  variant="outline"
                  className="w-full"
                >
                  Return to Dashboard
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // User is authorized, render children
  return <>{children}</>;
};

export default ProtectedRoute;

// Higher-order component for easier usage
export const withAuth = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) => {
  const AuthenticatedComponent = (props: P) => (
    <ProtectedRoute {...options}>
      <WrappedComponent {...props} />
    </ProtectedRoute>
  );

  AuthenticatedComponent.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name})`;
  
  return AuthenticatedComponent;
};

// Hook for checking specific permissions
export const usePermissions = () => {
  const { user, isAuthenticated } = useAuth();

  const hasPermission = (permission: string) => {
    if (!isAuthenticated || !user) return false;
    
    // Add your permission logic here
    // For example, check user roles, subscriptions, etc.
    const permissions = (user as any).permissions || [];
    return permissions.includes(permission);
  };

  const isVerified = isAuthenticated && user?.is_verified;
  const isAdmin = isAuthenticated && (user as any).is_admin;

  return {
    hasPermission,
    isVerified,
    isAdmin,
    canAccessPremiumFeatures: hasPermission('premium') || isAdmin,
    canManageUsers: hasPermission('manage_users') || isAdmin,
    canViewAnalytics: hasPermission('view_analytics') || isAdmin
  };
};