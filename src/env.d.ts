/// <reference types="astro/client" />

/** The commit the site was built from, read once per build by astro.config.mjs. */
declare const __GIT_COMMIT__: {
    shortSha: string;
    commitUrl: string;
    commitDate: string;
} | null;
