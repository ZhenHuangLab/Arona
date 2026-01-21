import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useSettingsStore } from '@/store';

type Theme = 'light' | 'dark' | 'system';

interface ThemeProviderContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  actualTheme: 'light' | 'dark';
}

const ThemeProviderContext = createContext<ThemeProviderContextValue | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
}

/**
 * Theme Provider Component
 *
 * Manages theme state and applies dark mode class to document root.
 * Supports light, dark, and system preference modes.
 *
 * Features:
 * - Persists theme preference via Zustand
 * - Listens to system theme changes
 * - Applies 'dark' class to <html> element
 * - Provides theme context to all children
 */
export function ThemeProvider({ children, defaultTheme = 'system' }: ThemeProviderProps) {
  const { theme, setTheme, toggleTheme } = useSettingsStore();

  // Initialize theme if not set
  useEffect(() => {
    if (!theme) {
      setTheme(defaultTheme);
    }
  }, [theme, defaultTheme, setTheme]);

  // Track system theme preference; only used when `theme === 'system'`.
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  );

  // Listen to system theme changes (kept always-on; cheap and avoids conditional deps).
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, []);

  const actualTheme: 'light' | 'dark' = theme === 'system' ? systemTheme : theme;

  // Apply theme to document root
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(actualTheme);

    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', actualTheme === 'dark' ? '#222222' : '#ffffff');
    }
  }, [actualTheme]);

  const value: ThemeProviderContextValue = {
    theme,
    setTheme,
    toggleTheme,
    actualTheme,
  };

  return (
    <ThemeProviderContext.Provider value={value}>
      {children}
    </ThemeProviderContext.Provider>
  );
}

/**
 * useTheme Hook
 *
 * Access theme context from any component.
 * Must be used within ThemeProvider.
 */
export function useTheme() {
  const context = useContext(ThemeProviderContext);

  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }

  return context;
}
