import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useAuth } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Layout from '@/components/layout/layout';
import {
  Users,
  Shield,
  TrendingUp,
  Activity,
  Eye,
  Download,
  RefreshCw,
  Search,
  Filter,
  MoreHorizontal,
  UserCheck,
  UserX,
  Mail,
  Calendar,
  Chrome,
  Twitter,
  MessageCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  Trash2,
  Edit,
  ExternalLink
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UserStats {
  total_users: number;
  verified_users: number;
  verification_rate: number;
  recent_signups: number;
  active_users: number;
  activity_rate: number;
  auth_providers: Record<string, number>;
  daily_signups?: Record<string, Record<string, number>>;
}

interface User {
  id: number;
  email: string;
  username?: string;
  full_name?: string;
  auth_provider: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  avatar_url?: string;
}

interface OAuthStats {
  provider_statistics: Array<{
    auth_provider: string;
    total_users: number;
    verified_users: number;
    active_users: number;
    verification_rate: number;
    activity_rate: number;
    first_signup: string;
    latest_signup: string;
  }>;
  adoption_trends: Record<string, Record<string, number>>;
  summary: {
    total_oauth_users: number;
    email_users: number;
    most_popular_oauth: string;
  };
}

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [oauthStats, setOauthStats] = useState<OAuthStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterProvider, setFilterProvider] = useState('');
  const [filterVerified, setFilterVerified] = useState('');
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      
      // Fetch user stats
      const statsResponse = await fetch(`${API_BASE_URL}/admin/users/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (statsResponse.ok) {
        const stats = await statsResponse.json();
        setUserStats(stats);
      }

      // Fetch OAuth stats
      const oauthResponse = await fetch(`${API_BASE_URL}/admin/oauth/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (oauthResponse.ok) {
        const oauth = await oauthResponse.json();
        setOauthStats(oauth);
      }

      // Fetch recent users
      const usersResponse = await fetch(`${API_BASE_URL}/admin/users/search?q=&limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users);
      }

    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({
        q: searchQuery,
        limit: '50'
      });
      
      if (filterProvider) params.append('auth_provider', filterProvider);
      if (filterVerified) params.append('is_verified', filterVerified);

      const response = await fetch(`${API_BASE_URL}/admin/users/search?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
      }
    } catch (error) {
      console.error('Failed to search users:', error);
    }
  };

  const handleVerifyUser = async (userId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/verify`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        setUsers(users.map(u => u.id === userId ? { ...u, is_verified: true } : u));
      }
    } catch (error) {
      console.error('Failed to verify user:', error);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        setUsers(users.filter(u => u.id !== userId));
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const handleExportUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/admin/users/export?format=csv`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gpu_yield_users_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to export users:', error);
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'google': return <Chrome className="w-4 h-4" />;
      case 'twitter': return <Twitter className="w-4 h-4" />;
      case 'discord': return <MessageCircle className="w-4 h-4" />;
      default: return <Mail className="w-4 h-4" />;
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'google': return 'bg-blue-100 text-blue-800';
      case 'twitter': return 'bg-sky-100 text-sky-800';
      case 'discord': return 'bg-indigo-100 text-indigo-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <ProtectedRoute requireAdmin>
        <Layout title="Admin Dashboard">
          <div className="flex items-center justify-center min-h-96">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-600">Loading dashboard data...</p>
            </div>
          </div>
        </Layout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requireAdmin>
      <Layout title="Admin Dashboard">
        <Head>
          <title>Admin Dashboard - GPU Yield</title>
          <meta name="description" content="Admin dashboard for managing GPU Yield users and OAuth authentication" />
        </Head>

        <div className="max-w-7xl mx-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage users, OAuth providers, and system analytics
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Button onClick={handleExportUsers} variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Export Users
              </Button>
              <Button onClick={fetchDashboardData}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>

          {/* Stats Cards */}
          {userStats && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{userStats.total_users.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">
                    {userStats.recent_signups} new this month
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Verified Users</CardTitle>
                  <UserCheck className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{userStats.verified_users.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">
                    {userStats.verification_rate}% verification rate
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{userStats.active_users.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">
                    {userStats.activity_rate}% activity rate
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">OAuth Users</CardTitle>
                  <Shield className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {oauthStats?.summary.total_oauth_users.toLocaleString() || '0'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Most popular: {oauthStats?.summary.most_popular_oauth || 'None'}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          <Tabs defaultValue="users" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="users">User Management</TabsTrigger>
              <TabsTrigger value="oauth">OAuth Analytics</TabsTrigger>
              <TabsTrigger value="providers">Auth Providers</TabsTrigger>
            </TabsList>

            {/* User Management Tab */}
            <TabsContent value="users" className="space-y-4">
              {/* Search and Filters */}
              <Card>
                <CardHeader>
                  <CardTitle>Search Users</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Search by email, username, or name..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <select
                      value={filterProvider}
                      onChange={(e) => setFilterProvider(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">All Providers</option>
                      <option value="email">Email</option>
                      <option value="google">Google</option>
                      <option value="twitter">Twitter</option>
                      <option value="discord">Discord</option>
                    </select>
                    <select
                      value={filterVerified}
                      onChange={(e) => setFilterVerified(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">All Users</option>
                      <option value="true">Verified</option>
                      <option value="false">Unverified</option>
                    </select>
                    <Button onClick={handleSearchUsers}>
                      <Search className="w-4 h-4 mr-2" />
                      Search
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Users Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Users ({users.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            User
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Auth Provider
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Joined
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Last Login
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {users.map((user) => (
                          <tr key={user.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                {user.avatar_url ? (
                                  <img 
                                    className="h-8 w-8 rounded-full" 
                                    src={user.avatar_url} 
                                    alt={user.username || user.email}
                                  />
                                ) : (
                                  <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
                                    <Users className="h-4 w-4 text-gray-600" />
                                  </div>
                                )}
                                <div className="ml-3">
                                  <div className="text-sm font-medium text-gray-900">
                                    {user.full_name || user.username || 'No name'}
                                  </div>
                                  <div className="text-sm text-gray-500">{user.email}</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <Badge className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getProviderColor(user.auth_provider)}`}>
                                {getProviderIcon(user.auth_provider)}
                                <span className="ml-1">{user.auth_provider}</span>
                              </Badge>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center space-x-2">
                                {user.is_verified ? (
                                  <Badge variant="default" className="bg-green-100 text-green-800">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Verified
                                  </Badge>
                                ) : (
                                  <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                    Unverified
                                  </Badge>
                                )}
                                {!user.is_active && (
                                  <Badge variant="destructive">Inactive</Badge>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDate(user.created_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {user.last_login ? formatDate(user.last_login) : 'Never'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex items-center space-x-2">
                                {!user.is_verified && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleVerifyUser(user.id)}
                                  >
                                    <UserCheck className="w-3 h-3 mr-1" />
                                    Verify
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => window.open(`/admin/users/${user.id}`, '_blank')}
                                >
                                  <Eye className="w-3 h-3 mr-1" />
                                  View
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="text-red-600 hover:text-red-700"
                                  onClick={() => handleDeleteUser(user.id)}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* OAuth Analytics Tab */}
            <TabsContent value="oauth" className="space-y-4">
              {oauthStats && (
                <>
                  {/* Provider Statistics */}
                  <Card>
                    <CardHeader>
                      <CardTitle>OAuth Provider Statistics</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {oauthStats.provider_statistics.map((provider) => (
                          <div key={provider.auth_provider} className="flex items-center justify-between p-4 border rounded-lg">
                            <div className="flex items-center space-x-3">
                              {getProviderIcon(provider.auth_provider)}
                              <div>
                                <h3 className="font-medium">{provider.auth_provider.charAt(0).toUpperCase() + provider.auth_provider.slice(1)}</h3>
                                <p className="text-sm text-gray-500">
                                  {provider.total_users} users • {provider.verification_rate}% verified
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium">{provider.active_users} active</div>
                              <div className="text-xs text-gray-500">{provider.activity_rate}% activity rate</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Total OAuth Users</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{oauthStats.summary.total_oauth_users}</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Email Users</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{oauthStats.summary.email_users}</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Most Popular OAuth</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold capitalize">{oauthStats.summary.most_popular_oauth}</div>
                      </CardContent>
                    </Card>
                  </div>
                </>
              )}
            </TabsContent>

            {/* Auth Providers Tab */}
            <TabsContent value="providers" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Authentication Providers</CardTitle>
                  <p className="text-sm text-gray-600">Manage OAuth provider configurations</p>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { name: 'Google', provider: 'google', icon: Chrome, status: 'active' },
                      { name: 'Twitter', provider: 'twitter', icon: Twitter, status: 'active' },
                      { name: 'Discord', provider: 'discord', icon: MessageCircle, status: 'active' }
                    ].map((provider) => (
                      <div key={provider.provider} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <provider.icon className="w-8 h-8" />
                          <div>
                            <h3 className="font-medium">{provider.name}</h3>
                            <p className="text-sm text-gray-500">OAuth 2.0</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={provider.status === 'active' ? 'default' : 'secondary'}>
                            {provider.status}
                          </Badge>
                          <Button size="sm" variant="outline">
                            <Edit className="w-3 h-3 mr-1" />
                            Configure
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </Layout>
    </ProtectedRoute>
  );
};

export default AdminDashboard;