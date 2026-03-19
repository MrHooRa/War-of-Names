/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'brand-teal': '#0B8A8D',
        'brand-teal-hover': '#067a79',
        'brand-teal-light': '#17a2b8',
        'brand-slate': '#64748B',
        'brand-orange': '#D84315',
        'brand-dark': '#1F2937',
        'brand-light-bg': '#F8F9FA',
        'brand-dark-bg': '#111827',
        'brand-card-dark': '#1F2937',
        'brand-success': '#10B981',
        'brand-danger': '#EF4444',
        // Lobby-specific colors (09)
        'brand-bg': '#0a0d14',
        'brand-surface': '#151b29',
        'brand-teal-light-lobby': '#00D9E9',
        'brand-purple': '#9333EA',
        'brand-blue': '#3B82F6',
        'brand-emerald': '#10B981',
        'brand-border': '#2A3142',
      },
      fontFamily: {
        display: ['Cairo', 'sans-serif'],
        heading: ['Changa', 'sans-serif'],
        body: ['Cairo', 'sans-serif'],
      },
      animation: {
        'slide-down-fade': 'slideDownFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-in-scale': 'fadeInScale 1s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        slideDownFade: {
          '0%': { opacity: '0', transform: 'translateY(-40px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInScale: {
          '0%': { opacity: '0', transform: 'scale(0.85)', filter: 'drop-shadow(0 0 0px rgba(11, 138, 141, 0))' },
          '100%': { opacity: '1', transform: 'scale(1)', filter: 'drop-shadow(0 0 40px rgba(11, 138, 141, 0.6)) drop-shadow(0 0 60px rgba(0, 217, 233, 0.3))' },
        },
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        'smooth': 'cubic-bezier(0.25, 1, 0.5, 1)',
      },
    },
  },
  plugins: [],
}
