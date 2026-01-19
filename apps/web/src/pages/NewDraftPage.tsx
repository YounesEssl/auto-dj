import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { Button, Card, CardHeader, CardTitle, CardContent, Input, Label } from '@autodj/ui';
import { draftsService } from '@/services/drafts.service';

const createDraftSchema = z.object({
  name: z.string().max(200, 'Name is too long').optional(),
});

type CreateDraftForm = z.infer<typeof createDraftSchema>;

/**
 * Page for creating a new draft (2-track transition)
 */
export function NewDraftPage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateDraftForm>({
    resolver: zodResolver(createDraftSchema),
  });

  const onSubmit = async (data: CreateDraftForm) => {
    setIsLoading(true);
    try {
      const draft = await draftsService.create(data.name);
      toast.success('Draft created successfully');
      navigate(`/drafts/${draft.id}`);
    } catch (error) {
      toast.error('Failed to create draft');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Create New Draft</h1>
        <p className="text-muted-foreground">
          Create a professional transition between two tracks.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Draft Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Draft Name (optional)</Label>
              <Input
                id="name"
                placeholder="e.g., Track A to Track B Transition"
                {...register('name')}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="flex justify-end space-x-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate('/drafts')}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create Draft'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
