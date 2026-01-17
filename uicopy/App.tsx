import React, { useState } from 'react';
import { Header } from './components/Header';
import { ImageUploader } from './components/ImageUploader';
import { AnalysisDisplay } from './components/AnalysisDisplay';
import { LoadingOverlay } from './components/LoadingOverlay';
import { analyzeImage } from './services/geminiService';
import { AnalysisResult, AnalysisState } from './types';
import { AlertTriangle, Sparkles, Heart } from 'lucide-react';

const App: React.FC = () => {
  const [analysisState, setAnalysisState] = useState<AnalysisState>(AnalysisState.IDLE);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [imageData, setImageData] = useState<{ base64: string; previewUrl: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelected = (base64: string, previewUrl: string) => {
    setImageData({ base64, previewUrl });
    setAnalysisState(AnalysisState.IDLE);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!imageData) return;

    setAnalysisState(AnalysisState.ANALYZING);
    setError(null);

    try {
      const data = await analyzeImage(imageData.base64);
      setResult(data);
      setAnalysisState(AnalysisState.COMPLETE);
    } catch (err: any) {
      console.error(err);
      setError("哎呀！连接失败。请检查 API Key。");
      setAnalysisState(AnalysisState.ERROR);
    }
  };

  return (
    <div className="min-h-screen flex flex-col font-vt323 text-[#2e1065]">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
          
          {/* Left Column: Upload & Preview */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div className="relative min-h-[450px]">
               <ImageUploader 
                  onImageSelected={handleImageSelected} 
                  isAnalyzing={analysisState === AnalysisState.ANALYZING} 
               />
               
               {analysisState === AnalysisState.ANALYZING && <LoadingOverlay />}
            </div>

            {/* Action Area */}
            {imageData && analysisState !== AnalysisState.ANALYZING && (
              <div className="animate-in fade-in slide-in-from-bottom-2">
                 <button
                    onClick={handleAnalyze}
                    className="group w-full py-4 px-6 bg-[#ec4899] border-b-8 border-[#be185d] text-white font-pixel text-sm uppercase tracking-wider rounded-xl hover:bg-[#db2777] active:border-b-0 active:translate-y-2 transition-all flex items-center justify-center gap-3 shadow-xl"
                 >
                    <Sparkles className="w-5 h-5 animate-spin-slow group-hover:animate-spin" />
                    {analysisState === AnalysisState.COMPLETE ? '再次扫描' : '开始扫描'}
                 </button>
              </div>
            )}
            
            {error && (
               <div className="p-4 bg-red-50 border-2 border-red-400 text-red-700 flex items-center gap-3 font-mono-tech rounded-lg">
                  <AlertTriangle className="w-6 h-6 shrink-0 animate-bounce text-red-500" />
                  <span className="text-sm font-bold">{error}</span>
               </div>
            )}

            {/* Instructions Window */}
            <div className="hidden lg:block bg-white border-2 border-[#a855f7] pixel-shadow-sm rounded-lg overflow-hidden">
                 <div className="bg-[#a855f7] text-white px-3 py-1.5 font-pixel text-[10px] flex gap-2 items-center">
                    <Heart className="w-3 h-3 fill-white" />
                    使用说明.TXT
                 </div>
                <div className="p-4 bg-[#faf5ff]">
                    <ul className="text-xl font-vt323 text-[#6b21a8] space-y-2">
                        <li className="flex items-center gap-2">1. 上传目标照片</li>
                        <li className="flex items-center gap-2">2. 等待 AI 扫描...</li>
                        <li className="flex items-center gap-2">3. 阅读安全报告</li>
                        <li className="flex items-center gap-2">4. 保持安全! ❤️</li>
                    </ul>
                </div>
            </div>
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-7">
             {analysisState === AnalysisState.IDLE && !result && (
                <div className="h-full flex flex-col items-center justify-center text-center p-12 border-4 border-dashed border-[#d8b4fe] bg-white/50 rounded-3xl">
                    <div className="w-24 h-24 bg-white border-4 border-[#c084fc] rounded-full flex items-center justify-center mb-6 shadow-md animate-bounce-slow">
                        <Heart className="w-12 h-12 text-[#c084fc] fill-[#f3e8ff]" />
                    </div>
                    <h2 className="text-3xl font-pixel text-[#7c3aed] mb-2 sweet-glitch">准备扫描</h2>
                    <p className="font-vt323 text-2xl text-[#8b5cf6] max-w-md">
                        上传照片以检测社交信号和隐藏细节！
                    </p>
                </div>
             )}

             {result && (
                <AnalysisDisplay result={result} />
             )}
          </div>

        </div>
      </main>
    </div>
  );
};

export default App;