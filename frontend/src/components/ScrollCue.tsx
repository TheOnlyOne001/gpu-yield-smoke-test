import React, { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function ScrollCue() {
  const [hidden, setHidden] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    let ticking = false;
    
    const updateScrollState = () => {
      setHidden(window.scrollY > 50);
      ticking = false;
    };
    
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updateScrollState);
        ticking = true;
      }
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToNext = () => {
    const el = document.getElementById('features');
    if (el) {
      const navHeight = 64;
      const elementPosition = el.getBoundingClientRect().top + window.pageYOffset;
      const offsetPosition = elementPosition - navHeight;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
      
      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('event', 'scroll_cue_click');
      }
    }
  };

  return (
    <div className={`fixed bottom-8 left-1/2 -translate-x-1/2 z-10 transition-all duration-700 ease-out ${
      hidden ? 'opacity-0 translate-y-8 pointer-events-none' : 'opacity-100 translate-y-0'
    }`}>
      <button
        aria-label="Scroll to features section"
        onClick={scrollToNext}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="group relative"
      >
        {/* Outer ring animation */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 opacity-20 blur-xl 
                        animate-pulse group-hover:opacity-30 transition-opacity duration-300" />
        
        {/* Middle ring */}
        <div className={`absolute inset-0 rounded-full bg-white/10 backdrop-blur-sm
                        transition-all duration-300 ${isHovered ? 'scale-110' : 'scale-100'}`} />
        
        {/* Inner button */}
        <div className="relative w-12 h-12 rounded-full bg-white/10 backdrop-blur-md 
                        border border-white/20 flex items-center justify-center
                        transition-all duration-300 hover:bg-white/20 hover:border-white/30
                        group-hover:shadow-[0_0_20px_rgba(255,255,255,0.3)]">
          
          {/* Arrow container with bounce animation */}
          <div className="relative">
            {/* Primary arrow */}
            <ChevronDown className="w-5 h-5 text-white/90 animate-bounce" 
                         style={{
                           animationDuration: '2s',
                           animationDelay: '0s'
                         }} />
            
            {/* Secondary arrow for layered effect */}
            <ChevronDown className="absolute inset-0 w-5 h-5 text-white/40 animate-bounce" 
                         style={{
                           animationDuration: '2s',
                           animationDelay: '0.1s'
                         }} />
          </div>
        </div>
        
        {/* Hover text */}
        <span className={`absolute -top-8 left-1/2 -translate-x-1/2 text-xs text-white/70 whitespace-nowrap
                         transition-all duration-300 ${isHovered ? 'opacity-100 -translate-y-1' : 'opacity-0 translate-y-1'}`}>
          Discover More
        </span>
      </button>
      
      {/* Ripple effect on hover */}
      {isHovered && (
        <>
          <div className="absolute inset-0 rounded-full border border-white/20 animate-ping" />
          <div className="absolute inset-0 rounded-full border border-white/10 animate-ping" 
               style={{ animationDelay: '0.2s' }} />
        </>
      )}
    </div>
  );
}