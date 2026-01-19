import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Trash2, ArrowLeftRight, Wand2, AlertTriangle, RefreshCw } from 'lucide-react';

import { Button, Card, CardContent } from '@autodj/ui';
import { useDraftStore } from '@/stores/draftStore';
import { useDraftProgress } from '@/hooks/useDraftProgress';
import { draftsService } from '@/services/drafts.service';
import { TrackSlot } from '@/components/draft/TrackSlot';
import { CompatibilityCard } from '@/components/draft/CompatibilityCard';
import { DraftProgress } from '@/components/draft/DraftProgress';
import { DraftPlayer } from '@/components/draft/DraftPlayer';

/**
 * Draft detail page for managing 2-track transitions
 */
export function DraftPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentDraft, isLoading, fetchDraft, deleteDraft, updateCurrentDraft } = useDraftStore();
  const { progress, error: wsError, connect, disconnect } = useDraftProgress(id!);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (id) {
      fetchDraft(id);
      connect();
    }
    return () => disconnect();
  }, [id, fetchDraft, connect, disconnect]);

  const handleDelete = async () => {
    if (!id) return;
    if (!confirm('Are you sure you want to delete this draft?')) return;

    try {
      await deleteDraft(id);
      toast.success('Draft deleted');
      navigate('/drafts');
    } catch {
      toast.error('Failed to delete draft');
    }
  };

  const handleUploadTrack = async (slot: 'A' | 'B', file: File) => {
    if (!id) return;
    try {
      await draftsService.uploadTrack(id, slot, file);
      toast.success(`Track uploaded to slot ${slot}`);
      fetchDraft(id); // Refresh to get updated draft
    } catch {
      toast.error('Failed to upload track');
    }
  };

  const handleRemoveTrack = async (slot: 'A' | 'B') => {
    if (!id) return;
    try {
      await draftsService.removeTrack(id, slot);
      toast.success(`Track removed from slot ${slot}`);
      fetchDraft(id);
    } catch {
      toast.error('Failed to remove track');
    }
  };

  const handleSwapTracks = async () => {
    if (!id) return;
    try {
      const updatedDraft = await draftsService.swapTracks(id);
      updateCurrentDraft(updatedDraft);
      toast.success('Tracks swapped');
    } catch {
      toast.error('Failed to swap tracks');
    }
  };

  const handleGenerateTransition = async () => {
    if (!id) return;
    setIsGenerating(true);
    try {
      await draftsService.generateTransition(id);
      toast.success('Transition generation started');
      fetchDraft(id);
    } catch {
      toast.error('Failed to start transition generation');
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading || !currentDraft) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const hasTrackA = !!currentDraft.trackA;
  const hasTrackB = !!currentDraft.trackB;
  const hasBothTracks = hasTrackA && hasTrackB;
  const bothAnalyzed = hasBothTracks &&
    currentDraft.trackA?.analysis &&
    currentDraft.trackB?.analysis;
  const isCompleted = currentDraft.transitionStatus === 'COMPLETED';
  const isProcessing = currentDraft.transitionStatus === 'PROCESSING' ||
    currentDraft.status === 'GENERATING';
  // Can generate if both tracks are analyzed and not already processing/completed
  const canGenerate = bothAnalyzed && !isProcessing && !isCompleted;

  // BPM warning
  const showBpmWarning = bothAnalyzed &&
    currentDraft.bpmDifference !== null &&
    currentDraft.bpmDifference > 8;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{currentDraft.name}</h1>
          <p className="text-muted-foreground">
            Upload two tracks and generate a professional transition.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="destructive" size="icon" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {(currentDraft.errorMessage || wsError) && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{currentDraft.errorMessage || wsError}</p>
          </CardContent>
        </Card>
      )}

      {/* BPM Warning */}
      {showBpmWarning && (
        <Card className="border-yellow-500 bg-yellow-500/10">
          <CardContent className="pt-6 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            <p className="text-yellow-700 dark:text-yellow-400">
              BPM difference is {currentDraft.bpmDifference?.toFixed(1)}% - transition will use crossfade mode instead of stems.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Track Slots */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TrackSlot
          slot="A"
          track={currentDraft.trackA}
          onUpload={(file) => handleUploadTrack('A', file)}
          onRemove={() => handleRemoveTrack('A')}
          disabled={isProcessing}
        />

        {/* Swap Button (centered) */}
        {hasBothTracks && (
          <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
            <Button
              variant="outline"
              size="icon"
              onClick={handleSwapTracks}
              disabled={isProcessing}
              className="rounded-full"
            >
              <ArrowLeftRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        <TrackSlot
          slot="B"
          track={currentDraft.trackB}
          onUpload={(file) => handleUploadTrack('B', file)}
          onRemove={() => handleRemoveTrack('B')}
          disabled={isProcessing}
        />
      </div>

      {/* Mobile Swap Button */}
      {hasBothTracks && (
        <div className="flex justify-center lg:hidden">
          <Button
            variant="outline"
            onClick={handleSwapTracks}
            disabled={isProcessing}
          >
            <ArrowLeftRight className="mr-2 h-4 w-4" />
            Swap Tracks
          </Button>
        </div>
      )}

      {/* Compatibility Card */}
      {bothAnalyzed && (
        <CompatibilityCard
          compatibilityScore={currentDraft.compatibilityScore}
          harmonicScore={currentDraft.harmonicScore}
          bpmScore={currentDraft.bpmScore}
          energyScore={currentDraft.energyScore}
          bpmDifference={currentDraft.bpmDifference}
        />
      )}

      {/* Progress */}
      {(isProcessing || progress) && (
        <DraftProgress progress={progress} />
      )}

      {/* Generate Button */}
      {canGenerate && (
        <Card>
          <CardContent className="pt-6 text-center">
            <Button
              size="lg"
              onClick={handleGenerateTransition}
              disabled={isGenerating}
            >
              <Wand2 className="mr-2 h-5 w-5" />
              {isGenerating ? 'Starting...' : 'Generate Transition'}
            </Button>
            <p className="text-sm text-muted-foreground mt-2">
              This will create a professional DJ transition between the two tracks.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Player */}
      {isCompleted && (
        <>
          <DraftPlayer
            draftId={id!}
            trackA={currentDraft.trackA!}
            trackB={currentDraft.trackB!}
            transitionDurationMs={currentDraft.transitionDurationMs || 0}
            trackAOutroMs={currentDraft.trackAOutroMs || 0}
            trackBIntroMs={currentDraft.trackBIntroMs || 0}
            transitionMode={currentDraft.transitionMode}
          />
          <Card>
            <CardContent className="pt-6 text-center">
              <Button
                variant="outline"
                onClick={handleGenerateTransition}
                disabled={isGenerating}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                {isGenerating ? 'Regenerating...' : 'Regenerate Transition'}
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
