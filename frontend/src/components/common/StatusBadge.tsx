import { CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type Status = 'online' | 'offline' | 'loading' | 'warning';

interface StatusBadgeProps extends Omit<BadgeProps, 'variant'> {
  status: Status;
  label?: string;
  showIcon?: boolean;
}

/**
 * StatusBadge Component
 * 
 * Badge with status indicator (online/offline/loading/warning).
 * Displays appropriate icon and color.
 */
export function StatusBadge({
  status,
  label,
  showIcon = true,
  className,
  ...props
}: StatusBadgeProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'online':
        return {
          icon: CheckCircle2,
          variant: 'default' as const,
          text: label || 'Online',
          color: 'text-green-600',
        };
      case 'offline':
        return {
          icon: XCircle,
          variant: 'destructive' as const,
          text: label || 'Offline',
          color: 'text-red-600',
        };
      case 'loading':
        return {
          icon: Loader2,
          variant: 'secondary' as const,
          text: label || 'Loading',
          color: 'text-blue-600',
          animate: true,
        };
      case 'warning':
        return {
          icon: AlertCircle,
          variant: 'outline' as const,
          text: label || 'Warning',
          color: 'text-yellow-600',
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn('gap-1.5', className)} {...props}>
      {showIcon && (
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            config.color,
            config.animate && 'animate-spin'
          )}
        />
      )}
      <span>{config.text}</span>
    </Badge>
  );
}

