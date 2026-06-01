/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#FBCE5B',
          50: '#FEF9E6',
          100: '#FDF3CC',
          200: '#FBE899',
          300: '#F9DC66',
          400: '#F7D033',
          500: '#FBCE5B',
          600: '#E5B82A',
          700: '#B8922A',
          800: '#8A6D2A',
          900: '#5C492A',
        },
      },
    },
  },
  plugins: [],
}