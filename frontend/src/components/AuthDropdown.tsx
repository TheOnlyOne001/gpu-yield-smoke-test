// frontend/src/components/AuthDropdown.tsx
// Modern AuthDropdown with glassmorphism matching navigation style

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { 
  ChevronDown, 
  LogIn,
  UserPlus,
  User,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AuthDropdownProps {
  className?: string;
}

const AuthDropdown: React.FC<AuthDropdownProps> = ({ className = "" }) => {
  const [isOpen, setIsOpen] = useState(false);
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
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Modern Trigger Button matching navigation style */}
      <div 
        className="p-1 rounded-2xl border"
        style={{ 
          background: 'rgba(255, 255, 255, 0.04)',
          borderColor: 'rgba(255, 255, 255, 0.08)'
        }}
      >
        <Button
          variant="ghost"
          className={`
            group relative
            px-4 py-2.5 rounded-xl
            text-sm font-medium
            transition-all duration-200 ease-out
            hover:bg-white/[0.08]
            focus:outline-none focus:ring-2 focus:ring-blue-500/20
            ${isOpen ? 'bg-white/[0.08] text-white' : 'text-gray-400'}
          `}
          style={{ 
            color: isOpen ? '#F4F6FF' : 'rgba(244, 246, 255, 0.64)'
          }}
          onClick={() => setIsOpen(!isOpen)}
          onMouseEnter={(e) => { 
            if (!isOpen) (e.currentTarget as HTMLElement).style.color = '#F4F6FF';
          }}
          onMouseLeave={(e) => { 
            if (!isOpen) (e.currentTarget as HTMLElement).style.color = 'rgba(244, 246, 255, 0.64)';
          }}
        >
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                <User className="w-3.5 h-3.5" />
              </div>
              {/* Subtle glow on hover */}
              <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 blur-md opacity-0 group-hover:opacity-60 transition-opacity duration-300" />
            </div>
            <span>Account</span>
            <ChevronDown 
              className={`w-4 h-4 transition-transform duration-200 ${
                isOpen ? 'rotate-180' : ''
              }`} 
            />
          </div>
        </Button>
      </div>

      {/* Modern Dropdown with glassmorphism */}
      {isOpen && (
        <>
          {/* Mobile backdrop */}
          <div 
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden" 
            onClick={() => setIsOpen(false)} 
          />
          
          <div 
            className={`
              absolute right-0 mt-3 w-72
              border rounded-2xl
              shadow-2xl
              z-50 overflow-hidden
              animate-dropdown-enter
            `}
            style={{
              background: 'rgba(17, 18, 24, 0.72)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              borderColor: 'rgba(255, 255, 255, 0.08)',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)'
            }}
          >
            {/* Ambient glow effect */}
            <div className="absolute inset-0 bg-gradient-to-b from-purple-500/5 via-transparent to-blue-500/5 pointer-events-none" />

            {/* Content */}
            <div className="relative p-2">
              {/* Sign In */}
              <Link href="/signin" onClick={() => setIsOpen(false)}>
                <div 
                  className="group relative flex items-center gap-3 p-4 rounded-xl transition-all duration-200 cursor-pointer hover:bg-white/[0.04]"
                >
                  {/* Hover background effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/0 via-blue-500/5 to-blue-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  <div className="relative">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 flex items-center justify-center group-hover:from-blue-500/20 group-hover:to-cyan-500/20 transition-colors duration-300">
                      <LogIn className="w-5 h-5 text-blue-400" />
                    </div>
                  </div>
                  <div className="relative flex-1">
                    <h4 className="text-sm font-semibold text-white mb-0.5">Sign in to your account</h4>
                    <p className="text-xs text-gray-400">Access dashboard & earnings</p>
                  </div>
                  <Sparkles className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors duration-300" />
                </div>
              </Link>

              {/* Divider */}
              <div className="relative my-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.06]"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 text-gray-500 bg-[rgba(17,18,24,0.72)]">or</span>
                </div>
              </div>

              {/* Create Account */}
              <Link href="/signup" onClick={() => setIsOpen(false)}>
                <div 
                  className="group relative flex items-center gap-3 p-4 rounded-xl transition-all duration-200 cursor-pointer hover:bg-white/[0.04]"
                >
                  {/* Hover background effect */}
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500/0 via-purple-500/5 to-purple-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  <div className="relative">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 flex items-center justify-center group-hover:from-purple-500/20 group-hover:to-pink-500/20 transition-colors duration-300">
                      <UserPlus className="w-5 h-5 text-purple-400" />
                    </div>
                  </div>
                  <div className="relative flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h4 className="text-sm font-semibold text-white">Create new account</h4>
                      <span 
                        className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md"
                        style={{
                          background: 'linear-gradient(135deg, #7A5FFF, #01C8FF)',
                          color: 'white'
                        }}
                      >
                        Free
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">Start earning in minutes</p>
                  </div>
                </div>
              </Link>
            </div>

            {/* Bottom gradient fade */}
            <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-[rgba(17,18,24,0.72)] to-transparent pointer-events-none" />
          </div>
        </>
      )}
    </div>
  );
};

export default AuthDropdown;