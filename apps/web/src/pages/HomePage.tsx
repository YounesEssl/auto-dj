import { Link } from 'react-router-dom';
import { Music2, Zap, Sparkles, Download } from 'lucide-react';

import { Button } from '@autodj/ui';

/**
 * Landing page with feature highlights
 */
export function HomePage() {
  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <section className="w-full py-12 md:py-24 lg:py-32">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center space-y-4 text-center">
            <div className="space-y-2">
              <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl lg:text-6xl">
                AI-Powered DJ Mix Generation
              </h1>
              <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl">
                Upload your tracks, let AI analyze and mix them into a seamless DJ set.
                Professional transitions, harmonic mixing, and beat-matched perfection.
              </p>
            </div>
            <div className="space-x-4">
              <Link to="/projects/new">
                <Button size="lg">
                  Start Mixing
                  <Zap className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button variant="outline" size="lg">
                  View Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="w-full py-12 md:py-24 bg-muted/50">
        <div className="container px-4 md:px-6">
          <h2 className="text-2xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid gap-8 md:grid-cols-3">
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="rounded-full bg-primary/10 p-4">
                <Music2 className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold">Upload Tracks</h3>
              <p className="text-muted-foreground">
                Upload 10-50 audio tracks in MP3 or WAV format. Our system accepts
                tracks of any genre.
              </p>
            </div>
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="rounded-full bg-primary/10 p-4">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold">AI Analysis</h3>
              <p className="text-muted-foreground">
                Advanced algorithms detect BPM, key, energy, and structure. Tracks are
                ordered using Camelot wheel compatibility.
              </p>
            </div>
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="rounded-full bg-primary/10 p-4">
                <Download className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold">Download Mix</h3>
              <p className="text-muted-foreground">
                Get a professionally mixed DJ set with smooth transitions between
                every track. Ready to play anywhere.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
