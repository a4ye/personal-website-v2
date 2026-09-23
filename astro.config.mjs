// @ts-check
import { defineConfig } from "astro/config";
import { visualizer } from "rollup-plugin-visualizer";

import tailwindcss from "@tailwindcss/vite";

import svelte from "@astrojs/svelte";

import icon from "astro-icon";

import vercel from "@astrojs/vercel";

import react from "@astrojs/react";

import sitemap from "@astrojs/sitemap";

export default defineConfig({
    site: "https://aaronye.dev",
    prefetch: true,
    security: {
        checkOrigin: false, // Handled by custom middleware (src/middleware.ts)
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

    integrations: [
        svelte(),
        icon({ iconDir: "src/assets/icons" }),
        react(),
        sitemap({
            filter: (page) => !page.includes("/guestbook/delete"),
        }),
    ],
    adapter: vercel(),
});
