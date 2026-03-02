import type { APIContext, MiddlewareNext } from "astro";

const ALLOWED_ORIGINS = ["https://aaronye.dev", "http://localhost:4321"];

export const onRequest = async (context: APIContext, next: MiddlewareNext) => {
    // Only check POST requests (actions)
    if (context.request.method === "POST") {
        const origin = context.request.headers.get("origin");

        if (!origin || !ALLOWED_ORIGINS.includes(origin)) {
            return new Response("Forbidden", { status: 403 });
        }
    }
    return next();
};
