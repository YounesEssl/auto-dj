import { useEffect, useRef, useCallback, useState, FormEvent } from 'react';
import { MessageSquare, Send, X, Trash2, Sparkles, Check, Loader2, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { cn } from '@autodj/ui';
import { Button } from '@autodj/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@autodj/ui';
import { useChatStore } from '@/stores/chatStore';
import { useProjectStore } from '@/stores/projectStore';
import { socketService, type ChatResponseEvent } from '@/services/socket.service';
import type { Transition } from '@/services/projects.service';

interface ChatProps {
  projectId: string;
}

/**
 * AI Chat assistant for track reordering
 */
export function Chat({ projectId }: ChatProps) {
  const {
    messages,
    isOpen,
    isLoading,
    openChat,
    closeChat,
    sendMessage,
    handleChatResponse,
    loadHistory,
    clearHistory,
    setProjectId,
  } = useChatStore();

  const { updateCurrentProject } = useProjectStore();
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Set project ID when component mounts
  useEffect(() => {
    setProjectId(projectId);
    loadHistory(projectId);
  }, [projectId, setProjectId, loadHistory]);

  // Subscribe to chat responses
  useEffect(() => {
    const handleResponse = (response: ChatResponseEvent) => {
      handleChatResponse(response);

      // If there's project data with new order, update the project store directly
      // This avoids a full refetch which can cause react-dnd issues
      if (response.projectData) {
        updateCurrentProject({
          orderedTracks: response.projectData.orderedTracks,
          transitions: response.projectData.transitions as Transition[],
          averageMixScore: response.projectData.averageMixScore,
        });
      }
    };

    socketService.onChatResponse(handleResponse);

    return () => {
      socketService.offChatResponse(handleResponse);
    };
  }, [handleChatResponse, updateCurrentProject, projectId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!inputValue.trim() || isLoading) return;

      const message = inputValue;
      setInputValue('');
      await sendMessage(projectId, message);
    },
    [inputValue, isLoading, projectId, sendMessage]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e as unknown as FormEvent);
      }
    },
    [handleSubmit]
  );

  const handleClearHistory = useCallback(() => {
    clearHistory(projectId);
  }, [clearHistory, projectId]);

  return (
    <TooltipProvider>
      {/* Toggle Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-24 right-6 z-50"
          >
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={openChat}
                  size="icon"
                  className="rounded-full !w-14 !h-14 shadow-lg bg-gradient-to-br from-primary to-accent hover:from-primary/90 hover:to-accent/90 btn-glow"
                >
                  <MessageSquare className="!w-6 !h-6 text-white" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p className="font-medium">Assistant IA</p>
                <p className="text-xs text-muted-foreground">Demande-moi de reordonner tes tracks</p>
              </TooltipContent>
            </Tooltip>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed bottom-24 right-6 z-50 w-[400px] h-[500px] max-h-[70vh] flex flex-col rounded-2xl shadow-2xl border border-border/50 bg-card/95 backdrop-blur-xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-gradient-to-r from-primary/10 to-accent/10">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Assistant DJ</h3>
                  <p className="text-xs text-muted-foreground">Reordonne tes tracks avec l'IA</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                      onClick={handleClearHistory}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Effacer l'historique</TooltipContent>
                </Tooltip>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={closeChat}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-studio">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-8">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mb-4">
                    <Sparkles className="w-8 h-8 text-primary" />
                  </div>
                  <h4 className="font-medium mb-2">Comment puis-je t'aider ?</h4>
                  <p className="text-sm text-muted-foreground max-w-[280px] mb-4">
                    Demande-moi de reorganiser tes tracks selon tes preferences
                  </p>
                  <div className="space-y-2 w-full">
                    <SuggestionChip
                      onClick={() => setInputValue('Je veux une montee progressive en energie')}
                    >
                      Montee progressive en energie
                    </SuggestionChip>
                    <SuggestionChip
                      onClick={() => setInputValue("Mets les morceaux les plus energiques au milieu")}
                    >
                      Peak au milieu du set
                    </SuggestionChip>
                    <SuggestionChip
                      onClick={() => setInputValue('Optimise les transitions harmoniques')}
                    >
                      Optimiser les harmoniques
                    </SuggestionChip>
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-border/50">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Dis-moi comment organiser ton set..."
                    className="w-full resize-none rounded-xl border border-border/50 bg-muted/30 px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent placeholder:text-muted-foreground/60"
                    rows={1}
                    disabled={isLoading}
                  />
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="submit"
                      size="icon"
                      disabled={!inputValue.trim() || isLoading}
                      className="h-11 w-11 rounded-xl bg-gradient-to-br from-primary to-accent hover:from-primary/90 hover:to-accent/90 disabled:opacity-50"
                    >
                      {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Send className="w-5 h-5" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Envoyer</TooltipContent>
                </Tooltip>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </TooltipProvider>
  );
}

/**
 * Individual chat message component
 */
function ChatMessage({ message }: { message: { id: string; role: 'user' | 'assistant'; content: string; isLoading?: boolean; changesMade?: string[]; newOrder?: string[] | null } }) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2.5',
          isUser
            ? 'bg-gradient-to-br from-primary to-accent text-primary-foreground'
            : 'bg-muted/50 border border-border/50'
        )}
      >
        {message.isLoading ? (
          <div className="flex items-center gap-2 py-1">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm text-muted-foreground">En train de reflechir...</span>
          </div>
        ) : (
          <>
            <div className={cn('text-sm whitespace-pre-wrap', isUser ? '' : 'text-foreground')}>
              {message.content}
            </div>

            {/* Changes Made */}
            {message.changesMade && message.changesMade.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/30">
                <p className="text-xs font-medium mb-2 flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-success" />
                  Modifications appliquees
                </p>
                <ul className="space-y-1">
                  {message.changesMade.map((change, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <ChevronRight className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      <span>{change}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}

/**
 * Suggestion chip component
 */
function SuggestionChip({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-2.5 rounded-xl bg-muted/30 border border-border/50 text-sm text-muted-foreground hover:bg-muted/50 hover:text-foreground hover:border-primary/30 transition-all duration-200"
    >
      {children}
    </button>
  );
}
