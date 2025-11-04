/**
 * Skip to Content Component
 * 
 * Accessibility feature that allows keyboard users to skip navigation
 * and jump directly to main content.
 * 
 * WCAG 2.1 AA Compliance:
 * - Provides bypass mechanism for repeated content
 * - Visible on focus for keyboard navigation
 * - Hidden from view when not focused
 * 
 * Usage:
 * Place at the very top of the app, before any other content.
 */
export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
    >
      Skip to main content
    </a>
  );
}

