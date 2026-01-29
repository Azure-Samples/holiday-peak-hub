const defaultTheme = require("tailwindcss/defaultTheme");
const colors = require("tailwindcss/colors");
const plugin = require("tailwindcss/plugin");

module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./layouts/**/*.{js,ts,jsx,tsx}",
    "./public/**/*.html",
  ],
  darkMode: 'media', // or 'media' or 'class'
  theme: {
    extend: {
      fontFamily: {
        sans: ["Poppins", ...defaultTheme.fontFamily.sans],
      },
      colors: {
        current: "currentColor",
        green: colors.emerald,
        yellow: colors.amber,
        purple: colors.violet,
        gray: colors.neutral,
        primary: '#3cb371',
        secondary: '#2e8b57',
        tertiary: '#90ee90',
        'neutral-bg': '#f5f5f5',
        'neutral-dark': '#333333',
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms")({
      strategy: "class",
    }),
    require("@tailwindcss/typography"),
    require("@tailwindcss/aspect-ratio"),
    plugin(function ({addVariant, e}) {
      addVariant("collapsed", ({modifySelectors, separator}) => {
        modifySelectors(({className}) => {
          return `.collapsed .${e(`collapsed${separator}${className}`)}`;
        });
      });
      addVariant("rtl", ({modifySelectors, separator}) => {
        modifySelectors(({className}) => {
          return `.rtl .${e(`rtl${separator}${className}`)}`;
        });
      });
    }),
  ],
};
