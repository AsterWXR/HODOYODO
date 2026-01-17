import React, { useCallback, useState } from 'react';
import { Upload, Image as ImageIcon, X, Heart } from 'lucide-react';

interface ImageUploaderProps {
  onImageSelected: (base64: string, previewUrl: string) => void;
  isAnalyzing: boolean;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({ onImageSelected, isAnalyzing }) => {
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      alert("⚠️ 哎呀！我们需要一张图片文件哦！");
      return;
    }
    
    const objectUrl = URL.createObjectURL(file);
    setPreview(objectUrl);

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = reader.result as string;
      const base64Data = base64String.split(',')[1];
      onImageSelected(base64Data, objectUrl);
    };
    reader.readAsDataURL(file);
  }, [onImageSelected]);

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const clearImage = () => {
    setPreview(null);
  };

  return (
    <div className="h-full flex flex-col pixel-border bg-white pixel-shadow-pink">
       {/* Window Header */}
       <div className="bg-[#ec4899] px-3 py-2 flex justify-between items-center border-b-4 border-[#4c1d95]">
           <div className="flex items-center gap-2">
               <Heart className="w-4 h-4 text-white fill-white" />
               <span className="text-white font-pixel text-xs">输入源.JPG</span>
           </div>
           <div className="px-2 py-0.5 bg-white border-2 border-[#4c1d95] text-[10px] font-pixel text-[#ec4899]">
               拖拽上传
           </div>
       </div>

      <div 
        className={`
          relative flex-1 transition-all duration-300 flex flex-col items-center justify-center p-6 m-3
          border-4 border-dashed rounded-lg
          ${isDragging ? 'border-[#ec4899] bg-[#fdf2f8]' : 'border-[#a855f7] bg-[#faf5ff]'}
          ${preview ? 'border-none p-0 bg-black overflow-hidden' : ''}
        `}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        {preview ? (
          <div className="relative w-full h-full flex items-center justify-center bg-gray-900 group">
            <img 
              src={preview} 
              alt="Uploaded preview" 
              className="max-w-full max-h-full object-contain"
            />
            {!isAnalyzing && (
               <button 
               onClick={(e) => { e.stopPropagation(); clearImage(); }}
               className="absolute top-4 right-4 p-2 bg-[#ec4899] border-2 border-white hover:bg-[#db2777] text-white pixel-shadow-sm transition-transform hover:-translate-y-1"
             >
               <X className="w-5 h-5" strokeWidth={3} />
             </button>
            )}
           
             <div className="absolute bottom-4 left-0 right-0 text-center pointer-events-none">
                <span className="px-4 py-2 bg-white border-2 border-[#4c1d95] text-[#4c1d95] font-pixel text-xs pixel-shadow-sm">
                   目标已锁定
                </span>
             </div>
          </div>
        ) : (
          <div className="text-center p-6">
            <div className={`mx-auto w-24 h-24 border-4 border-[#4c1d95] ${isDragging ? 'bg-[#ec4899] text-white' : 'bg-white text-[#4c1d95]'} flex items-center justify-center mb-6 pixel-shadow transition-colors rounded-xl`}>
              <Upload className="w-10 h-10" strokeWidth={2.5} />
            </div>
            <h3 className="text-lg font-pixel text-[#4c1d95] mb-3 leading-relaxed">
                把你的照片<br/>拖到这里！
            </h3>
            <label className="mt-4 inline-flex cursor-pointer items-center px-6 py-3 bg-[#8b5cf6] border-b-4 border-[#5b21b6] text-white font-pixel text-xs hover:bg-[#7c3aed] active:border-b-0 active:translate-y-1 transition-all rounded-lg">
              <span>选择文件</span>
              <input 
                type="file" 
                className="hidden" 
                accept="image/*"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
            </label>
            <p className="mt-6 text-sm font-vt323 text-[#a855f7] bg-white px-2 inline-block">
              支持格式：JPG, PNG
            </p>
          </div>
        )}
      </div>
    </div>
  );
};