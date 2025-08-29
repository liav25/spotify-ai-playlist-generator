/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Theme-aware colors using CSS custom properties
        'bg-primary': 'var(--color-bg-primary)',
        'bg-secondary': 'var(--color-bg-secondary)',
        'bg-tertiary': 'var(--color-bg-tertiary)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        'accent-primary': 'var(--color-accent-primary)',
        'accent-hover': 'var(--color-accent-hover)',
        'accent-secondary': 'var(--color-accent-secondary)',
        'accent-warning': 'var(--color-accent-warning)',
        'accent-info': 'var(--color-accent-info)',
        'border-primary': 'var(--color-border-primary)',
        'border-secondary': 'var(--color-border-secondary)',
        'shadow': 'var(--color-shadow)',
        
        // Color palette from your image
        palette: {
          spearmint: '#52C88A',
          'spearmint-dark': '#45B87A',
          fuchsia: '#E91E63',
          'fuchsia-dark': '#C2185B',
          citric: '#FFC107',
          'citric-dark': '#FFA000',
          navy: '#1A237E',
          'navy-light': '#303F9F',
          black: '#000000',
          white: '#FFFFFF',
          'light-grey': '#F5F5F5',
          'medium-grey': '#EAEAEA',
        },
        
        // Legacy Spotify colors (keep for backwards compatibility)
        spotify: {
          // Core Spotify Colors
          green: '#1DB954',
          'green-hover': '#1ED760',
          black: '#171313',
          white: '#FFFFFF',
          
          // Vibrant Palette from Image
          navy: '#2E3A87',
          'navy-light': '#4A5BAE',
          teal: '#1DB954',
          'teal-light': '#2ECC71',
          orange: '#FF6B35',
          'orange-light': '#FF8C69',
          skyblue: '#74B9FF',
          'skyblue-light': '#A29BFE',
          coral: '#E74C3C',
          'coral-light': '#FF7675',
          pink: '#FD79A8',
          'pink-light': '#FDCB6E',
          brown: '#A0522D',
          'brown-light': '#D2691E',
          emerald: '#00B894',
          'emerald-light': '#00CEC9',
          
          // Warm Beige/Cream Base
          cream: {
            50: '#FEFCF9',
            100: '#FAF9F7',
            200: '#F5F4F2',
            300: '#F0EFED',
            400: '#E8E6E3',
            500: '#D4D2CF',
            600: '#B8B6B3',
            700: '#9C9A97',
            800: '#7D7B78',
            900: '#5E5C59'
          },
          
          // Enhanced Grays
          gray: {
            50: '#F8F9FA',
            100: '#F1F3F4',
            200: '#E8EAED',
            300: '#DADCE0',
            400: '#9AA0A6',
            500: '#5F6368',
            600: '#3C4043',
            700: '#202124',
            800: '#171717',
            900: '#0F0F0F'
          }
        }
      },
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        'display': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'bounce-in': 'bounceIn 0.5s ease-out',
        'pulse-ring': 'pulseRing 2s cubic-bezier(0.455, 0.03, 0.515, 0.955) infinite',
        'float': 'float 6s ease-in-out infinite',
        'color-shift': 'colorShift 8s ease-in-out infinite',
        'gradient-x': 'gradientX 3s ease infinite',
        'wiggle': 'wiggle 1s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceIn: {
          '0%': { transform: 'scale(0.3)', opacity: '0' },
          '50%': { transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulseRing: {
          '0%': { transform: 'scale(0.33)' },
          '40%, 50%': { opacity: '1' },
          '100%': { opacity: '0', transform: 'scale(1.2)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-10px) rotate(5deg)' },
        },
        colorShift: {
          '0%, 100%': { filter: 'hue-rotate(0deg)' },
          '50%': { filter: 'hue-rotate(180deg)' },
        },
        gradientX: {
          '0%, 100%': { 'background-position': '0% 50%' },
          '50%': { 'background-position': '100% 50%' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-3deg)' },
          '50%': { transform: 'rotate(3deg)' },
        },
      },
      backgroundImage: {
        'gradient-rainbow': 'linear-gradient(45deg, #FF6B35, #FD79A8, #74B9FF, #1DB954, #00B894)',
        'gradient-warm': 'linear-gradient(135deg, #FAF9F7 0%, #F5F4F2 50%, #F0EFED 100%)',
        'gradient-sunset': 'linear-gradient(45deg, #FF6B35, #FD79A8)',
        'gradient-ocean': 'linear-gradient(45deg, #74B9FF, #00B894)',
        'gradient-forest': 'linear-gradient(45deg, #1DB954, #00B894)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography')
  ],
}