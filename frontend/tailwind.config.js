/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        mongodb: {
          green: '#10aa50',
          'green-dim': '#0d8a40',
          surface: '#f0fdf4',
        },
        fastapi: {
          teal: '#009485',
        },
        accent: {
          purple: '#7c3aed',
        },
        dark: {
          bg: '#0f172a',
          card: '#1e293b',
          input: '#334155',
          border: '#334155',
        },
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s infinite',
        'slide-up': 'slideUp 0.2s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'generate': 'generatePulse 0.6s ease-out',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(16, 170, 80, 0.4)' },
          '70%': { boxShadow: '0 0 0 10px rgba(16, 170, 80, 0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        generatePulse: {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.95)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
