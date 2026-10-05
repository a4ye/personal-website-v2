// @ts-check
import { defineConfig } from "astro/config";
import { visualizer } from "rollup-plugin-visualizer";

import tailwindcss from "@tailwindcss/vite";

import svelte from "@astrojs/svelte";

import icon from "astro-icon";

import vercel from "@astrojs/vercel";

import sitemap from "@astrojs/sitemap";

/**
 * The commit the footer shows.
 *
 * Asking GitHub here costs one request per build. The page used to ask a serverless route for it
 * on every view, which is a function invocation and a round trip for a line that only changes when
 * the site is deployed. The answer is frozen into the static pages and the server bundle alike by
 * the `define` below, so the server-rendered pages do not ask either.
 */
async function latestCommit() {
    const token = process.env.GITHUB_API_TOKEN;
    try {
        const response = await fetch(
            "https://api.github.com/repos/a4ye/personal-website-v2/commits?per_page=1",
            {
                headers: {
                    Accept: "application/vnd.github.v3+json",
                    ...(token && { Authorization: `Bearer ${token}` }),
                },
            },
        );
        if (!response.ok) throw new Error(`GitHub answered ${response.status}`);
        const [commit] = await response.json();
        return {
            shortSha: commit.sha.slice(0, 7),
            commitUrl: commit.html_url,
            commitDate: commit.commit.author.date,
        };
    } catch (e) {
        // A footer line is not worth failing a build over; the footer leaves it out instead
        console.warn(`could not read the latest commit: ${e.message}`);
        return null;
    }
}

export default defineConfig({
    site: "https://aaronye.dev",
    prefetch: true,
    security: {
        checkOrigin: false, // Handled by custom middleware (src/middleware.ts)
    },
    vite: {
        define: {
            __GIT_COMMIT__: JSON.stringify(await latestCommit()),
        },
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
        sitemap({
            filter: (page) => !page.includes("/guestbook/delete"),
        }),
    ],
    adapter: vercel(),
});
