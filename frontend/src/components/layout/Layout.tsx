import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppShell } from './AppShell';
import { SkipToContent } from '@/components/common';

/**
 * Layout Component
 *
 * Main layout wrapper for all pages using the new AppShell layout.
 *
 * Structure:
 * - Skip to content link (accessibility)
 * - AppShell (Sidebar + Main content area)
 *
 * Accessibility:
 * - Skip to content link for keyboard users
 * - Semantic HTML with <main> element inside AppShell
 * - Proper heading hierarchy
 */
export const Layout: React.FC = () => {
  return (
    <>
      <SkipToContent />
      <AppShell>
        <Outlet />
      </AppShell>
    </>
  );
};
