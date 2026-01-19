import { AlertTriangle, Music, Gauge, Zap } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent, cn } from '@autodj/ui';

interface CompatibilityCardProps {
  compatibilityScore: number | null;
  harmonicScore: number | null;
  bpmScore: number | null;
  energyScore: number | null;
  bpmDifference: number | null;
}

/**
 * Compatibility score card showing how well two tracks will mix
 */
export function CompatibilityCard({
  compatibilityScore,
  harmonicScore,
  bpmScore,
  energyScore,
  bpmDifference,
}: CompatibilityCardProps) {
  if (compatibilityScore === null) return null;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getScoreBackground = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const showBpmWarning = bpmDifference !== null && bpmDifference > 8;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Compatibility Score
          {showBpmWarning && (
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main Score */}
        <div className="flex items-center justify-center">
          <div className="relative w-32 h-32">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                strokeDasharray={`${(compatibilityScore / 100) * 352} 352`}
                className={getScoreBackground(compatibilityScore)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={cn('text-3xl font-bold', getScoreColor(compatibilityScore))}>
                {compatibilityScore}%
              </span>
            </div>
          </div>
        </div>

        {/* Detail Scores */}
        <div className="grid grid-cols-3 gap-4">
          <ScoreBar
            icon={Music}
            label="Harmonic"
            score={harmonicScore}
            tooltip="Key compatibility"
          />
          <ScoreBar
            icon={Gauge}
            label="BPM"
            score={bpmScore}
            tooltip={bpmDifference !== null ? `${bpmDifference.toFixed(1)}% difference` : undefined}
          />
          <ScoreBar
            icon={Zap}
            label="Energy"
            score={energyScore}
            tooltip="Energy level match"
          />
        </div>

        {/* BPM Warning */}
        {showBpmWarning && (
          <div className="text-sm text-yellow-600 dark:text-yellow-400 bg-yellow-500/10 rounded-lg p-3">
            <strong>Note:</strong> BPM difference of {bpmDifference?.toFixed(1)}% is above the 8% threshold.
            The transition will use a simple crossfade instead of beat-matched stems.
          </div>
        )}

        {/* Score Legend */}
        <div className="flex justify-center gap-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span>Great (80+)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span>Good (60-79)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span>Poor (&lt;60)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ScoreBarProps {
  icon: typeof Music;
  label: string;
  score: number | null;
  tooltip?: string;
}

function ScoreBar({ icon: Icon, label, score, tooltip }: ScoreBarProps) {
  if (score === null) return null;

  const getColor = (s: number) => {
    if (s >= 80) return 'bg-green-500';
    if (s >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1 text-muted-foreground">
          <Icon className="h-3 w-3" />
          <span>{label}</span>
        </div>
        <span className="font-medium">{score}%</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden" title={tooltip}>
        <div
          className={cn('h-full rounded-full transition-all', getColor(score))}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
