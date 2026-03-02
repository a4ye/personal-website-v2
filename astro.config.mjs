// @ts-check
import { defineConfig } from "astro/config";
import { visualizer } from "rollup-plugin-visualizer";

import tailwindcss from "@tailwindcss/vite";

import svelte from "@astrojs/svelte";

import icon from "astro-icon";

import vercel from "@astrojs/vercel";

import react from "@astrojs/react";

export default defineConfig({
    site: "https://aaronye.dev",
    security: {
        checkOrigin: false, // Temporarily disabled to debug CSRF issue
    },
    vite: {
        plugins: [
            visualizer({
                emitFile: true,
                filename: "stats.html",
            }),
            tailwindcss(),
        ],
    },

    integrations: [svelte(), icon({ iconDir: "src/assets/icons" }), react()],
    adapter: vercel(),
});
