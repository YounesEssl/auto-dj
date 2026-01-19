import * as React from 'react';
import { cn } from '../lib/utils';

interface SliderProps {
  value: number[];
  max?: number;
  min?: number;
  step?: number;
  onValueChange?: (value: number[]) => void;
  className?: string;
  disabled?: boolean;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ value, max = 100, min = 0, step = 1, onValueChange, className, disabled }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = parseFloat(e.target.value);
      onValueChange?.([newValue]);
    };

    // Debug logging
    if (value === undefined || value === null) {
      console.warn('[Slider] value is undefined/null:', { value, max, min });
    }

    const currentValue = value?.[0] ?? 0;
    const percentage = (currentValue - min) / (max - min) * 100;

    return (
      <div className={cn('relative flex w-full touch-none select-none items-center', className)}>
        <div className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
          <div
            className="absolute h-full bg-primary"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <input
          ref={ref}
          type="range"
          min={min}
          max={max}
          step={step}
          value={currentValue}
          onChange={handleChange}
          disabled={disabled}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />
      </div>
    );
  }
);
Slider.displayName = 'Slider';

export { Slider };
