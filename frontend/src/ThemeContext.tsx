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
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('playlist-ai-theme') as Theme | null;
      if (savedTheme === 'light' || savedTheme === 'dark') {
        return savedTheme;
      }
    }

    return 'light';
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
      // Light theme - Vibrant and professional with warm backgrounds
      root.style.setProperty('--color-bg-primary', '#FEFEFE');     // Warm white background
      root.style.setProperty('--color-bg-secondary', '#F8F9FA');   // Subtle warm surface
      root.style.setProperty('--color-bg-tertiary', '#FFFFFF');    // Pure white for cards/inputs
      root.style.setProperty('--color-text-primary', '#1A1A1A');   // Near black text
      root.style.setProperty('--color-text-secondary', '#4A4A4A');  // Dark grey secondary text
      root.style.setProperty('--color-text-muted', '#6B7280');     // Cool grey muted text
      root.style.setProperty('--color-accent-primary', '#1DB954');  // Spotify Green
      root.style.setProperty('--color-accent-hover', '#1ED760');    // Brighter green on hover
      root.style.setProperty('--color-accent-secondary', '#E91E63'); // Vibrant Pink
      root.style.setProperty('--color-accent-warning', '#FFB02E');  // Warm Orange
      root.style.setProperty('--color-accent-info', '#3B82F6');     // Bright Blue  
      root.style.setProperty('--color-border-primary', '#E5E7EB');  // Light cool border
      root.style.setProperty('--color-border-secondary', '#D1D5DB'); // Medium cool border
      root.style.setProperty('--color-shadow', 'rgba(0, 0, 0, 0.08)'); // Subtle shadows
    } else {
      // Dark theme - Rich dark with vibrant accents
      root.style.setProperty('--color-bg-primary', '#0F0F0F');     // Rich black
      root.style.setProperty('--color-bg-secondary', '#1A1A1A');   // Dark charcoal
      root.style.setProperty('--color-bg-tertiary', '#242424');    // Medium dark for cards
      root.style.setProperty('--color-text-primary', '#FFFFFF');   // Pure white text
      root.style.setProperty('--color-text-secondary', '#B3B3B3'); // Light grey secondary
      root.style.setProperty('--color-text-muted', '#737373');     // Medium grey muted
      root.style.setProperty('--color-accent-primary', '#1DB954'); // Spotify Green
      root.style.setProperty('--color-accent-hover', '#1ED760');   // Brighter green on hover
      root.style.setProperty('--color-accent-secondary', '#FF1493'); // Hot Pink
      root.style.setProperty('--color-accent-warning', '#FFA500');  // Orange
      root.style.setProperty('--color-accent-info', '#00BFFF');     // Deep Sky Blue
      root.style.setProperty('--color-border-primary', '#404040'); // Medium dark border
      root.style.setProperty('--color-border-secondary', '#525252'); // Lighter dark border
      root.style.setProperty('--color-shadow', 'rgba(0, 0, 0, 0.4)'); // Rich shadows
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
