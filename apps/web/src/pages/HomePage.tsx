import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Music2, Sparkles, Download, Zap, Play, ChevronRight, Activity } from 'lucide-react';
import { Button } from '@autodj/ui';

/**
 * Landing page with Midnight Studio design - professional audio studio aesthetic
 */
export function HomePage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 selection:text-primary overflow-x-hidden">
      {/* Studio Background Grid */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-20 bg-[radial-gradient(circle_at_center,rgba(38,195,255,0.08)_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="fixed inset-0 z-0 pointer-events-none opacity-10 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:128px_128px]" />

      {/* Decorative VU Meter Sidebar (Hardware feel) */}
      <div className="fixed left-4 top-1/2 -translate-y-1/2 flex flex-col gap-1 z-50 hidden xl:flex">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className={`w-1 h-3 rounded-full transition-all duration-500 ${i < 8 ? 'bg-primary/40' : i < 10 ? 'bg-primary' : 'bg-accent'}`}
            style={{ opacity: 0.3 + Math.random() * 0.7 }}
          />
        ))}
        <span className="[writing-mode:vertical-lr] text-[8px] uppercase tracking-widest text-muted-foreground mt-4 font-mono">Input Gain</span>
      </div>

      <main className="relative z-10">
        {/* HERO SECTION */}
        <section className="relative pt-24 pb-32 px-6 flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 mb-8"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-accent">Engine v2.4 Online</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="max-w-3xl text-3xl md:text-5xl lg:text-6xl font-black tracking-tight leading-[1.1] mb-6 text-glow"
          >
            THE ART OF THE <span className="text-primary italic">PERFECT</span> TRANSITION, <br />
            POWERED BY INTELLIGENCE.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-xl text-sm md:text-base text-muted-foreground leading-relaxed mb-10 font-light"
          >
            Automate the complexity of harmonic mixing, BPM matching, and energy flow.
            AutoDJ analyzes your library to craft professional-grade studio mixes in seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center gap-4"
          >
            <Link to="/studio">
              <Button size="lg" className="btn-glow h-11 px-8 text-xs uppercase tracking-widest font-bold min-w-[180px]">
                Open Studio
                <Zap className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link to="/studio">
              <Button variant="ghost" size="lg" className="h-11 px-8 text-xs uppercase tracking-widest font-bold text-muted-foreground hover:text-foreground">
                Start Mixing <ChevronRight size={14} className="ml-1" />
              </Button>
            </Link>
          </motion.div>

          {/* Hero Visual Component: Animated Waveform/Mixer Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="mt-20 w-full max-w-4xl studio-panel p-1 rounded-xl gradient-border"
          >
            <div className="bg-background/80 rounded-[10px] p-6 flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-border/50 pb-4">
                <div className="flex gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[9px] uppercase tracking-tighter text-muted-foreground">Deck A</span>
                    <span className="text-xs font-mono text-primary uppercase">Current Master</span>
                  </div>
                  <div className="h-8 w-px bg-border" />
                  <div className="flex flex-col gap-1">
                    <span className="text-[9px] uppercase tracking-tighter text-muted-foreground">BPM</span>
                    <span className="text-xs font-mono">126.00</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="w-12 h-6 rounded bg-muted flex items-center justify-center">
                    <div className="w-1 h-1 rounded-full bg-accent animate-pulse" />
                  </div>
                  <Activity size={18} className="text-muted-foreground" />
                </div>
              </div>

              <div className="h-24 relative flex items-end gap-[2px]">
                {[...Array(60)].map((_, i) => (
                  <motion.div
                    key={i}
                    animate={{
                      height: [
                        `${20 + Math.random() * 60}%`,
                        `${10 + Math.random() * 80}%`,
                        `${20 + Math.random() * 60}%`
                      ]
                    }}
                    transition={{
                      repeat: Infinity,
                      duration: 1.5 + Math.random(),
                      ease: "easeInOut"
                    }}
                    className={`flex-1 min-w-[4px] rounded-t-sm ${i > 25 && i < 35 ? 'bg-primary shadow-[0_0_8px_rgba(251,191,36,0.3)]' : 'bg-muted-foreground/20'}`}
                  />
                ))}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-10 h-10 rounded-full bg-background border border-primary/50 flex items-center justify-center shadow-2xl backdrop-blur-sm">
                    <Play size={16} className="text-primary fill-current ml-0.5" />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </section>

        {/* HOW IT WORKS SECTION */}
        <section id="technology" className="py-24 px-6 bg-muted/30">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
              <div className="max-w-md">
                <span className="text-[10px] uppercase tracking-[0.3em] font-bold text-primary mb-4 block">Workflow</span>
                <h2 className="text-2xl font-bold tracking-tight uppercase italic">Studio Precision. AI Scale.</h2>
              </div>
              <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
                Our algorithm mimics the decision-making of world-class DJs, analyzing phase, frequency, and harmonic compatibility.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Step 1 */}
              <div className="studio-panel group hover:border-primary/50 transition-colors p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 font-mono text-3xl opacity-5 italic group-hover:opacity-10 transition-opacity">01</div>
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center mb-6 group-hover:text-primary transition-colors border border-border">
                  <Music2 size={20} />
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wider mb-3">Upload Tracks</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Drop your high-res WAV or MP3 files. Our engine handles multi-track ingestion with instant peak-volume normalization.
                </p>
                <div className="mt-6 h-1 w-0 group-hover:w-full bg-primary transition-all duration-500 rounded-full" />
              </div>

              {/* Step 2 */}
              <div className="studio-panel group hover:border-primary/50 transition-colors p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 font-mono text-3xl opacity-5 italic group-hover:opacity-10 transition-opacity">02</div>
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center mb-6 group-hover:text-accent transition-colors border border-border">
                  <Sparkles size={20} />
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wider mb-3">AI Analysis</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Deep scanning for BPM, Camelot keys, and energy markers. The AI identifies optimal "intro/outro" zones for seamless layering.
                </p>
                <div className="mt-6 h-1 w-0 group-hover:w-full bg-accent transition-all duration-500 rounded-full" />
              </div>

              {/* Step 3 */}
              <div className="studio-panel group hover:border-primary/50 transition-colors p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 font-mono text-3xl opacity-5 italic group-hover:opacity-10 transition-opacity">03</div>
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center mb-6 group-hover:text-primary transition-colors border border-border">
                  <Download size={20} />
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wider mb-3">Export Mix</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Generate your continuous mix with automated EQ carving. Download in lossless formats with a full timestamped tracklist.
                </p>
                <div className="mt-6 h-1 w-0 group-hover:w-full bg-primary transition-all duration-500 rounded-full" />
              </div>
            </div>
          </div>
        </section>

        {/* Technical Specs / VU Strip */}
        <section className="border-y border-border py-12 px-6 flex flex-wrap justify-around items-center gap-8 bg-black/40">
          <div className="flex flex-col gap-1">
            <span className="text-[8px] uppercase tracking-widest text-muted-foreground">latency</span>
            <span className="text-xs font-mono font-bold">&lt; 140ms</span>
          </div>
          <div className="h-10 w-px bg-border hidden sm:block" />
          <div className="flex flex-col gap-1">
            <span className="text-[8px] uppercase tracking-widest text-muted-foreground">engine status</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent shadow-[0_0_8px_rgba(38,195,255,0.6)]" />
              <span className="text-xs font-mono font-bold">NOMINAL</span>
            </div>
          </div>
          <div className="h-10 w-px bg-border hidden sm:block" />
          <div className="flex flex-col gap-1">
            <span className="text-[8px] uppercase tracking-widest text-muted-foreground">processing power</span>
            <div className="vu-meter h-1.5 w-32 rounded-full overflow-hidden bg-muted">
               <div className="h-full w-4/5 bg-primary shadow-[0_0_10px_rgba(251,191,36,0.4)]" />
            </div>
          </div>
          <div className="h-10 w-px bg-border hidden sm:block" />
          <div className="flex flex-col gap-1">
            <span className="text-[8px] uppercase tracking-widest text-muted-foreground">harmonic engine</span>
            <span className="text-xs font-mono font-bold">V-PHASE 2.0</span>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="relative z-10 py-12 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2 grayscale opacity-50">
            <div className="w-5 h-5 bg-foreground rounded-sm flex items-center justify-center">
              <Zap size={12} className="text-background fill-current" />
            </div>
            <span className="text-xs font-bold tracking-tighter uppercase">AutoDJ</span>
          </div>

          <div className="flex gap-8">
            <a href="#" className="text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground">Terms</a>
            <a href="#" className="text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground">Privacy</a>
            <a href="#" className="text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground">API</a>
            <a href="#" className="text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground">Contact</a>
          </div>

          <p className="text-[10px] text-muted-foreground font-mono">
            © {new Date().getFullYear()} AUTODJ SYSTEMS. ALL RIGHTS RESERVED.
          </p>
        </div>
      </footer>
    </div>
  );
}
