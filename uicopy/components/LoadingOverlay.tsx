import React, { useEffect, useState } from 'react';
import { Heart, Lock, Sparkles, Search, Shield } from 'lucide-react';

interface LoadingOverlayProps {
  message?: string; // Optional override, but we'll use our internal cycle mostly
}

const LOADING_STEPS = [
  "正在初始化甜心引擎...",
  "正在提取像素中的秘密...",
  "正在扫描社交信号...",
  "正在进行安全协议握手...",
  "正在生成最终报告...",
  "马上就好...",
];

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ message }) => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % LOADING_STEPS.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  const currentText = message || LOADING_STEPS[stepIndex];

  return (
    <div className="absolute inset-0 bg-[#fdf2f8]/95 z-20 flex flex-col items-center justify-center backdrop-blur-sm overflow-hidden">
      <style>{`
        @keyframes stripe-move {
          0% { background-position: 0 0; }
          100% { background-position: 50px 50px; }
        }
        .candy-stripe {
          background-image: linear-gradient(
            45deg, 
            #ec4899 25%, 
            #f472b6 25%, 
            #f472b6 50%, 
            #ec4899 50%, 
            #ec4899 75%, 
            #f472b6 75%, 
            #f472b6 100%
          );
          background-size: 50px 50px;
          animation: stripe-move 1s linear infinite;
        }
        @keyframes float-up {
          0% { transform: translateY(0) rotate(0deg); opacity: 0; }
          50% { opacity: 1; }
          100% { transform: translateY(-100px) rotate(20deg); opacity: 0; }
        }
        .particle {
           animation: float-up 3s ease-in-out infinite;
        }
      `}</style>

      {/* Floating Particles Background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/2 left-1/4 particle" style={{ animationDelay: '0s' }}>
              <Sparkles className="w-6 h-6 text-[#a78bfa]" />
          </div>
          <div className="absolute top-2/3 right-1/4 particle" style={{ animationDelay: '1s' }}>
              <Heart className="w-5 h-5 text-[#f472b6] fill-[#f472b6]" />
          </div>
          <div className="absolute top-1/3 right-1/3 particle" style={{ animationDelay: '0.5s' }}>
              <Shield className="w-4 h-4 text-[#34d399]" />
          </div>
          <div className="absolute bottom-1/3 left-1/3 particle" style={{ animationDelay: '2s' }}>
               <Search className="w-5 h-5 text-[#60a5fa]" />
          </div>
          <div className="absolute top-1/4 left-1/2 particle" style={{ animationDelay: '1.5s' }}>
               <Heart className="w-3 h-3 text-[#fbbf24] fill-[#fbbf24]" />
          </div>
      </div>

      {/* Main Pixel Art Heart Animation */}
      <div className="relative mb-8 group scale-125 transition-transform duration-500">
         <div className="absolute inset-0 bg-[#ec4899] blur-2xl opacity-30 rounded-full animate-pulse"></div>
         
         <div className="relative">
             <Heart className="w-24 h-24 text-[#ec4899] fill-[#fbcfe8] animate-bounce drop-shadow-[4px_4px_0px_#4c1d95]" strokeWidth={2.5} />
             
             {/* Overlay Icon that changes */}
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                {stepIndex % 2 === 0 ? (
                    <Lock className="w-8 h-8 text-[#4c1d95] animate-ping" strokeWidth={3} />
                ) : (
                    <Sparkles className="w-8 h-8 text-[#8b5cf6] animate-spin" strokeWidth={3} />
                )}
             </div>
         </div>
      </div>
      
      {/* Glitchy Text */}
      <h3 className="text-2xl font-pixel text-[#4c1d95] sweet-glitch animate-pulse text-center px-4 leading-relaxed min-h-[3rem] flex items-center justify-center">
        {currentText}
      </h3>
      
      {/* Retro Candy Stripe Progress Bar */}
      <div className="mt-8 w-72 h-8 bg-white border-4 border-[#4c1d95] p-1 rounded-full pixel-shadow relative overflow-hidden">
          <div className="h-full w-full rounded-full candy-stripe shadow-inner"></div>
      </div>
      
      <p className="mt-4 font-vt323 text-[#8b5cf6] text-xl animate-pulse">
        [ 请勿关闭窗口 ]
      </p>
    </div>
  );
};