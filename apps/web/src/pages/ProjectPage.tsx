import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Download, Play, Trash2, Wand2 } from 'lucide-react';

import { Button, Card, CardHeader, CardTitle, CardContent } from '@autodj/ui';
import { useProjectStore } from '@/stores/projectStore';
import { TrackUploader } from '@/components/tracks/TrackUploader';
import { TrackList } from '@/components/tracks/TrackList';
import { ProjectProgress } from '@/components/project/ProjectProgress';
import { MixScoreCard } from '@/components/project/MixScoreCard';
import { MixPlayer } from '@/components/player/MixPlayer';
import { useJobProgress } from '@/hooks/useJobProgress';
import { projectsService } from '@/services/projects.service';

/**
 * Project detail page with track management
 */
export function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, isLoading, fetchProject, deleteProject } = useProjectStore();
  const { progress, connect, disconnect } = useJobProgress(id!);

  useEffect(() => {
    if (id) {
      fetchProject(id);
      connect();
    }
    return () => disconnect();
  }, [id, fetchProject, connect, disconnect]);

  const handleDelete = async () => {
    if (!id) return;
    if (!confirm('Are you sure you want to delete this project?')) return;

    try {
      await deleteProject(id);
      toast.success('Project deleted');
      navigate('/dashboard');
    } catch {
      toast.error('Failed to delete project');
    }
  };

  const handleGenerateTransitions = async () => {
    if (!id) return;
    try {
      const result = await projectsService.generateTransitions(id);
      toast.success(`Generating ${result.transitionCount} transitions...`);
      fetchProject(id); // Refresh to get updated status
    } catch {
      toast.error('Failed to start transition generation');
    }
  };

  const handleGenerateMix = async () => {
    if (!id) return;
    try {
      await projectsService.generateMix(id);
      toast.success('Mix generation started');
    } catch {
      toast.error('Failed to start mix generation');
    }
  };

  const handleDownload = () => {
    if (!id || !currentProject?.outputFile) return;
    window.open(`/api/v1/projects/${id}/download`, '_blank');
  };

  if (isLoading || !currentProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isProcessing = ['ANALYZING', 'ORDERING', 'MIXING'].includes(currentProject.status);
  const isReady = currentProject.status === 'READY';
  const isCompleted = currentProject.status === 'COMPLETED';
  const isFailed = currentProject.status === 'FAILED';

  const canGenerateMix =
    currentProject.tracks.length >= 2 &&
    currentProject.tracks.every((t) => t.analysis) &&
    ['CREATED', 'READY'].includes(currentProject.status);

  // Check if transitions can be generated (ordered but no audio yet)
  const hasTransitions = currentProject.transitions && currentProject.transitions.length > 0;
  const allTransitionsComplete = hasTransitions && currentProject.transitions.every(t => t.audioStatus === 'COMPLETED');
  const anyTransitionProcessing = hasTransitions && currentProject.transitions.some(t => t.audioStatus === 'PROCESSING');
  const canGenerateTransitions = isReady && hasTransitions && !allTransitionsComplete && !anyTransitionProcessing;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{currentProject.name}</h1>
          <p className="text-muted-foreground">
            {currentProject.tracks.length} track{currentProject.tracks.length !== 1 ? 's' : ''} uploaded
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {isCompleted && (
            <Button onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download Mix
            </Button>
          )}
          {canGenerateTransitions && (
            <Button onClick={handleGenerateTransitions} variant="secondary">
              <Wand2 className="mr-2 h-4 w-4" />
              Generate Transitions
            </Button>
          )}
          {canGenerateMix && (
            <Button onClick={handleGenerateMix}>
              <Play className="mr-2 h-4 w-4" />
              Generate Mix
            </Button>
          )}
          <Button variant="destructive" size="icon" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Progress */}
      {(isProcessing || isReady || progress) && (
        <ProjectProgress project={currentProject} progress={progress} />
      )}

      {/* Error Message */}
      {isFailed && currentProject.errorMessage && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{currentProject.errorMessage}</p>
          </CardContent>
        </Card>
      )}

      {/* Track Upload */}
      {!isProcessing && !isCompleted && !isReady && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Tracks</CardTitle>
          </CardHeader>
          <CardContent>
            <TrackUploader projectId={id!} />
          </CardContent>
        </Card>
      )}

      {/* Mix Score Card */}
      {(isReady || isCompleted) && currentProject.averageMixScore !== null && (
        <MixScoreCard project={currentProject} />
      )}

      {/* Mix Player */}
      {isCompleted && (
        <MixPlayer
          projectId={id!}
          onRefresh={() => fetchProject(id!)}
        />
      )}

      {/* Track List */}
      <Card>
        <CardHeader>
          <CardTitle>
            {currentProject.orderedTracks.length > 0 ? 'Track Order' : 'Tracks'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <TrackList
            tracks={currentProject.tracks}
            projectId={id!}
            orderedTrackIds={currentProject.orderedTracks}
            transitions={currentProject.transitions}
          />
        </CardContent>
      </Card>
    </div>
  );
}
