import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useAuth } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Layout from '@/components/layout/layout';
import {
  User,
  Mail,
  Shield,
  Key,
  Link as LinkIcon,
  Unlink,
  Chrome,
  Twitter,
  MessageCircle,
  Calendar,
  Check,
  X,
  AlertCircle,
  Loader2,
  Settings,
  Eye,
  EyeOff,
  Save
} from 'lucide-react';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface LinkedAccount {
  provider: string;
  provider_id: string;
  linked_at: string;
  is_primary: boolean;
}

const UserProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const [linkedAccounts, setLinkedAccounts] = useState<LinkedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Profile editing
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    username: user?.username || '',
    full_name: user?.full_name || '',
    email: user?.email || ''
  });
  
  // Password change
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [passwordLoading, setPasswordLoading] = useState(false);

  // OAuth providers configuration
  const oauthProviders = [
    {
      name: 'Google',
      provider: 'google',
      icon: Chrome,
      color: 'bg-blue-600',
      textColor: 'text-white'
    },
    {
      name: 'Twitter',
      provider: 'twitter',
      icon: Twitter,
      color: 'bg-sky-500',
      textColor: 'text-white'
    },
    {
      name: 'Discord',
      provider: 'discord',
      icon: MessageCircle,
      color: 'bg-indigo-600',
      textColor: 'text-white'
    }
  ];

  useEffect(() => {
    fetchLinkedAccounts();
  }, []);

  const fetchLinkedAccounts = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/auth/linked-accounts`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setLinkedAccounts(data.accounts || []);
      }
    } catch (error) {
      console.error('Failed to fetch linked accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkAccount = async (provider: string) => {
    try {
      setError('');
      // Redirect to OAuth provider
      window.location.href = `${API_BASE_URL}/auth/${provider}/login?link=true`;
    } catch (error) {
      setError(`Failed to link ${provider} account`);
    }
  };

  const handleUnlinkAccount = async (provider: string) => {
    try {
      setError('');
      setSuccess('');
      
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/auth/unlink/${provider}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setSuccess(`${provider} account unlinked successfully`);
        fetchLinkedAccounts();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || `Failed to unlink ${provider} account`);
      }
    } catch (error) {
      setError(`Failed to unlink ${provider} account`);
    }
  };

  const handleProfileSave = async () => {
    try {
      setError('');
      setSuccess('');
      
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editForm),
      });

      if (response.ok) {
        setSuccess('Profile updated successfully');
        setIsEditing(false);
        // Refresh user data
        window.location.reload();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update profile');
      }
    } catch (error) {
      setError('Failed to update profile');
    }
  };

  const handlePasswordChange = async () => {
    try {
      setError('');
      setSuccess('');
      setPasswordLoading(true);

      if (passwordForm.new_password !== passwordForm.confirm_password) {
        setError('New passwords do not match');
        return;
      }

      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      });

      if (response.ok) {
        setSuccess('Password changed successfully');
        setPasswordForm({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to change password');
      }
    } catch (error) {
      setError('Failed to change password');
    } finally {
      setPasswordLoading(false);
    }
  };

  const isAccountLinked = (provider: string) => {
    return linkedAccounts.some(account => account.provider === provider);
  };

  const getProviderInfo = (provider: string) => {
    return oauthProviders.find(p => p.provider === provider);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <ProtectedRoute>
      <Layout title="Profile">
        <Head>
          <title>Profile - GPU Yield</title>
          <meta name="description" content="Manage your GPU Yield profile and account settings" />
        </Head>

        <div className="max-w-4xl mx-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Profile</h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage your account settings and linked social accounts
              </p>
            </div>
            <div className="flex items-center space-x-2">
              {user?.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt="Profile"
                  className="w-12 h-12 rounded-full border-2 border-gray-200 dark:border-gray-700"
                />
              )}
            </div>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md flex items-center">
              <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
              <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
            </div>
          )}

          {success && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md flex items-center">
              <Check className="w-5 h-5 text-green-500 mr-2" />
              <span className="text-sm text-green-700 dark:text-green-400">{success}</span>
            </div>
          )}

          <Tabs defaultValue="profile" className="space-y-6">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
              <TabsTrigger value="accounts">Linked Accounts</TabsTrigger>
              <TabsTrigger value="privacy">Privacy</TabsTrigger>
            </TabsList>

            {/* Profile Tab */}
            <TabsContent value="profile">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center">
                      <User className="w-5 h-5 mr-2" />
                      Profile Information
                    </CardTitle>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Update your personal information and preferences
                    </p>
                  </div>
                  <Button
                    variant={isEditing ? "outline" : "default"}
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    {isEditing ? (
                      <>
                        <X className="w-4 h-4 mr-2" />
                        Cancel
                      </>
                    ) : (
                      <>
                        <Settings className="w-4 h-4 mr-2" />
                        Edit
                      </>
                    )}
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Email
                      </label>
                      {isEditing ? (
                        <input
                          type="email"
                          value={editForm.email}
                          onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                      ) : (
                        <div className="flex items-center">
                          <Mail className="w-4 h-4 mr-2 text-gray-400" />
                          <span>{user?.email}</span>
                          {user?.is_verified ? (
                            <Check className="w-4 h-4 ml-2 text-green-500" />
                          ) : (
                            <AlertCircle className="w-4 h-4 ml-2 text-yellow-500" />
                          )}
                        </div>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Username
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.username}
                          onChange={(e) => setEditForm({...editForm, username: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                      ) : (
                        <span>{user?.username || 'Not set'}</span>
                      )}
                    </div>

                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Full Name
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.full_name}
                          onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                      ) : (
                        <span>{user?.full_name || 'Not set'}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Member since {user?.created_at ? formatDate(user.created_at) : 'Unknown'}
                    </span>
                  </div>

                  {isEditing && (
                    <div className="flex justify-end space-x-2 pt-4">
                      <Button onClick={handleProfileSave}>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Security Tab */}
            <TabsContent value="security">
              <div className="space-y-6">
                {/* Authentication Method */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center">
                      <Shield className="w-5 h-5 mr-2" />
                      Authentication Method
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Primary Authentication</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {user?.auth_provider === 'email' ? 'Email & Password' : `${user?.auth_provider} OAuth`}
                        </p>
                      </div>
                      <Badge variant={user?.auth_provider === 'email' ? 'default' : 'secondary'}>
                        {user?.auth_provider}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Change Password (only for email users) */}
                {user?.auth_provider === 'email' && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <Key className="w-5 h-5 mr-2" />
                        Change Password
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Current Password
                        </label>
                        <div className="relative">
                          <input
                            type={showPasswords.current ? 'text' : 'password'}
                            value={passwordForm.current_password}
                            onChange={(e) => setPasswordForm({...passwordForm, current_password: e.target.value})}
                            className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPasswords({...showPasswords, current: !showPasswords.current})}
                            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                          >
                            {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          New Password
                        </label>
                        <div className="relative">
                          <input
                            type={showPasswords.new ? 'text' : 'password'}
                            value={passwordForm.new_password}
                            onChange={(e) => setPasswordForm({...passwordForm, new_password: e.target.value})}
                            className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPasswords({...showPasswords, new: !showPasswords.new})}
                            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                          >
                            {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Confirm New Password
                        </label>
                        <div className="relative">
                          <input
                            type={showPasswords.confirm ? 'text' : 'password'}
                            value={passwordForm.confirm_password}
                            onChange={(e) => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
                            className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPasswords({...showPasswords, confirm: !showPasswords.confirm})}
                            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                          >
                            {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      <Button 
                        onClick={handlePasswordChange}
                        disabled={passwordLoading || !passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password}
                      >
                        {passwordLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Changing...
                          </>
                        ) : (
                          'Change Password'
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>

            {/* Linked Accounts Tab */}
            <TabsContent value="accounts">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <LinkIcon className="w-5 h-5 mr-2" />
                    Linked Accounts
                  </CardTitle>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Connect your social media accounts for easier sign-in
                  </p>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-4">
                      <Loader2 className="w-6 h-6 animate-spin" />
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {oauthProviders.map((provider) => {
                        const isLinked = isAccountLinked(provider.provider);
                        const Icon = provider.icon;
                        
                        return (
                          <div key={provider.provider} className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <div className={`p-2 rounded-full ${provider.color}`}>
                                <Icon className={`w-5 h-5 ${provider.textColor}`} />
                              </div>
                              <div>
                                <h3 className="font-medium">{provider.name}</h3>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  {isLinked ? 'Connected' : 'Not connected'}
                                </p>
                              </div>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              {isLinked ? (
                                <>
                                  <Badge variant="secondary" className="bg-green-100 text-green-800">
                                    <Check className="w-3 h-3 mr-1" />
                                    Connected
                                  </Badge>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleUnlinkAccount(provider.provider)}
                                    className="text-red-600 hover:text-red-700"
                                  >
                                    <Unlink className="w-4 h-4 mr-1" />
                                    Unlink
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleLinkAccount(provider.provider)}
                                >
                                  <LinkIcon className="w-4 h-4 mr-1" />
                                  Connect
                                </Button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Privacy Tab */}
            <TabsContent value="privacy">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="w-5 h-5 mr-2" />
                    Privacy Settings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium">Email Verification Status</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {user?.is_verified ? 'Your email is verified' : 'Your email needs verification'}
                      </p>
                    </div>
                    <Badge variant={user?.is_verified ? 'default' : 'destructive'}>
                      {user?.is_verified ? 'Verified' : 'Unverified'}
                    </Badge>
                  </div>

                  <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="font-medium mb-2">Account Actions</h3>
                    <div className="space-y-2">
                      <Button variant="outline" className="w-full justify-start text-red-600 hover:text-red-700">
                        Export Account Data
                      </Button>
                      <Button variant="outline" className="w-full justify-start text-red-600 hover:text-red-700">
                        Delete Account
                      </Button>
                    </div>
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

export default UserProfilePage;