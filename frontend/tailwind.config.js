/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["var(--font-body)", "system-ui", "sans-serif"], display: ["var(--font-display)", "system-ui", "sans-serif"] },
      colors: { ink: "#0B1B3A", brand: "#0E7C7B", brandbg: "#E3F3F2", stamp: "#C2331A", stampbg: "#FDEEEA", paper: "#F4F6FA", ok: "#0B7A55", okbg: "#E5F5EE", warnbg: "#FFF5D6", warn: "#7A4E00" },
      boxShadow: { soft: "0 1px 2px rgba(11,27,58,.05), 0 8px 24px -12px rgba(11,27,58,.14)" },
    },
  },
  plugins: [],
};
