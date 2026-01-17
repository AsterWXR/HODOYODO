import React from 'react';
import { AnalysisResult } from '../types';
import { ResultCard } from './ResultCard';
import { 
  Coffee, 
  Search, 
  Aperture, 
  ShieldCheck, 
  User, 
  Sparkles
} from 'lucide-react';

interface AnalysisDisplayProps {
  result: AnalysisResult | null;
}

export const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ result }) => {
  if (!result) return null;

  return (
    <div className="space-y-8 pb-12">
      {/* Lifestyle Section */}
      <ResultCard title="生活方式分析" icon={Coffee} color="emerald" delay={100}>
        <p className="text-[#065f46] mb-6 font-vt323 text-2xl border-l-4 border-[#34d399] pl-4 bg-[#ecfdf5] py-2">
          {result.lifestyle.description}
        </p>
        <div className="flex flex-wrap gap-3">
          {result.lifestyle.tags.map((tag, idx) => (
            <span 
              key={idx} 
              className="inline-flex items-center px-3 py-1.5 bg-white border-2 border-[#34d399] text-[#065f46] shadow-[3px_3px_0px_0px_#34d399] font-pixel text-[10px] transform hover:-translate-y-0.5 transition-transform"
            >
              {tag.type === 'consumption' && <span className="mr-2">💰</span>}
              {tag.type === 'scene' && <span className="mr-2">📍</span>}
              {tag.type === 'object' && <span className="mr-2">✨</span>}
              {tag.tag}
            </span>
          ))}
        </div>
      </ResultCard>

      {/* Hidden Details Section */}
      <ResultCard title="隐藏细节发现" icon={Search} color="violet" delay={200}>
        <div className="bg-[#f5f3ff] p-4 border-2 border-dashed border-[#a78bfa] rounded-lg">
            <p className="mb-4 text-[#5b21b6] italic">"{result.details.description}"</p>
            <ul className="space-y-2">
            {result.details.findings.map((finding, idx) => (
                <li key={idx} className="flex items-start font-vt323 text-lg text-[#4c1d95]">
                <span className="mr-2 text-[#a78bfa]">✦</span>
                <span>{finding}</span>
                </li>
            ))}
            </ul>
        </div>
      </ResultCard>

      {/* Intention Section */}
      <ResultCard title="信号检测" icon={Aperture} color="blue" delay={300}>
         <div className="flex items-center justify-between mb-4 pb-2 border-b-2 border-[#bfdbfe]">
            <span className="text-[#1e40af] font-pixel text-xs">意图：</span>
            <span className="inline-block px-4 py-1 bg-[#dbeafe] text-[#1e40af] border-2 border-[#3b82f6] font-pixel text-[10px] rounded-full">
                {result.intention.category}
            </span>
         </div>
         <p className="text-[#1e3a8a] font-vt323 text-xl">
             {result.intention.description}
         </p>
      </ResultCard>

      {/* Credibility Section */}
      <ResultCard title="安全检查" icon={ShieldCheck} color="rose" delay={400}>
        <div className="flex flex-col md:flex-row gap-6 mb-4">
            <div className="flex-shrink-0 flex flex-col items-center justify-center p-4 bg-[#fdf2f8] border-2 border-[#f472b6] rounded-xl">
                <ShieldCheck className="w-10 h-10 text-[#db2777]" />
                <span className="text-[10px] text-[#db2777] mt-2 font-pixel">安全吗？</span>
            </div>
            <div className="flex-1">
                 <p className="text-[#831843] mb-4 text-xl">{result.credibility.description}</p>
                 <div className="space-y-2">
                    {result.credibility.clues.map((clue, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-[#be185d] font-vt323 text-lg">
                            <span className="text-sm font-bold">[!]</span>
                            {clue}
                        </div>
                    ))}
                </div>
            </div>
        </div>

        {result.credibility.exif && (result.credibility.exif.camera || result.credibility.exif.datetime) && (
            <div className="mt-4 pt-4 border-t-2 border-dashed border-[#fbcfe8]">
                <h4 className="text-[#db2777] font-pixel text-[10px] mb-3">元数据提取</h4>
                <div className="flex flex-wrap gap-3 font-mono-tech text-sm text-[#9d174d]">
                    {result.credibility.exif.camera && <div className="bg-[#fce7f3] px-2 py-1 rounded">相机: <b>{result.credibility.exif.camera}</b></div>}
                    {result.credibility.exif.datetime && <div className="bg-[#fce7f3] px-2 py-1 rounded">日期: <b>{result.credibility.exif.datetime}</b></div>}
                    {result.credibility.exif.has_gps !== undefined && <div className="bg-[#fce7f3] px-2 py-1 rounded">定位: <b>{result.credibility.exif.has_gps ? '有' : '无'}</b></div>}
                </div>
            </div>
        )}
      </ResultCard>

      {/* Person Section */}
      <ResultCard title="主角分析" icon={User} color="orange" delay={500}>
         <div className="mb-4 bg-[#fffbeb] border border-[#fcd34d] p-3 rounded-lg text-sm text-[#b45309] font-mono-tech flex items-center gap-2">
             <Sparkles className="w-4 h-4 text-[#f59e0b]" />
             <span>AI 估算 (仅供参考)</span>
         </div>
         <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
             <div className="bg-white border-2 border-[#fbbf24] p-3 text-center rounded-lg shadow-sm">
                 <div className="text-[10px] text-[#d97706] mb-1 font-pixel">身高</div>
                 <div className="text-[#78350f] font-bold text-lg">{result.person.estimated_height}</div>
             </div>
             <div className="bg-white border-2 border-[#fbbf24] p-3 text-center rounded-lg shadow-sm">
                 <div className="text-[10px] text-[#d97706] mb-1 font-pixel">体型</div>
                 <div className="text-[#78350f] font-bold text-lg">{result.person.body_type}</div>
             </div>
             <div className="bg-white border-2 border-[#fbbf24] p-3 text-center rounded-lg shadow-sm">
                 <div className="text-[10px] text-[#d97706] mb-1 font-pixel">性别</div>
                 <div className="text-[#78350f] font-bold text-lg">{result.person.gender}</div>
             </div>
         </div>
         <p className="text-[#92400e] font-vt323 text-xl border-t-2 border-[#fef3c7] pt-3">
             {result.person.description}
         </p>
      </ResultCard>
    </div>
  );
};