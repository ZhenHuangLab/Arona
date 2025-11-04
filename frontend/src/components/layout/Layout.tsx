import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { ModeSwitch } from './ModeSwitch';
import { SkipToContent } from '@/components/common';

/**
 * Layout Component
 *
 * Main layout wrapper for all pages
 *
 * Structure:
 * - Skip to content link (accessibility)
 * - Header (navigation, settings)
 * - Mode switch (Chat/Documents navigation)
 * - Main content area (Outlet for routes)
 *
 * Accessibility:
 * - Skip to content link for keyboard users
 * - Semantic HTML with <main> element
 * - Proper heading hierarchy
 */
export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background">
      <SkipToContent />
      <Header />
      <ModeSwitch />
      <main id="main-content" tabIndex={-1} className="focus:outline-none">
        <Outlet />
      </main>
    </div>
  );
};

