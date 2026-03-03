/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slateblue: "#1B3558",
        mint: "#00A896",
        amber: "#F0A202",
        coral: "#F05D5E"
      }
    }
  },
  plugins: []
};
