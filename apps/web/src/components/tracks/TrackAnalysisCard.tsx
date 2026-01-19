import { useState } from 'react';
import { ChevronDown, ChevronUp, Zap, Music2, Volume2, Gauge } from 'lucide-react';
import { cn, Badge, Button, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@autodj/ui';
import type { TrackAnalysis } from '@/services/projects.service';

interface TrackAnalysisCardProps {
  analysis: TrackAnalysis;
  duration?: number | null;
}

/**
 * Get color class based on energy level
 */
function getEnergyColor(energy: number): string {
  if (energy > 0.7) return 'bg-red-500';
  if (energy > 0.4) return 'bg-yellow-500';
  return 'bg-green-500';
}

/**
 * Get color for danceability
 */
function getDanceabilityColor(danceability: number): string {
  if (danceability > 0.7) return 'bg-purple-500';
  if (danceability > 0.4) return 'bg-blue-500';
  return 'bg-slate-400';
}

/**
 * Get color for confidence badge
 */
function getConfidenceBadge(confidence: number): { variant: 'default' | 'secondary' | 'outline'; label: string } {
  if (confidence >= 0.8) return { variant: 'default', label: 'High' };
  if (confidence >= 0.5) return { variant: 'secondary', label: 'Med' };
  return { variant: 'outline', label: 'Low' };
}

/**
 * Get section type color
 */
function getSectionColor(type: string): string {
  switch (type) {
    case 'drop': return 'bg-red-500';
    case 'buildup': return 'bg-orange-500';
    case 'breakdown': return 'bg-blue-500';
    case 'main': return 'bg-green-500';
    default: return 'bg-gray-500';
  }
}

/**
 * Format time in seconds to mm:ss
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Mini progress bar component
 */
function MiniBar({ value, color, label }: { value: number; color: string; label: string }) {
  const clampedValue = Math.min(1, Math.max(0, value));
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1.5">
            <div className="w-12 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', color)}
                style={{ width: `${clampedValue * 100}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-8">
              {Math.round(clampedValue * 100)}%
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{label}: {Math.round(clampedValue * 100)}%</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Track structure timeline visualization
 */
function StructureTimeline({
  analysis,
  duration
}: {
  analysis: TrackAnalysis;
  duration: number;
}) {
  const structure = analysis.structureJson;
  if (!structure?.sections?.length) return null;

  return (
    <div className="mt-3 pt-3 border-t">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-muted-foreground">Structure</span>
        <div className="flex gap-1">
          {['drop', 'buildup', 'breakdown', 'main'].map(type => (
            <div key={type} className="flex items-center gap-0.5">
              <div className={cn('w-2 h-2 rounded-sm', getSectionColor(type))} />
              <span className="text-[10px] text-muted-foreground capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="relative h-4 bg-muted/50 rounded overflow-hidden">
        {/* Intro */}
        {analysis.introEnd && analysis.introEnd > 0 && (
          <div
            className="absolute h-full bg-slate-400/50"
            style={{
              left: '0%',
              width: `${(analysis.introEnd / duration) * 100}%`
            }}
          />
        )}

        {/* Sections */}
        {structure.sections.map((section, idx) => (
          <TooltipProvider key={idx}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className={cn('absolute h-full', getSectionColor(section.type))}
                  style={{
                    left: `${(section.start / duration) * 100}%`,
                    width: `${((section.end - section.start) / duration) * 100}%`,
                    opacity: 0.8
                  }}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p className="capitalize">{section.type}</p>
                <p className="text-xs text-muted-foreground">
                  {formatTime(section.start)} - {formatTime(section.end)}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}

        {/* Outro */}
        {analysis.outroStart && (
          <div
            className="absolute h-full bg-slate-400/50"
            style={{
              left: `${(analysis.outroStart / duration) * 100}%`,
              width: `${((duration - analysis.outroStart) / duration) * 100}%`
            }}
          />
        )}
      </div>

      {/* Time markers */}
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-muted-foreground">0:00</span>
        {analysis.introEnd && (
          <span className="text-[10px] text-muted-foreground">
            Intro: {formatTime(analysis.introEnd)}
          </span>
        )}
        {analysis.outroStart && (
          <span className="text-[10px] text-muted-foreground">
            Outro: {formatTime(analysis.outroStart)}
          </span>
        )}
        <span className="text-[10px] text-muted-foreground">{formatTime(duration)}</span>
      </div>
    </div>
  );
}

/**
 * Enhanced track analysis display with expandable details
 */
export function TrackAnalysisCard({ analysis, duration }: TrackAnalysisCardProps) {
  const [expanded, setExpanded] = useState(false);

  const bpmConf = getConfidenceBadge(analysis.bpmConfidence);
  const keyConf = getConfidenceBadge(analysis.keyConfidence);

  return (
    <div className={cn(
      'rounded-lg border bg-card/50 transition-all',
      expanded ? 'p-3 min-w-[320px]' : 'p-2'
    )}>
      {/* Compact view - always visible */}
      <div className="flex items-center gap-4">
        {/* BPM */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <Gauge className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm font-semibold">{Math.round(analysis.bpm)}</span>
                </div>
                <div className="text-[10px] text-muted-foreground">BPM</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>BPM: {analysis.bpm.toFixed(1)}</p>
              <p className="text-xs">Confidence: {Math.round(analysis.bpmConfidence * 100)}%</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Key/Camelot */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <Music2 className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm font-semibold">{analysis.camelot}</span>
                </div>
                <div className="text-[10px] text-muted-foreground">{analysis.key}</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Key: {analysis.key}</p>
              <p>Camelot: {analysis.camelot}</p>
              <p className="text-xs">Confidence: {Math.round(analysis.keyConfidence * 100)}%</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Energy */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <div className={cn('w-2 h-2 rounded-full', getEnergyColor(Math.min(1, analysis.energy)))} />
                  <span className="text-sm font-semibold">
                    {Math.round(Math.min(1, analysis.energy) * 100)}%
                  </span>
                </div>
                <div className="text-[10px] text-muted-foreground">Energy</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Energy Level: {Math.round(Math.min(1, analysis.energy) * 100)}%</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Danceability (compact) */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <Zap className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm font-semibold">
                    {Math.round(Math.min(1, analysis.danceability) * 100)}%
                  </span>
                </div>
                <div className="text-[10px] text-muted-foreground">Dance</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Danceability: {Math.round(Math.min(1, analysis.danceability) * 100)}%</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Loudness (compact) */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <Volume2 className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm font-semibold">
                    {analysis.loudness.toFixed(1)}
                  </span>
                </div>
                <div className="text-[10px] text-muted-foreground">dB</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Loudness: {analysis.loudness.toFixed(2)} dB</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Expand button */}
        {duration && analysis.structureJson && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 space-y-3">
          {/* Confidence badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">BPM:</span>
              <Badge variant={bpmConf.variant} className="text-[10px] h-4">
                {bpmConf.label} ({Math.round(analysis.bpmConfidence * 100)}%)
              </Badge>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Key:</span>
              <Badge variant={keyConf.variant} className="text-[10px] h-4">
                {keyConf.label} ({Math.round(analysis.keyConfidence * 100)}%)
              </Badge>
            </div>
          </div>

          {/* Bars */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-xs text-muted-foreground">Energy</span>
              <MiniBar value={analysis.energy} color={getEnergyColor(analysis.energy)} label="Energy" />
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Danceability</span>
              <MiniBar value={analysis.danceability} color={getDanceabilityColor(analysis.danceability)} label="Danceability" />
            </div>
          </div>

          {/* Structure timeline */}
          {duration && <StructureTimeline analysis={analysis} duration={duration} />}
        </div>
      )}
    </div>
  );
}
