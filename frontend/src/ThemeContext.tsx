import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage first, then system preference, default to dark
    const savedTheme = localStorage.getItem('playlist-ai-theme') as Theme;
    if (savedTheme) {
      return savedTheme;
    }
    
    // Check system preference
    if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    
    return 'dark';
  });

  useEffect(() => {
    // Save to localStorage whenever theme changes
    localStorage.setItem('playlist-ai-theme', theme);
    
    // Apply theme class to document root
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    
    // Update CSS custom properties
    updateThemeProperties(theme);
  }, [theme]);

  const updateThemeProperties = (currentTheme: Theme) => {
    const root = document.documentElement;
    
    if (currentTheme === 'light') {
      // Light theme - Spearmint dominant with light grey backgrounds
      root.style.setProperty('--color-bg-primary', '#F5F5F5');    // Light grey background
      root.style.setProperty('--color-bg-secondary', '#EAEAEA');  // Slightly darker grey for surfaces
      root.style.setProperty('--color-bg-tertiary', '#FFFFFF');   // Pure white for cards/inputs
      root.style.setProperty('--color-text-primary', '#1A1A1A');  // Near black text
      root.style.setProperty('--color-text-secondary', '#4A4A4A'); // Dark grey secondary text
      root.style.setProperty('--color-text-muted', '#757575');     // Medium grey muted text
      root.style.setProperty('--color-accent-primary', '#52C88A'); // Spearmint primary
      root.style.setProperty('--color-accent-hover', '#45B87A');   // Darker spearmint on hover
      root.style.setProperty('--color-accent-secondary', '#E91E63'); // Fuchsia accent
      root.style.setProperty('--color-accent-warning', '#FFC107');  // Citric warning
      root.style.setProperty('--color-accent-info', '#1A237E');    // Navy info
      root.style.setProperty('--color-border-primary', '#D1D1D1'); // Light borders
      root.style.setProperty('--color-border-secondary', '#B8B8B8'); // Darker borders
      root.style.setProperty('--color-shadow', 'rgba(0, 0, 0, 0.1)'); // Light shadows
    } else {
      // Dark theme - keep existing dark colors
      root.style.setProperty('--color-bg-primary', '#0d1117');
      root.style.setProperty('--color-bg-secondary', '#161b22');
      root.style.setProperty('--color-bg-tertiary', '#21262d');
      root.style.setProperty('--color-text-primary', '#ffffff');
      root.style.setProperty('--color-text-secondary', '#8b949e');
      root.style.setProperty('--color-text-muted', '#656d76');
      root.style.setProperty('--color-accent-primary', '#1DB954');
      root.style.setProperty('--color-accent-hover', '#1ed760');
      root.style.setProperty('--color-accent-secondary', '#FD79A8');
      root.style.setProperty('--color-accent-warning', '#FFC107');
      root.style.setProperty('--color-accent-info', '#74B9FF');
      root.style.setProperty('--color-border-primary', '#30363d');
      root.style.setProperty('--color-border-secondary', '#444c56');
      root.style.setProperty('--color-shadow', 'rgba(0, 0, 0, 0.3)');
    }
  };

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};