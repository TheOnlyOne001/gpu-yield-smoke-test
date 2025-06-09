import React, { useState, useEffect } from 'react';
import { TrendingUp, Zap, DollarSign, BarChart3, Bell, Shield, Users, ArrowRight, Play, CheckCircle, Star } from 'lucide-react';

const EnhancedLandingPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [livePrice, setLivePrice] = useState({ gpu: 'RTX 4090', price: 0.75, platform: 'vast.ai' });
  const [roi, setRoi] = useState(null);

  // Simulate live price updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLivePrice(prev => ({
        ...prev,
        price: parseFloat((Math.random() * 0.5 + 0.5).toFixed(3))
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: "Real-Time Price Tracking",
      description: "Monitor GPU rental prices across 15+ platforms updated every 60 seconds"
    },
    {
      icon: <DollarSign className="w-6 h-6" />,
      title: "Profit Calculator",
      description: "Calculate exact ROI based on your electricity costs and hardware setup"
    },
    {
      icon: <Bell className="w-6 h-6" />,
      title: "Smart Alerts",
      description: "Get notified instantly when profitable opportunities match your criteria"
    },
    {
      icon: <BarChart3 className="w-6 h-6" />,
      title: "Advanced Analytics",
      description: "Historical trends, platform comparisons, and earning predictions"
    }
  ];

  const testimonials = [
    {
      name: "Alex Chen",
      role: "ML Engineer",
      content: "Increased my GPU earnings by 40% in the first month. The alerts are incredibly accurate.",
      rating: 5
    },
    {
      name: "Sarah Kim",
      role: "Crypto Miner",
      content: "Finally, a tool that actually helps me find the best rates. The ROI calculator is spot-on.",
      rating: 5
    }
  ];

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "/month",
      features: ["Basic price monitoring", "5 alerts per day", "Community support"],
      cta: "Get Started",
      popular: false
    },
    {
      name: "Pro",
      price: "$19",
      period: "/month",
      features: ["Real-time alerts", "Unlimited notifications", "Historical analytics", "API access", "Priority support"],
      cta: "Start Free Trial",
      popular: true
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "",
      features: ["Custom integrations", "Dedicated support", "White-label options", "Advanced reporting"],
      cta: "Contact Sales",
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:60px_60px]" />
        
        {/* Navigation */}
        <nav className="relative z-10 container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Zap className="w-8 h-8 text-yellow-400" />
              <span className="text-2xl font-bold text-white">GPU Yield</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="text-gray-300 hover:text-white transition-colors">Pricing</a>
              <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                Sign In
              </button>
            </div>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="relative z-10 container mx-auto px-6 py-20">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center px-4 py-2 bg-purple-500/20 border border-purple-500/30 rounded-full text-purple-200 text-sm mb-8">
              <Zap className="w-4 h-4 mr-2" />
              Live tracking 50,000+ GPU instances
            </div>
            
            <h1 className="text-6xl md:text-7xl font-bold text-white mb-6 leading-tight">
              Maximize Your
              <span className="bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent"> GPU Earnings</span>
            </h1>
            
            <p className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto">
              Find the most profitable GPU rental opportunities in real-time. 
              Get alerts when rates spike and calculate your exact ROI instantly.
            </p>

            {/* Live Price Card */}
            <div className="inline-flex items-center space-x-4 bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl p-6 mb-12">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
              <div className="text-left">
                <div className="text-sm text-gray-300">Live Deal</div>
                <div className="text-lg font-semibold text-white">
                  {livePrice.gpu} · ${livePrice.price}/hr · {livePrice.platform}
                </div>
              </div>
              <div className="text-green-400 font-semibold">+15% vs avg</div>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-xl transition-all transform hover:scale-105 shadow-lg">
                <div className="flex items-center justify-center space-x-2">
                  <span>Start Earning More</span>
                  <ArrowRight className="w-5 h-5" />
                </div>
              </button>
              <button className="px-8 py-4 bg-white/10 backdrop-blur-lg border border-white/20 hover:bg-white/20 text-white font-semibold rounded-xl transition-all">
                <div className="flex items-center justify-center space-x-2">
                  <Play className="w-5 h-5" />
                  <span>Watch Demo</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <section id="features" className="py-24 bg-slate-800/50">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              Everything you need to maximize profits
            </h2>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
              Professional-grade tools used by thousands of GPU owners worldwide
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="group p-6 bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl hover:bg-white/10 transition-all duration-300">
                <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
                <p className="text-gray-300 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-16 bg-slate-900/50">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-white mb-2">$2.4M+</div>
              <div className="text-gray-300">Total earnings tracked</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-white mb-2">50K+</div>
              <div className="text-gray-300">GPU instances monitored</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-white mb-2">98.9%</div>
              <div className="text-gray-300">Alert accuracy</div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24">
        <div className="container mx-auto px-6">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Trusted by GPU owners worldwide
          </h2>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="p-6 bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl">
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-300 mb-4 text-lg italic">"{testimonial.content}"</p>
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white font-semibold mr-3">
                    {testimonial.name[0]}
                  </div>
                  <div>
                    <div className="text-white font-semibold">{testimonial.name}</div>
                    <div className="text-gray-400 text-sm">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 bg-slate-800/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Choose your plan</h2>
            <p className="text-xl text-gray-300">Start free, upgrade when you need more</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {plans.map((plan, index) => (
              <div key={index} className={`relative p-8 rounded-2xl border-2 transition-all duration-300 hover:scale-105 ${
                plan.popular 
                  ? 'border-purple-500 bg-gradient-to-b from-purple-500/20 to-transparent' 
                  : 'border-white/20 bg-white/5 backdrop-blur-lg'
              }`}>
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white text-sm font-semibold rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-gray-300 ml-1">{plan.period}</span>
                  </div>
                </div>

                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center text-gray-300">
                      <CheckCircle className="w-5 h-5 text-green-400 mr-3 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button className={`w-full py-3 rounded-xl font-semibold transition-all ${
                  plan.popular
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white'
                    : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
                }`}>
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="container mx-auto px-6 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to maximize your GPU earnings?
          </h2>
          <p className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto">
            Join thousands of GPU owners who've increased their profits by an average of 35%
          </p>
          <button className="px-12 py-4 bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-black font-bold rounded-xl transition-all transform hover:scale-105 shadow-lg text-lg">
            Start Your Free Trial
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-12">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <Zap className="w-6 h-6 text-yellow-400" />
              <span className="text-xl font-bold text-white">GPU Yield</span>
            </div>
            <div className="text-gray-400 text-sm">
              © 2024 GPU Yield. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default EnhancedLandingPage;