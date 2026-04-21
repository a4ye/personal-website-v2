/** @type {import("tailwindcss").Config} */
export default {
    content: ["./src/**/*.{astro,html,js,ts,svelte}"],
    theme: {
        extend: {
            fontFamily: {
                sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
                display: ["Fraunces", "Georgia", "serif"],
                mono: ["JetBrains Mono", "SF Mono", "Monaco", "monospace"],
            },
            colors: {
                // CSS variable colors
                primary: {
                    bg: "var(--bg-primary)",
                    text: "var(--text-primary)",
                },
                secondary: {
                    bg: "var(--bg-secondary)",
                    text: "var(--text-secondary)",
                },
                tertiary: {
                    bg: "var(--bg-tertiary)",
                    text: "var(--text-tertiary)",
                },
                // Vibrant accent colors
                accent: {
                    purple: "var(--accent-purple)",
                    "purple-bright": "var(--accent-purple-bright)",
                    blue: "var(--accent-blue)",
                    "blue-bright": "var(--accent-blue-bright)",
                    pink: "var(--accent-pink)",
                    "pink-bright": "var(--accent-pink-bright)",
                    yellow: "var(--accent-yellow)",
                    orange: "var(--accent-orange)",
                    red: "var(--accent-red)",
                },
            },
            boxShadow: {
                soft: "var(--shadow-sm)",
                medium: "var(--shadow-md)",
                large: "var(--shadow-lg)",
            },
            keyframes: {
                gradientShift: {
                    "0%": { backgroundPosition: "0% 50%" },
                    "50%": { backgroundPosition: "100% 50%" },
                    "100%": { backgroundPosition: "0% 50%" },
                },
                floatBlob: {
                    "0%, 100%": { transform: "translateY(0px) scale(1)" },
                    "50%": { transform: "translateY(-20px) scale(1.05)" },
                },
            },
            animation: {
                gradientShift: "gradientShift 8s ease-in-out infinite",
                floatBlob: "floatBlob 6s ease-in-out infinite",
            },
        },
    },
    plugins: [],
};
