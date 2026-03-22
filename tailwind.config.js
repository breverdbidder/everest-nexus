/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: '#1E3A5F',
        accent: '#F59E0B',
        bg: '#020617',
        p0: '#EF4444',
        p1: '#F59E0B',
        p2: '#EAB308',
        p3: '#6B7280',
        success: '#10B981',
        layer: {
          tasks: '#EF4444',
          workflows: '#8B5CF6',
          repos: '#1E3A5F',
          data: '#10B981',
          secrets: '#F59E0B',
          domains: '#06B6D4',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      }
    },
  },
  plugins: [],
}
