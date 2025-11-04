import React from 'react';
import { cn } from '../../lib/utils';

/**
 * Skeleton Props
 */
interface SkeletonProps {
  className?: string;
}

/**
 * Base Skeleton Component
 * 
 * Displays an animated skeleton placeholder for loading states
 */
export const Skeleton: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-gray-200',
        className
      )}
    />
  );
};

/**
 * Message Skeleton
 * 
 * Skeleton loader for chat messages
 */
export const MessageSkeleton: React.FC<{ isUser?: boolean }> = ({ isUser = false }) => {
  return (
    <div className={cn('flex gap-3 p-3', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('space-y-2', isUser ? 'max-w-[80%]' : 'max-w-[80%]')}>
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-4 w-32" />
      </div>
    </div>
  );
};

/**
 * Document Card Skeleton
 * 
 * Skeleton loader for document cards
 */
export const DocumentCardSkeleton: React.FC = () => {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-5 w-16" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-24" />
      </div>
    </div>
  );
};

/**
 * Graph Stats Skeleton
 * 
 * Skeleton loader for graph statistics
 */
export const GraphStatsSkeleton: React.FC = () => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-16" />
        </div>
      ))}
    </div>
  );
};

/**
 * Settings Section Skeleton
 * 
 * Skeleton loader for settings sections
 */
export const SettingsSectionSkeleton: React.FC = () => {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-32" />
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
};

