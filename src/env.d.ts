/// <reference types="astro/client" />

/** The commit the site was built from, read once per build by astro.config.mjs. */
declare const __GIT_COMMIT__: {
    shortSha: string;
    commitUrl: string;
    commitDate: string;
} | null;

/** The Umami tracker. Layout.astro loads it in production only, and a blocker can stop it. */
interface Window {
    umami?: {
        track(event: string, data?: Record<string, unknown>): Promise<unknown>;
    };
}
