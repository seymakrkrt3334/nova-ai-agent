/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#07060d",
        plum: "#2a1248",
        iris: "#7c3aed",
      },
    },
  },
  plugins: [],
};
