import React from 'react';
import { LucideIcon, Minus, Square, X } from 'lucide-react';

interface ResultCardProps {
  title: string;
  icon: LucideIcon;
  color: string; // Tailwind color class prefix (mapped to theme colors inside)
  children: React.ReactNode;
  delay?: number;
}

// Pastel Pixel Palette
const getThemeColor = (color: string) => {
  switch(color) {
    case 'emerald': return 'bg-[#34d399]'; // Mint
    case 'violet': return 'bg-[#a78bfa]'; // Lavender
    case 'blue': return 'bg-[#60a5fa]'; // Sky
    case 'rose': return 'bg-[#f472b6]'; // Pink
    case 'orange': return 'bg-[#fbbf24]'; // Gold
    default: return 'bg-gray-300';
  }
};

export const ResultCard: React.FC<ResultCardProps> = ({ title, icon: Icon, color, children, delay = 0 }) => {
  const headerBg = getThemeColor(color);

  return (
    <div 
        className={`bg-white pixel-border pixel-shadow mb-8 overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700`}
        style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      {/* Sweetheart Window Header */}
      <div className={`${headerBg} border-b-4 border-[#4c1d95] px-3 py-2 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
            <div className="bg-white border-2 border-[#4c1d95] p-1 shadow-sm">
                 <Icon className="w-4 h-4 text-[#4c1d95]" />
            </div>
            <h3 className="font-pixel text-xs text-white uppercase tracking-wider drop-shadow-md">{title}</h3>
        </div>
        <div className="flex gap-1.5">
            <button className="w-5 h-5 bg-white border-2 border-[#4c1d95] flex items-center justify-center hover:bg-yellow-200 transition-colors">
                <Minus className="w-3 h-3 text-[#4c1d95]" strokeWidth={3} />
            </button>
            <button className="w-5 h-5 bg-white border-2 border-[#4c1d95] flex items-center justify-center hover:bg-green-200 transition-colors">
                <Square className="w-2.5 h-2.5 text-[#4c1d95]" strokeWidth={3} />
            </button>
            <button className="w-5 h-5 bg-white border-2 border-[#4c1d95] flex items-center justify-center hover:bg-red-200 transition-colors">
                <X className="w-3 h-3 text-[#4c1d95]" strokeWidth={3} />
            </button>
        </div>
      </div>

      {/* Content Area */}
      <div className={`p-6 bg-white relative`}>
        {/* Dotted Background */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" 
             style={{ backgroundImage: 'radial-gradient(#4c1d95 1.5px, transparent 1.5px)', backgroundSize: '16px 16px' }}>
        </div>
        <div className="relative z-10 font-vt323 text-xl leading-relaxed text-[#2e1065]">
             {children}
        </div>
      </div>
    </div>
  );
};