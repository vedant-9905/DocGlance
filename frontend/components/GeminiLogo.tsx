import React from "react";

interface GeminiLogoProps {
  className?: string;
  size?: number;
}

export default function GeminiLogo({ className = "", size = 24 }: GeminiLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="geminiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4285f4" />
          <stop offset="35%" stopColor="#9b72cb" />
          <stop offset="70%" stopColor="#d96570" />
          <stop offset="100%" stopColor="#fbbc04" />
        </linearGradient>
      </defs>
      <path
        d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z"
        fill="url(#geminiGrad)"
      />
    </svg>
  );
}
