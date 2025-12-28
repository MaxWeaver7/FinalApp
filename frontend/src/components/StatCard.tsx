import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  subValue?: string;
  trend?: 'positive' | 'negative' | 'neutral';
  sparkline?: ReactNode;
  className?: string;
  delay?: number;
  rank?: number | string;
  teamColors?: { primary: string; secondary: string };
}

export function StatCard({ label, value, subValue, trend = 'neutral', sparkline, className, delay = 0, rank, teamColors }: StatCardProps) {
  return (
    <div 
      className={cn(
        "glass-card rounded-xl p-4 opacity-0 animate-slide-up border-2",
        className
      )}
      style={{ 
        animationDelay: `${delay}ms`,
        background: teamColors ? `linear-gradient(135deg, ${teamColors.primary}30, ${teamColors.secondary}20)` : undefined,
        borderColor: teamColors?.primary || undefined,
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </p>
        {rank && (
          <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">
            #{rank}
          </span>
        )}
      </div>
      <div className={cn(
        "text-2xl font-bold font-mono",
        trend === 'positive' && "text-primary",
        trend === 'negative' && "text-destructive",
        trend === 'neutral' && "text-foreground"
      )}>
        {value}
      </div>
      {subValue && (
        <p className="text-xs text-muted-foreground mt-1">
          {subValue}
        </p>
      )}
      {sparkline && (
        <div className="mt-2 -mx-2 -mb-2">
          {sparkline}
        </div>
      )}
    </div>
  );
}


