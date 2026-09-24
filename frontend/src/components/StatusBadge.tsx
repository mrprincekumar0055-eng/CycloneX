"use client";

import React from "react";

export type BadgeType = 
  | "LIVE DATA" 
  | "HISTORICAL DATA" 
  | "DEMO MODE" 
  | "MODEL OUTPUT" 
  | "AI ADVISORY" 
  | "OFFICIAL SOURCE" 
  | "FALLBACK DATA";

interface StatusBadgeProps {
  type: BadgeType;
  label?: string;
  className?: string;
}

export default function StatusBadge({ type, label, className = "" }: StatusBadgeProps) {
  const text = label || type;

  // Unobtrusive, minimal, monochrome-leaning labels for enterprise clarity
  switch (type) {
    case "LIVE DATA":
      return (
        <span className={`inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 ${className}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          <span>{text}</span>
        </span>
      );
    case "OFFICIAL SOURCE":
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold text-slate-900 bg-slate-100 border border-slate-300 ${className}`}>
          {text}
        </span>
      );
    case "AI ADVISORY":
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-700 bg-slate-100 border border-slate-200 ${className}`}>
          {text}
        </span>
      );
    case "MODEL OUTPUT":
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-600 bg-slate-50 border border-slate-200 ${className}`}>
          {text}
        </span>
      );
    case "DEMO MODE":
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-amber-800 bg-amber-50 border border-amber-200 ${className}`}>
          {text}
        </span>
      );
    case "FALLBACK DATA":
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-600 bg-slate-100 border border-slate-200 ${className}`}>
          {text}
        </span>
      );
    case "HISTORICAL DATA":
    default:
      return (
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-600 bg-slate-100 border border-slate-200 ${className}`}>
          {text}
        </span>
      );
  }
}
