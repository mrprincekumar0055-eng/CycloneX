/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#111827",
        "surface-raised": "#1f2937",
        border: "#374151",
        primary: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        emergency: {
          critical: '#ef4444',
          high: '#f97316',
          moderate: '#eab308',
          advisory: '#3b82f6',
        }
      },
    },
  },
  plugins: [],
};

