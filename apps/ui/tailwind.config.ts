import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './layouts/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // New color palette: Ocean Blue, Lime Green, Cyan
        ocean: {
          50: '#E6F4FB',
          100: '#CCE9F7',
          200: '#99D3EF',
          300: '#66BDE7',
          400: '#33A7DF',
          500: '#0077BE',
          600: '#005F98',
          700: '#004772',
          800: '#00304C',
          900: '#001826',
        },
        lime: {
          50: '#F0FBF0',
          100: '#E1F8E1',
          200: '#C3F1C3',
          300: '#A5EAA5',
          400: '#87E387',
          500: '#32CD32',
          600: '#28A428',
          700: '#1E7B1E',
          800: '#145214',
          900: '#0A290A',
        },
        cyan: {
          50: '#E6FAFA',
          100: '#CCF5F5',
          200: '#99EBEB',
          300: '#66E1E1',
          400: '#33D7D7',
          500: '#00CED1',
          600: '#00A5A7',
          700: '#007C7D',
          800: '#005254',
          900: '#00292A',
        },
        // Legacy colors for compatibility
        primary: '#0077BE',
        secondary: '#32CD32',
        tertiary: '#00CED1',
        'neutral-bg': '#f5f5f5',
        'neutral-dark': '#2D3748',
      },
      boxShadow: {
        'ocean-sm': '0 1px 2px 0 rgb(0 119 190 / 0.05)',
        'ocean-md': '0 4px 6px -1px rgb(0 119 190 / 0.1)',
        'ocean-lg': '0 10px 15px -3px rgb(0 119 190 / 0.1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}

export default config
