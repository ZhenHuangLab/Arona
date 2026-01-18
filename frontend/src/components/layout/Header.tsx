import { SettingsModal } from './SettingsModal';
import { ThemeToggle } from '@/components/theme';

/**
 * Header Component
 *
 * Top navigation bar with logo/title, theme toggle, and settings button.
 * Mode switching is handled by ModeSwitch component in the main layout.
 *
 * Accessibility:
 * - Semantic HTML with <header> element
 * - Sticky positioning for persistent navigation
 * - Responsive padding and spacing
 */
export function Header() {
  return (
    <header className="border-b bg-background sticky top-0 z-50 shadow-sm">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">A</span>
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Arona</h1>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <SettingsModal />
          </div>
        </div>
      </div>
    </header>
  );
}
