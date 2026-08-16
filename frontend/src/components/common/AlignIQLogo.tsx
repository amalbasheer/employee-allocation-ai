import React from 'react';

interface AlignIQLogoProps {
  className?: string;
  size?: number;
}

export const AlignIQLogo: React.FC<AlignIQLogoProps> = ({ 
  className = "w-10 h-10",
  size
}) => {
  const rawId = React.useId();
  const uniqueId = rawId.replace(/:/g, '');

  return (
    <svg 
      viewBox="0 0 36 36" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size } : undefined}
    >
      <defs>
        {/* Main 'A' Gradient */}
        <linearGradient id={`aGrad-${uniqueId}`} x1="6" y1="6" x2="30" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#818CF8" /> {/* indigo-400 */}
          <stop offset="100%" stopColor="#6366F1" /> {/* indigo-600 */}
        </linearGradient>

        {/* Target Node Gradient */}
        <linearGradient id={`nodeGrad-${uniqueId}`} x1="14" y1="20" x2="22" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#34D399" /> {/* emerald-400 */}
          <stop offset="100%" stopColor="#22D3EE" /> {/* cyan-400 */}
        </linearGradient>
      </defs>

      {/* 1. Bold, Crisp Letter 'A' Outer Frame */}
      <path 
        d="M 6 30 L 18 6 L 30 30" 
        stroke={`url(#aGrad-${uniqueId})`} 
        strokeWidth="4" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
      />

      {/* 2. Straight Horizontal Crossbar */}
      <path 
        d="M 11 20 H 25" 
        stroke={`url(#aGrad-${uniqueId})`} 
        strokeWidth="3.5" 
        strokeLinecap="round" 
      />

      {/* 3. Central Target Node (Alignment Point) */}
      <circle cx="18" cy="20" r="4" fill={`url(#nodeGrad-${uniqueId})`} />
      <circle cx="18" cy="20" r="1.8" fill="#FFFFFF" />
    </svg>
  );
};