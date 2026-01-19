import { ArrowDown, Zap, Music, TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

import { cn } from '@autodj/ui';
import type { Transition, HarmonicCompatibility } from '@/services/projects.service';

interface TransitionIndicatorProps {
  transition: Transition;
}

/**
 * Labels and colors for harmonic compatibility types
 */
const compatibilityConfig: Record<HarmonicCompatibility, { label: string; color: string; icon: typeof Music }> = {
  PERFECT_MATCH: { label: 'Perfect', color: 'text-green-500', icon: Music },
  ADJACENT: { label: 'Adjacent', color: 'text-green-400', icon: Music },
  RELATIVE: { label: 'Relative', color: 'text-blue-400', icon: Music },
  DIAGONAL_ADJACENT: { label: 'Diagonal', color: 'text-blue-300', icon: Music },
  ENERGY_BOOST: { label: 'Energy Boost', color: 'text-yellow-400', icon: Zap },
  COMPATIBLE: { label: 'Compatible', color: 'text-orange-400', icon: Music },
  RISKY: { label: 'Risky', color: 'text-red-400', icon: AlertTriangle },
};

/**
 * Get score color based on value
 */
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-500';
  if (score >= 60) return 'text-yellow-500';
  if (score >= 40) return 'text-orange-500';
  return 'text-red-500';
}

/**
 * Get energy flow icon
 */
function getEnergyIcon(difference: number) {
  if (difference > 0.05) return TrendingUp;
  if (difference < -0.05) return TrendingDown;
  return Minus;
}

/**
 * Transition indicator component showing the quality of transition between two tracks
 */
export function TransitionIndicator({ transition }: TransitionIndicatorProps) {
  const config = compatibilityConfig[transition.compatibilityType];
  const CompatibilityIcon = config.icon;
  const EnergyIcon = getEnergyIcon(transition.energyDifference);
  const scoreColor = getScoreColor(transition.score);

  return (
    <div className="flex items-center justify-center py-2">
      <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-muted/50 border border-border/50">
        {/* Main score */}
        <div className={cn('text-lg font-bold', scoreColor)}>
          {transition.score}
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-border" />

        {/* Compatibility type */}
        <div className="flex items-center gap-1.5">
          <CompatibilityIcon className={cn('h-4 w-4', config.color)} />
          <span className={cn('text-xs font-medium', config.color)}>
            {config.label}
          </span>
        </div>

        {/* BPM difference */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <span>BPM</span>
          <span className={transition.bpmDifference <= 4 ? 'text-green-400' : 'text-orange-400'}>
            {transition.bpmDifference > 0 ? `+${transition.bpmDifference.toFixed(1)}%` : '0%'}
          </span>
        </div>

        {/* Energy flow */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <EnergyIcon className={cn(
            'h-3.5 w-3.5',
            transition.energyDifference > 0.05 ? 'text-green-400' :
            transition.energyDifference < -0.05 ? 'text-orange-400' : 'text-gray-400'
          )} />
          <span>
            {transition.energyDifference > 0 ? '+' : ''}{(transition.energyDifference * 100).toFixed(0)}%
          </span>
        </div>

        {/* Arrow */}
        <ArrowDown className="h-4 w-4 text-muted-foreground" />
      </div>
    </div>
  );
}
