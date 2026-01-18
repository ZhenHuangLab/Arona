import { Clock, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { IndexStatusEnum } from '@/types/index-status';

interface IndexStatusBadgeProps extends Omit<BadgeProps, 'variant'> {
  status: IndexStatusEnum;
  errorMessage?: string | null;
  showIcon?: boolean;
}

/**
 * Status configuration mapping
 * Eliminates conditional branches - Linus's "good taste" principle
 */
const STATUS_CONFIG = {
  pending: {
    icon: Clock,
    variant: 'outline' as const,
    label: 'Pending',
    color: 'text-gray-600',
  },
  processing: {
    icon: Loader2,
    variant: 'secondary' as const,
    label: 'Processing',
    color: 'text-yellow-600',
    animate: true,
  },
  indexed: {
    icon: CheckCircle2,
    variant: 'default' as const,
    label: 'Indexed',
    color: 'text-green-600',
  },
  failed: {
    icon: XCircle,
    variant: 'destructive' as const,
    label: 'Failed',
    color: 'text-red-600',
  },
} as const;

/**
 * IndexStatusBadge Component
 *
 * Displays document indexing status with color-coded badge and icon.
 *
 * Features:
 * - Color-coded status: pending (gray), processing (yellow), indexed (green), failed (red)
 * - Animated spinner for processing status
 * - Error message display via title attribute for failed status
 *
 * Usage:
 * ```tsx
 * <IndexStatusBadge status="processing" />
 * <IndexStatusBadge status="failed" errorMessage="Parse error" />
 * ```
 */
export function IndexStatusBadge({
  status,
  errorMessage,
  showIcon = true,
  className,
  ...props
}: IndexStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  // Add error message as title for tooltip on failed status
  const title = status === 'failed' && errorMessage ? errorMessage : undefined;

  return (
    <Badge
      variant={config.variant}
      className={cn('gap-1.5', className)}
      title={title}
      {...props}
    >
      {showIcon && (
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            config.color,
            'animate' in config && config.animate && 'animate-spin'
          )}
        />
      )}
      <span>{config.label}</span>
    </Badge>
  );
}
