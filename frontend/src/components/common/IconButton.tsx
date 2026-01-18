import type { LucideIcon } from 'lucide-react';
import { Button, type ButtonProps } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface IconButtonProps extends Omit<ButtonProps, 'children'> {
  icon: LucideIcon;
  label?: string;
  iconClassName?: string;
}

/**
 * IconButton Component
 *
 * Button with Lucide React icon.
 * Supports all Button variants and sizes.
 */
export function IconButton({
  icon: Icon,
  label,
  iconClassName,
  className,
  ...props
}: IconButtonProps) {
  return (
    <Button className={cn('gap-2', className)} {...props}>
      <Icon className={cn('h-4 w-4', iconClassName)} />
      {label && <span>{label}</span>}
      {!label && <span className="sr-only">{props['aria-label'] || 'Button'}</span>}
    </Button>
  );
}
