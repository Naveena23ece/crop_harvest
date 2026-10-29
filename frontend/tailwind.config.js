/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary:  { DEFAULT: "#16a34a", 50: "#f0fdf4", 500: "#22c55e", 700: "#15803d" },
        risk: {
          low:      "#22c55e",
          moderate: "#f59e0b",
          high:     "#ef4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["JetBrains Mono", "ui-monospace"],
      },
    },
  },
  plugins: [],
};
