import React from 'react';
import { Shield, Heart } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-sm border-b-4 border-[#4c1d95] shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Logo Icon */}
          <div className="relative group cursor-pointer">
            <div className="absolute inset-0 bg-[#4c1d95] translate-x-1 translate-y-1 rounded-sm"></div>
            <div className="relative bg-[#a855f7] p-2 border-2 border-black rounded-sm group-hover:-translate-y-1 transition-transform">
               <Shield className="w-8 h-8 text-white fill-[#ec4899]" strokeWidth={2.5} />
               <div className="absolute -top-1 -right-1">
                   <Heart className="w-4 h-4 text-white fill-white animate-bounce" />
               </div>
            </div>
          </div>
          
          <div className="flex flex-col">
            <h1 className="text-xl md:text-2xl font-bold font-pixel text-[#4c1d95] sweet-glitch tracking-tight">
              网恋<span className="text-[#ec4899]">安全卫士</span>
            </h1>
            <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-[#ec4899] text-white text-[10px] font-pixel rounded-full">BETA</span>
                <p className="text-xs font-pixel text-[#8b5cf6] hidden sm:block tracking-widest">
                  HO DO YO DO
                </p>
            </div>
          </div>
        </div>

        <div className="flex items-center">
            <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-[#f3e8ff] border-2 border-[#a855f7] rounded-lg pixel-shadow-sm">
              <div className="w-3 h-3 bg-[#ec4899] rounded-full animate-ping"></div>
              <span className="text-[#4c1d95] font-pixel text-xs">系统状态：可爱</span>
            </div>
        </div>
      </div>
    </header>
  );
};