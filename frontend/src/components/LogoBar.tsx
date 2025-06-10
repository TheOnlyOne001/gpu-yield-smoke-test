// src/components/LogoBar.tsx

import React, { useState, useEffect, useRef } from 'react';
import Image from 'next/image';

interface Provider {
  name: string;
  src: string;
  alt: string;
  description: string;
  stats?: {
    gpus?: string;
    price?: string;
  };
}

const providers: Provider[] = [
  {
    name: 'io.net',
    src: '/logos/ionet.svg',
    alt: 'io.net GPU Cloud',
    description: 'Decentralized GPU network',
    stats: {
      gpus: '10K+',
      price: 'From $0.30/hr'
    }
  },
  {
    name: 'Hyperbolic',
    src: '/logos/hyperbolic.svg',
    alt: 'Hyperbolic Labs',
    description: 'AI-focused GPU marketplace',
    stats: {
      gpus: '5K+',
      price: 'From $0.35/hr'
    }
  },
  {
    name: 'Akash',
    src: '/logos/akash.svg',
    alt: 'Akash Network',
    description: 'Decentralized cloud compute',
    stats: {
      gpus: '8K+',
      price: 'From $0.25/hr'
    }
  },
  {
    name: 'Vast.ai',
    src: '/logos/vastai.svg',
    alt: 'Vast.ai',
    description: 'GPU rental marketplace',
    stats: {
      gpus: '30K+',
      price: 'From $0.20/hr'
    }
  },
  {
    name: 'AWS',
    src: '/logos/aws.svg',
    alt: 'AWS Spot Instances',
    description: 'Enterprise cloud GPUs',
    stats: {
      gpus: 'Unlimited',
      price: 'From $0.90/hr'
    }
  },
];

export default function LogoBar() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="relative py-16 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-900/5 to-transparent" />
      
      <div className="container mx-auto px-4">
        {/* Section header */}
        <div className={`text-center mb-12 transition-all duration-600 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'
        }`}>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Tracking Real-Time Prices Across
          </h3>
          <h2 className="text-3xl md:text-4xl font-bold text-white">
            All Major GPU Providers
          </h2>
          <p className="mt-4 text-gray-300 max-w-2xl mx-auto">
            We aggregate pricing data from {providers.length}+ platforms to ensure you always get the best rates
          </p>
        </div>

        {/* Logo grid */}
        <div className="relative">
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 max-w-6xl mx-auto">
            {providers.map((provider, index) => (
              <div
                key={provider.name}
                className={`relative group transition-all duration-500 ${
                  isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'
                }`}
                style={{ transitionDelay: `${index * 100}ms` }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {/* Logo container */}
                <div className="relative">
                  <div className={`
                    relative h-12 w-32 md:h-14 md:w-40 
                    grayscale opacity-60 
                    transition-all duration-300 ease-out
                    group-hover:grayscale-0 group-hover:opacity-100 
                    group-hover:scale-110
                    ${hoveredIndex === index ? 'z-10' : 'z-0'}
                  `}>
                    <Image
                      src={provider.src}
                      alt={provider.alt}
                      fill
                      className="object-contain"
                      sizes="(max-width: 768px) 128px, 160px"
                    />
                  </div>
                  
                  {/* Glow effect on hover */}
                  <div className={`
                    absolute inset-0 rounded-lg bg-gradient-to-r 
                    from-blue-500/20 to-purple-500/20 blur-xl
                    transition-opacity duration-300
                    ${hoveredIndex === index ? 'opacity-100' : 'opacity-0'}
                  `} />
                </div>

                {/* Tooltip with stats */}
                <div className={`
                  absolute bottom-full left-1/2 -translate-x-1/2 mb-4
                  bg-slate-900/95 backdrop-blur-sm rounded-lg p-4
                  border border-white/10 shadow-xl
                  transition-all duration-200 origin-bottom
                  ${hoveredIndex === index 
                    ? 'opacity-100 scale-100 pointer-events-auto' 
                    : 'opacity-0 scale-95 pointer-events-none'
                  }
                  w-48 z-20
                `}>
                  <div className="text-center">
                    <p className="font-semibold text-white mb-1">{provider.name}</p>
                    <p className="text-xs text-gray-400 mb-3">{provider.description}</p>
                    {provider.stats && (
                      <div className="flex justify-around text-xs">
                        {provider.stats.gpus && (
                          <div>
                            <p className="text-gray-500">GPUs</p>
                            <p className="text-blue-400 font-medium">{provider.stats.gpus}</p>
                          </div>
                        )}
                        {provider.stats.price && (
                          <div>
                            <p className="text-gray-500">Starting</p>
                            <p className="text-green-400 font-medium">{provider.stats.price}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Tooltip arrow */}
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 
                                  bg-slate-900 border-r border-b border-white/10 
                                  rotate-45" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom stats */}
        <div className={`mt-12 flex flex-wrap justify-center gap-8 text-center transition-all duration-600 delay-500 ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}>
          <div className="px-4">
            <p className="text-3xl font-bold text-white">50K+</p>
            <p className="text-sm text-gray-400">Total GPUs Tracked</p>
          </div>
          <div className="px-4">
            <p className="text-3xl font-bold text-white">24/7</p>
            <p className="text-sm text-gray-400">Real-time Updates</p>
          </div>
          <div className="px-4">
            <p className="text-3xl font-bold text-white">5+</p>
            <p className="text-sm text-gray-400">Platforms Monitored</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// Minimal version without animations for performance-sensitive environments
export function LogoBarMinimal() {
  return (
    <div className="py-12">
      <p className="text-center text-sm text-gray-400 mb-6">Tracking prices across</p>
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-6 px-4">
        {providers.map(({ src, alt, name }) => (
          <div 
            key={name} 
            className="relative h-10 w-28 grayscale opacity-60 transition-all duration-300 hover:grayscale-0 hover:opacity-100"
          >
            <Image
              src={src}
              alt={alt}
              fill
              className="object-contain"
              sizes="112px"
            />
          </div>
        ))}
      </div>
    </div>
  );
}