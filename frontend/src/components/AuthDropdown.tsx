// Create file: frontend/src/components/AuthDropdown.tsx

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { 
  ChevronDown, 
  User, 
  UserPlus, 
  LogIn, 
  Sparkles, 
  Zap,
  ArrowUpRight,
  Star
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AuthDropdownProps {
  className?: string;
}

const AuthDropdown: React.FC<AuthDropdownProps> = ({ className = "" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown when pressing Escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>      {/* Enhanced Trigger Button */}
      <Button
        variant="outline"
        className={`
          group relative overflow-hidden
          border border-white/20
          text-white hover:text-white
          px-5 py-3 rounded-2xl
          transition-all duration-500 ease-out
          hover:border-white/40
          hover:shadow-2xl hover:shadow-blue-500/25
          ${isOpen ? 'border-white/40 shadow-2xl shadow-blue-500/25' : ''}
        `}
        style={{
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(16px) saturate(120%)',
          WebkitBackdropFilter: 'blur(16px) saturate(120%)'
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {/* Animated background layer */}
        <div 
          className="absolute inset-0 rounded-2xl transition-all duration-500"
          style={{
            background: isOpen 
              ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(147, 51, 234, 0.15), rgba(6, 182, 212, 0.15))'
              : 'linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(147, 51, 234, 0.05), rgba(6, 182, 212, 0.05))'
          }}
        />
        
        {/* Shine effect on hover */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
        </div>
        
        <div className="relative flex items-center gap-3">
          <div className="w-6 h-6 rounded-xl bg-gradient-to-br from-blue-400 via-purple-500 to-cyan-400 flex items-center justify-center shadow-lg">
            <User className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-sm">Account</span>
          <ChevronDown className={`w-4 h-4 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </Button>      {/* Enhanced Glassmorphism Dropdown */}
      {isOpen && (
        <>
          {/* Mobile backdrop with enhanced blur */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-md md:hidden z-40" 
            style={{ backdropFilter: 'blur(12px)' }}
            onClick={() => setIsOpen(false)} 
          />
          
          <div 
            className={`
              absolute right-0 mt-4 w-[340px]
              border border-white/30 rounded-3xl
              shadow-[0_32px_64px_rgba(0,0,0,0.4)]
              z-50 overflow-hidden
              animate-dropdown-enter
            `}
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              backdropFilter: 'blur(24px) saturate(150%)',
              WebkitBackdropFilter: 'blur(24px) saturate(150%)',
              boxShadow: `
                0 32px 64px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.1),
                0 0 0 1px rgba(255, 255, 255, 0.05)
              `
            }}
          >
              {/* Enhanced Header with Multiple Glass Layers */}
            <div 
              className="relative p-8 border-b border-white/20"
              style={{
                background: `
                  linear-gradient(135deg, 
                    rgba(30, 41, 59, 0.9) 0%, 
                    rgba(15, 23, 42, 0.95) 50%, 
                    rgba(30, 41, 59, 0.9) 100%
                  )
                `,
                backdropFilter: 'blur(20px) saturate(150%)',
                WebkitBackdropFilter: 'blur(20px) saturate(150%)'
              }}
            >
              {/* Primary glass layer */}
              <div 
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(147, 51, 234, 0.2), rgba(6, 182, 212, 0.15))',
                  mixBlendMode: 'overlay'
                }}
              />
              
              {/* Tertiary shine layer */}
              <div 
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, transparent 50%, rgba(255, 255, 255, 0.05) 100%)'
                }}
              />
              
              {/* Animated particles effect */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute top-4 right-6 w-1 h-1 bg-blue-400 rounded-full animate-pulse" />
                <div className="absolute top-8 right-12 w-0.5 h-0.5 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.5s' }} />
                <div className="absolute top-6 right-8 w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" style={{ animationDelay: '1s' }} />
              </div>
              
              <div className="relative flex items-center gap-5">
                <div className="relative">
                  <div className="w-14 h-14 rounded-3xl bg-gradient-to-br from-blue-500 via-purple-600 to-cyan-500 flex items-center justify-center shadow-2xl">
                    <Zap className="w-7 h-7 text-white" />
                  </div>
                  {/* Glow effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500 via-purple-600 to-cyan-500 rounded-3xl blur-lg opacity-50 -z-10" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-white text-xl tracking-tight">GPU Yield</h3>
                  <p className="text-sm text-white/70 font-medium mt-1">Transform your GPU into profit</p>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-500/30 to-orange-500/30 rounded-xl border border-amber-400/30 backdrop-blur-sm">
                  <Star className="w-3.5 h-3.5 text-amber-300" fill="currentColor" />
                  <span className="text-sm font-bold text-amber-200">4.9</span>
                </div>
              </div>
            </div>
              <div className="p-4 space-y-3">
              {/* Enhanced Sign In Card */}
              <Link href="/login" onClick={() => setIsOpen(false)}>
                <div 
                  className={`
                    relative group p-5 rounded-2xl cursor-pointer
                    border border-white/20
                    transition-all duration-500 ease-out
                    hover:border-white/30
                    hover:shadow-2xl hover:shadow-blue-500/20
                    ${hoveredItem === 'signin' ? 'scale-[1.02] shadow-2xl shadow-blue-500/20' : ''}
                  `}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    backdropFilter: 'blur(16px) saturate(120%)',
                    WebkitBackdropFilter: 'blur(16px) saturate(120%)'
                  }}
                  onMouseEnter={() => setHoveredItem('signin')}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  {/* Layered background effects */}
                  <div 
                    className="absolute inset-0 rounded-2xl transition-all duration-500"
                    style={{
                      background: hoveredItem === 'signin' 
                        ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(6, 182, 212, 0.15))'
                        : 'linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(6, 182, 212, 0.05))'
                    }}
                  />
                  <div 
                    className="absolute inset-0 rounded-2xl transition-all duration-500"
                    style={{
                      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, transparent 50%, rgba(255, 255, 255, 0.02) 100%)',
                      opacity: hoveredItem === 'signin' ? 1 : 0
                    }}
                  />
                  
                  <div className="relative flex items-center gap-4">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500/30 to-cyan-500/30 border border-blue-400/40 flex items-center justify-center group-hover:from-blue-500/50 group-hover:to-cyan-500/50 group-hover:border-blue-400/60 transition-all duration-500 backdrop-blur-sm">
                        <LogIn className="w-5 h-5 text-blue-300" />
                      </div>
                      {/* Icon glow */}
                      <div className="absolute inset-0 bg-blue-400/20 rounded-2xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="font-bold text-white text-base">Sign In</h4>
                        <div className="px-2.5 py-1 bg-blue-500/25 border border-blue-400/30 rounded-lg backdrop-blur-sm">
                          <span className="text-xs font-semibold text-blue-200">Secure</span>
                        </div>
                      </div>
                      <p className="text-sm text-white/60 font-medium">Access your earnings dashboard</p>
                    </div>
                    <ArrowUpRight className="w-5 h-5 text-white/40 group-hover:text-blue-300 group-hover:translate-x-1 group-hover:-translate-y-1 transition-all duration-300" />
                  </div>
                </div>
              </Link>              {/* Enhanced Sign Up Card */}
              <Link href="/signup" onClick={() => setIsOpen(false)}>
                <div 
                  className={`
                    relative group p-5 rounded-2xl cursor-pointer
                    border border-white/20
                    transition-all duration-500 ease-out
                    hover:border-white/30
                    hover:shadow-2xl hover:shadow-purple-500/20
                    ${hoveredItem === 'signup' ? 'scale-[1.02] shadow-2xl shadow-purple-500/20' : ''}
                  `}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    backdropFilter: 'blur(16px) saturate(120%)',
                    WebkitBackdropFilter: 'blur(16px) saturate(120%)'
                  }}
                  onMouseEnter={() => setHoveredItem('signup')}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  {/* Layered background effects */}
                  <div 
                    className="absolute inset-0 rounded-2xl transition-all duration-500"
                    style={{
                      background: hoveredItem === 'signup' 
                        ? 'linear-gradient(135deg, rgba(147, 51, 234, 0.15), rgba(236, 72, 153, 0.15), rgba(6, 182, 212, 0.15))'
                        : 'linear-gradient(135deg, rgba(147, 51, 234, 0.05), rgba(236, 72, 153, 0.05), rgba(6, 182, 212, 0.05))'
                    }}
                  />
                  <div 
                    className="absolute inset-0 rounded-2xl transition-all duration-500"
                    style={{
                      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, transparent 50%, rgba(255, 255, 255, 0.02) 100%)',
                      opacity: hoveredItem === 'signup' ? 1 : 0
                    }}
                  />
                  
                  <div className="relative flex items-center gap-4">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500/30 via-pink-500/30 to-cyan-500/30 border border-purple-400/40 flex items-center justify-center group-hover:from-purple-500/50 group-hover:via-pink-500/50 group-hover:to-cyan-500/50 group-hover:border-purple-400/60 transition-all duration-500 backdrop-blur-sm">
                        <UserPlus className="w-5 h-5 text-purple-300" />
                      </div>
                      {/* Icon glow */}
                      <div className="absolute inset-0 bg-purple-400/20 rounded-2xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="font-bold text-white text-base">Create Account</h4>
                        <div className="px-2.5 py-1 bg-gradient-to-r from-purple-500/25 to-pink-500/25 border border-purple-400/30 rounded-lg backdrop-blur-sm">
                          <span className="text-xs font-semibold text-purple-200">Free</span>
                        </div>
                      </div>
                      <p className="text-sm text-white/60 font-medium">Start earning in under 2 minutes</p>
                    </div>
                    <ArrowUpRight className="w-5 h-5 text-white/40 group-hover:text-purple-300 group-hover:translate-x-1 group-hover:-translate-y-1 transition-all duration-300" />
                  </div>
                </div>
              </Link>
            </div>            {/* Minimal Clean Footer */}
            <div 
              className="relative p-6 border-t border-white/20"
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(16px) saturate(120%)',
                WebkitBackdropFilter: 'blur(16px) saturate(120%)'
              }}
            >
              <div className="relative flex items-center justify-center">
                <div 
                  className="flex items-center gap-2 px-4 py-2 rounded-xl border border-emerald-400/30"
                  style={{
                    background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(59, 130, 246, 0.2))',
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)'
                  }}
                >
                  <Sparkles className="w-4 h-4 text-emerald-300" />
                  <span className="text-sm font-semibold text-emerald-200">Trusted by miners worldwide</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AuthDropdown;