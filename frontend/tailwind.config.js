/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        hud: ['"Share Tech Mono"', 'monospace'],
        title: ['"Rajdhani"', 'sans-serif'],
        sans: ['"Barlow"', 'sans-serif'],
      },
      colors: {
        void: 'var(--bg-void)',
        panel: 'var(--bg-panel)',
        card: 'var(--bg-card)',
        glow: 'var(--border-glow)',
        cyan: {
          DEFAULT: 'var(--cyan)',
          dim: 'var(--cyan-dim)',
        },
        green: 'var(--green)',
        red: 'var(--red)',
        gold: 'var(--gold)',
      }
    },
  },
  plugins: [],
}
