import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  Home,
  BarChart3,
  Settings,
  User,
  Bell,
  Search,
  Menu,
  X,
  Zap,
  DollarSign,
  TrendingUp,
  HelpCircle,
  LogOut,
  Sun,
  Moon,
  ChevronDown,
  Globe,
  Shield,
  CreditCard,
  Mail,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  showSidebar?: boolean;
}

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  submenu?: NavigationItem[];
}

const Layout: React.FC<LayoutProps> = ({ 
  children, 
  title, 
  showSidebar = true 
}) => {
  const router = useRouter();
  
  // Auto-generate title based on route if not provided
  const pageTitle = title || (() => {
    switch (router.pathname) {
      case '/dashboard': return 'Dashboard';
      case '/analytics': return 'Analytics';
      case '/gpus': return 'GPU Management';
      case '/earnings': return 'Earnings';
      case '/market': return 'Market';
      case '/settings': return 'Settings';
      default: return 'GPU Yield';
    }
  })();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState(3);
  const [searchQuery, setSearchQuery] = useState('');

  // Navigation items
  const navigation: NavigationItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: Home },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { 
      name: 'GPU Management', 
      href: '/gpus', 
      icon: Zap,
      submenu: [
        { name: 'All GPUs', href: '/gpus', icon: Zap },
        { name: 'Add GPU', href: '/gpus/add', icon: Zap },
        { name: 'Performance', href: '/gpus/performance', icon: Activity },
      ]
    },
    { name: 'Earnings', href: '/earnings', icon: DollarSign, badge: 'New' },
    { name: 'Market', href: '/market', icon: TrendingUp },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const userMenuItems = [
    { name: 'Profile', href: '/profile', icon: User },
    { name: 'Billing', href: '/billing', icon: CreditCard },
    { name: 'Security', href: '/security', icon: Shield },
    { name: 'Support', href: '/support', icon: HelpCircle },
  ];

  // Mock user data
  const user = {
    name: 'John Doe',
    email: 'john@example.com',
    avatar: '/api/placeholder/32/32',
    plan: 'Pro',
    earnings: '$1,247.82'
  };

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [router.asPath]);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setUserMenuOpen(false);
    if (userMenuOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [userMenuOpen]);

  const isActiveRoute = (href: string) => {
    return router.asPath === href || router.asPath.startsWith(href + '/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Sidebar */}
      {showSidebar && (
        <>
          {/* Mobile sidebar backdrop */}
          {sidebarOpen && (
            <div 
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Sidebar */}
          <div className={`
            fixed top-0 left-0 z-50 h-full w-64 bg-black/60 backdrop-blur-xl border-r border-white/10
            transform transition-transform duration-300 ease-in-out lg:translate-x-0
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}>
            {/* Sidebar header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <Link href="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">GPU Yield</span>
              </Link>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* User info */}
            <div className="p-4 border-b border-white/10">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{user.name}</p>
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-xs">
                      {user.plan}
                    </Badge>
                    <span className="text-green-400 text-sm font-mono">{user.earnings}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="p-4 space-y-2 flex-1 overflow-y-auto custom-scrollbar">
              {navigation.map((item) => (
                <div key={item.name}>
                  <Link href={item.href}>
                    <div className={`
                      flex items-center justify-between px-3 py-2 rounded-lg transition-all
                      ${isActiveRoute(item.href) 
                        ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30 text-white' 
                        : 'text-gray-300 hover:text-white hover:bg-white/10'
                      }
                    `}>
                      <div className="flex items-center space-x-3">
                        <item.icon className="w-5 h-5" />
                        <span className="font-medium">{item.name}</span>
                      </div>
                      {item.badge && (
                        <Badge className="bg-red-500/10 text-red-400 border-red-500/20 text-xs">
                          {item.badge}
                        </Badge>
                      )}
                    </div>
                  </Link>
                  
                  {/* Submenu */}
                  {item.submenu && isActiveRoute(item.href) && (
                    <div className="ml-8 mt-2 space-y-1">
                      {item.submenu.map((subItem) => (
                        <Link key={subItem.name} href={subItem.href}>
                          <div className={`
                            flex items-center space-x-2 px-3 py-1 rounded-lg text-sm transition-all
                            ${isActiveRoute(subItem.href)
                              ? 'text-blue-400 bg-blue-500/10'
                              : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }
                          `}>
                            <div className="w-1 h-1 bg-current rounded-full" />
                            <span>{subItem.name}</span>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </nav>

            {/* Sidebar footer */}
            <div className="p-4 border-t border-white/10">
              <Card className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/20 p-3">
                <div className="text-center">
                  <p className="text-white text-sm font-medium mb-1">Upgrade to Pro</p>
                  <p className="text-gray-400 text-xs mb-3">Get advanced analytics and alerts</p>
                  <Button
                    size="sm"
                    className="bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs"
                  >
                    Upgrade Now
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}

      {/* Main content */}
      <div className={`${showSidebar ? 'lg:ml-64' : ''} min-h-screen`}>
        {/* Top bar */}
        <header className="bg-black/20 backdrop-blur-xl border-b border-white/10 sticky top-0 z-30">
          <div className="flex items-center justify-between px-4 py-3">
            {/* Left side */}
            <div className="flex items-center space-x-4">
              {showSidebar && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden text-gray-400 hover:text-white"
                >
                  <Menu className="w-5 h-5" />
                </Button>
              )}
              
              <h1 className="text-xl font-semibold text-white">{pageTitle}</h1>
            </div>

            {/* Center - Search */}
            <div className="hidden md:flex flex-1 max-w-lg mx-8">
              <div className="relative w-full">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search GPUs, earnings, or settings..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Right side */}
            <div className="flex items-center space-x-4">
              {/* Theme toggle */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDarkMode(!darkMode)}
                className="text-gray-400 hover:text-white"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>

              {/* Notifications */}
              <Button
                variant="ghost"
                size="sm"
                className="relative text-gray-400 hover:text-white"
              >
                <Bell className="w-5 h-5" />
                {notifications > 0 && (
                  <Badge className="absolute -top-1 -right-1 w-5 h-5 p-0 bg-red-500 text-white border-0 text-xs flex items-center justify-center">
                    {notifications}
                  </Badge>
                )}
              </Button>

              {/* User menu */}
              <div className="relative">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setUserMenuOpen(!userMenuOpen);
                  }}
                  className="flex items-center space-x-2 text-gray-400 hover:text-white"
                >
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <ChevronDown className="w-4 h-4" />
                </Button>

                {/* User menu dropdown */}
                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl py-2 z-50">
                    {/* User info */}
                    <div className="px-4 py-3 border-b border-white/10">
                      <p className="text-white font-medium">{user.name}</p>
                      <p className="text-gray-400 text-sm">{user.email}</p>
                    </div>

                    {/* Menu items */}
                    <div className="py-2">
                      {userMenuItems.map((item) => (
                        <Link key={item.name} href={item.href}>
                          <div className="flex items-center space-x-3 px-4 py-2 text-gray-300 hover:text-white hover:bg-white/10 transition-colors">
                            <item.icon className="w-4 h-4" />
                            <span>{item.name}</span>
                          </div>
                        </Link>
                      ))}
                    </div>

                    {/* Logout */}
                    <div className="border-t border-white/10 pt-2">
                      <button className="flex items-center space-x-3 px-4 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors w-full">
                        <LogOut className="w-4 h-4" />
                        <span>Sign out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;