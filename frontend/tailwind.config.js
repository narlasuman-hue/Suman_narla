/** @type {import('tailwindcss').Config} */

// One accent across the app: `indigo-*` classes render as the same blue as `blue-*`.
const accent = {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb',
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
};

module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Cool slate greys (the app's neutral)
        gray: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        indigo: accent,
        blue: accent,
        canvas: '#f4f5f7', // page background
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        // Cards read as a hairline border plus a whisper of depth.
        sm: '0 0 0 1px #e2e8f0',
        DEFAULT: '0 0 0 1px #e2e8f0, 0 1px 2px 0 rgba(15, 23, 42, 0.04)',
        md: '0 0 0 1px #e2e8f0, 0 4px 8px -2px rgba(15, 23, 42, 0.08)',
        lg: '0 0 0 1px #e2e8f0, 0 10px 20px -6px rgba(15, 23, 42, 0.12)',
      },
      borderRadius: {
        lg: '10px',
      },
      transitionDuration: {
        DEFAULT: '200ms',
      },
    },
  },
  plugins: [],
};
