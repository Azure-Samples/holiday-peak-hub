'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');

    const resolveTheme = (): Theme => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'dark' || savedTheme === 'light') {
        return savedTheme;
      }
      return media.matches ? 'dark' : 'light';
    };

    const applyTheme = (nextTheme: Theme) => {
      setTheme(nextTheme);
      root.classList.toggle('dark', nextTheme === 'dark');
      root.setAttribute('data-theme', nextTheme);
    };

    applyTheme(resolveTheme());

    const handleSystemTheme = (event: MediaQueryListEvent) => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'dark' || savedTheme === 'light') {
        return;
      }
      applyTheme(event.matches ? 'dark' : 'light');
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== 'theme') {
        return;
      }
      applyTheme(resolveTheme());
    };

    media.addEventListener('change', handleSystemTheme);
    window.addEventListener('storage', handleStorage);

    return () => {
      media.removeEventListener('change', handleSystemTheme);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const toggleTheme = () => {
    setTheme((currentTheme) => {
      const nextTheme: Theme = currentTheme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', nextTheme);
      document.documentElement.classList.toggle('dark', nextTheme === 'dark');
      document.documentElement.setAttribute('data-theme', nextTheme);
      return nextTheme;
    });
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
