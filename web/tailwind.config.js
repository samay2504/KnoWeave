/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Futuristic Black & Orange Palette
        'cyber': {
          black: '#0a0a0a',
          'gray-900': '#0d0d0d', 
          'gray-800': '#111111',
          'gray-700': '#1a1a1a',
          'gray-600': '#262626',
          'gray-500': '#404040',
          'gray-400': '#595959',
          'gray-300': '#737373',
          'gray-200': '#a3a3a3',
          'gray-100': '#d4d4d4',
        },
        'neon': {
          'orange-900': '#7c2d12',
          'orange-800': '#9a3412',
          'orange-700': '#c2410c',
          'orange-600': '#ea580c',
          'orange-500': '#f97316',
          'orange-400': '#fb923c',
          'orange-300': '#fdba74',
          'orange-200': '#fed7aa',
          'orange-100': '#ffedd5',
          'orange-50': '#fff7ed',
        },
        // Legacy gray support
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient': 'gradient 15s ease infinite',
        'liquid': 'liquid 20s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%': { 
            boxShadow: '0 0 5px #f97316, 0 0 10px #f97316, 0 0 15px #f97316',
          },
          '100%': { 
            boxShadow: '0 0 10px #f97316, 0 0 20px #f97316, 0 0 30px #f97316',
          },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradient: {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          },
        },
        liquid: {
          '0%, 100%': {
            'border-radius': '60% 40% 30% 70% / 60% 30% 70% 40%',
          },
          '50%': {
            'border-radius': '30% 60% 70% 40% / 50% 60% 30% 60%',
          },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':
          'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'cyber-grid': 'linear-gradient(rgba(249, 115, 22, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(249, 115, 22, 0.03) 1px, transparent 1px)',
        'liquid-gradient': 'linear-gradient(45deg, #0a0a0a 0%, #1a1a1a 25%, #f97316 50%, #1a1a1a 75%, #0a0a0a 100%)',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
    },
  },
  plugins: [],
}
