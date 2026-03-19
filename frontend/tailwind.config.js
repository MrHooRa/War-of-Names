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
      },
      fontFamily: {
        display: ['Cairo', 'sans-serif'],
        heading: ['Changa', 'sans-serif'],
        body: ['Cairo', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
