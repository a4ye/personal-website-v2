import { defineAction, ActionError } from "astro:actions";
import { z } from "astro/zod";
import { insertGuestbookEntry } from "@/lib/sqlc/guestbook_sql.ts";
import { incrementVisitsCount } from "@/lib/sqlc/counters_sql.ts";
import { db } from "@/lib/database.ts";
import { checkRateLimit } from "@/lib/rate-limit.ts";
import sanitizeHtml from "sanitize-html";
import { profanity } from "@2toad/profanity";

// Rate limit config: 5 submissions per minute
const RATE_LIMIT_CONFIG = {
    windowMs: 30 * 1000, // 30 seconds
    maxRequests: 3,
};

// Sanitize user input - escape HTML entities
function sanitize(input: string): string {
    return sanitizeHtml(input, {
        allowedTags: [],
        allowedAttributes: {},
        disallowedTagsMode: "escape",
    }).trim();
}

export const server = {
    incrementVisits: defineAction({
        accept: "json",
        input: z.object({}),
        async handler() {
            const result = await incrementVisitsCount(db);
            if (!result) {
                throw new ActionError({
                    code: "INTERNAL_SERVER_ERROR",
                    message: "Failed to increment visits count",
                });
            }
            return { countValue: result.countValue };
        },
    }),
    submitGuestbookEntry: defineAction({
        accept: "form",
        input: z.object({
            name: z
                .string()
                .min(1, "Name is required.")
                .max(32, "Name must be at most 32 characters."),
            message: z
                .string()
                .min(1, "Message is required.")
                .max(1024, "Message must be at most 1024 characters."),
        }),
        async handler(input, context) {
            // Get client IP from request headers
            const forwarded = context.request.headers.get("x-forwarded-for");
            const ip =
                forwarded?.split(",")[0]?.trim() ||
                context.request.headers.get("x-real-ip") ||
                "unknown";

            // Check rate limit
            const rateLimitResult = await checkRateLimit(`guestbook:${ip}`, RATE_LIMIT_CONFIG);

            if (!rateLimitResult.allowed) {
                const resetInSeconds = Math.ceil(
                    (rateLimitResult.resetAt.getTime() - Date.now()) / 1000,
                );
                throw new ActionError({
                    code: "TOO_MANY_REQUESTS",
                    message: `Too many submissions. Please try again in ${resetInSeconds} seconds.`,
                });
            }

            const { name, message } = input;

            // Check for profanity
            if (profanity.exists(name) || profanity.exists(message)) {
                throw new ActionError({
                    code: "BAD_REQUEST",
                    message: "Please avoid using offensive language in your submission.",
                });
            }

            // Sanitize inputs
            const sanitizedName = sanitize(name);
            const sanitizedMessage = sanitize(message);

            // Re-validate after sanitization
            if (sanitizedName.length === 0) {
                throw new ActionError({
                    code: "BAD_REQUEST",
                    message: "Name cannot be empty after removing invalid characters.",
                });
            }
            if (sanitizedMessage.length === 0) {
                throw new ActionError({
                    code: "BAD_REQUEST",
                    message: "Message cannot be empty after removing invalid characters.",
                });
            }

            try {
                return await insertGuestbookEntry(db, {
                    name: sanitizedName,
                    message: sanitizedMessage,
                });
            } catch (error) {
                throw new ActionError({
                    code: "INTERNAL_SERVER_ERROR",
                    message: "An unexpected error occurred :(",
                });
            }
        },
    }),
};
