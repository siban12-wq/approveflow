/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1B3A",
        canvas: "#F7F9FC",
        line: "#EEF2F7",
        indigo: "#4F46E5",
        sky: "#38BDF8",
        teal: "#14B8A6",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 10px 40px -12px rgba(15,23,42,.12)",
        lift: "0 18px 50px -16px rgba(15,23,42,.18)",
      },
      borderRadius: { card: "1.25rem" },
    },
  },
  plugins: [],
};
