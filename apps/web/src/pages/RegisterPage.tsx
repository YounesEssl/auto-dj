import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Loader2, Zap, ArrowRight, Check } from 'lucide-react';

import { Button, Card, CardHeader, CardContent, Input, Label } from '@autodj/ui';
import { useAuthStore } from '@/stores/authStore';

const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').optional(),
  email: z.string().email('Please enter a valid email'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Za-z]/, 'Password must contain at least one letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

/**
 * Registration page - Midnight Studio design
 */
export function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch('password', '');
  const hasMinLength = password.length >= 8;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    try {
      await registerUser(data.email, data.password, data.name);
      toast.success('Account created successfully!');
      navigate('/studio');
    } catch {
      toast.error('Failed to create account. Email may already be registered.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-accent/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:48px_48px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 bg-primary rounded flex items-center justify-center shadow-[0_0_25px_rgba(251,191,36,0.4)] group-hover:shadow-[0_0_35px_rgba(251,191,36,0.6)] transition-shadow">
              <Zap size={22} className="text-primary-foreground fill-current" />
            </div>
            <span className="text-lg font-bold tracking-tight uppercase">
              AutoDJ<span className="text-primary font-mono">.io</span>
            </span>
          </Link>
        </div>

        <Card className="studio-panel border-border/50 bg-card/60 backdrop-blur-xl">
          <CardHeader className="text-center space-y-2 pb-2">
            <div className="flex items-center justify-center gap-2 mb-2">
              <div className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_8px_hsl(185,70%,45%)]" />
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                New Registration
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight">Create an account</h1>
            <p className="text-sm text-muted-foreground">
              Join the studio and start mixing with AI
            </p>
          </CardHeader>

          <CardContent className="pt-6">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-[11px] uppercase tracking-widest text-muted-foreground font-medium">
                  Display Name <span className="text-muted-foreground/50">(Optional)</span>
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="DJ Nova"
                  className="h-11 bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 placeholder:text-muted-foreground/40"
                  {...register('name')}
                />
                {errors.name && (
                  <p className="text-[11px] text-destructive flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-destructive" />
                    {errors.name.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-[11px] uppercase tracking-widest text-muted-foreground font-medium">
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  className="h-11 bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 placeholder:text-muted-foreground/40"
                  {...register('email')}
                />
                {errors.email && (
                  <p className="text-[11px] text-destructive flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-destructive" />
                    {errors.email.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-[11px] uppercase tracking-widest text-muted-foreground font-medium">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  className="h-11 bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 placeholder:text-muted-foreground/40"
                  {...register('password')}
                />
                {/* Password requirements */}
                <div className="flex gap-4 pt-1">
                  <span className={`text-[10px] flex items-center gap-1 ${hasMinLength ? 'text-[hsl(142,70%,45%)]' : 'text-muted-foreground/50'}`}>
                    <Check size={10} className={hasMinLength ? 'opacity-100' : 'opacity-30'} />
                    8+ chars
                  </span>
                  <span className={`text-[10px] flex items-center gap-1 ${hasLetter ? 'text-[hsl(142,70%,45%)]' : 'text-muted-foreground/50'}`}>
                    <Check size={10} className={hasLetter ? 'opacity-100' : 'opacity-30'} />
                    Letter
                  </span>
                  <span className={`text-[10px] flex items-center gap-1 ${hasNumber ? 'text-[hsl(142,70%,45%)]' : 'text-muted-foreground/50'}`}>
                    <Check size={10} className={hasNumber ? 'opacity-100' : 'opacity-30'} />
                    Number
                  </span>
                </div>
                {errors.password && (
                  <p className="text-[11px] text-destructive flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-destructive" />
                    {errors.password.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-[11px] uppercase tracking-widest text-muted-foreground font-medium">
                  Confirm Password
                </Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  className="h-11 bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 placeholder:text-muted-foreground/40"
                  {...register('confirmPassword')}
                />
                {errors.confirmPassword && (
                  <p className="text-[11px] text-destructive flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-destructive" />
                    {errors.confirmPassword.message}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full h-11 btn-glow text-[11px] uppercase tracking-widest font-bold"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating Account...
                  </>
                ) : (
                  <>
                    Initialize Account
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <div className="mt-8 pt-6 border-t border-border/30 text-center">
              <span className="text-[11px] text-muted-foreground">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="text-primary hover:text-primary/80 font-medium transition-colors"
                >
                  Sign in
                </Link>
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-[10px] text-muted-foreground/50 font-mono uppercase tracking-wider">
            By signing up, you agree to our Terms of Service
          </p>
        </div>
      </div>
    </div>
  );
}
