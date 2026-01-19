import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Loader2, Music2 } from 'lucide-react';

import { Button, Card } from '@autodj/ui';
import { useDraftStore } from '@/stores/draftStore';
import { DraftCard } from '@/components/draft/DraftCard';

/**
 * Page listing all user drafts (2-track transitions)
 */
export function DraftsListPage() {
  const { drafts, isLoading, fetchDrafts } = useDraftStore();

  useEffect(() => {
    fetchDrafts();
  }, [fetchDrafts]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Drafts</h1>
          <p className="text-muted-foreground">
            Create professional transitions between two tracks.
          </p>
        </div>
        <Link to="/drafts/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Draft
          </Button>
        </Link>
      </div>

      {/* Drafts List */}
      {drafts.length === 0 ? (
        <Card className="p-8 text-center">
          <Music2 className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No drafts yet</h3>
          <p className="text-muted-foreground mb-4">
            Create a draft to generate a professional transition between two tracks.
          </p>
          <Link to="/drafts/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Draft
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  );
}
