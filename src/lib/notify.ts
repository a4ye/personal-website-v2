import sanitizeHtml from "sanitize-html";
import { createDeleteToken } from "@/lib/delete-token";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const MAX_ATTEMPTS = 3;
const RETRY_DELAYS_MS = [500, 2000];
const REQUEST_TIMEOUT_MS = 10_000;

interface GuestbookEntry {
    id: number;
    name: string;
    message: string;
    createdAt: Date | null;
}

function toHtml(value: string): string {
    return sanitizeHtml(value, { allowedTags: [], allowedAttributes: {} }).replace(/\n/g, "<br>");
}

// Email clients strip webfonts, so Georgia stands in for Petrona and Figtree falls back to system sans.
const SERIF = "Georgia, 'Times New Roman', serif";
const SANS = "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif";

function buildHtml(entry: GuestbookEntry, deleteUrl: string): string {
    const date = entry.createdAt
        ? entry.createdAt.toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
          })
        : "";

    return `<div style="margin:0;padding:40px 32px;background:#f2f7f4;font-family:${SANS};">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;">
<tr><td style="padding-bottom:22px;font-family:${SERIF};font-size:30px;line-height:1.2;color:#3d6b55;">New guestbook entry</td></tr>
<tr><td style="border-top:1px solid #c5d6cc;padding:22px 0 26px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td style="font-family:${SERIF};font-size:19px;line-height:1.3;color:#3d6b55;">${toHtml(entry.name)}</td>
<td align="right" style="font-family:${SANS};font-size:12px;line-height:1.3;letter-spacing:0.08em;color:#7a9988;white-space:nowrap;">${date}</td>
</tr>
</table>
<div style="padding-top:12px;font-family:${SANS};font-size:16px;line-height:1.7;color:#2c3830;">${toHtml(entry.message)}</div>
</td></tr>
<tr><td style="border-top:1px solid #c5d6cc;padding-top:26px;">
<a href="${deleteUrl}" style="display:inline-block;background:#c06060;color:#f2f7f4;padding:10px 20px;border-radius:6px;text-decoration:none;font-family:${SANS};font-size:15px;line-height:20px;">Delete this entry</a>
<div style="padding-top:14px;font-family:${SANS};font-size:13px;line-height:1.6;color:#7a9988;">Opens a confirmation page first. Expires in 30 days.</div>
</td></tr>
</table>
</div>`;
}

export async function sendGuestbookNotification(entry: GuestbookEntry, origin: string) {
    const apiKey = import.meta.env.RESEND_API_KEY;
    const to = import.meta.env.GUESTBOOK_NOTIFY_TO;
    if (!apiKey || !to) {
        console.error(
            "Guestbook notification skipped: RESEND_API_KEY or GUESTBOOK_NOTIFY_TO unset",
        );
        return;
    }

    const deleteUrl = `${origin}/guestbook/delete?token=${encodeURIComponent(createDeleteToken(entry.id))}`;
    const body = JSON.stringify({
        from: import.meta.env.GUESTBOOK_NOTIFY_FROM || "onboarding@resend.dev",
        to,
        subject: `[guestbook] New entry from ${entry.name}`,
        html: buildHtml(entry, deleteUrl),
    });

    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
        try {
            const response = await fetch(RESEND_ENDPOINT, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${apiKey}`,
                    "Content-Type": "application/json",
                },
                body,
                signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
            });

            if (response.ok) return;

            // 4xx other than rate limiting means the request itself is wrong; retrying cannot fix it.
            if (response.status < 500 && response.status !== 429) {
                console.error(
                    `Guestbook notification rejected (${response.status}): ${await response.text()}`,
                );
                return;
            }
            console.warn(
                `Guestbook notification attempt ${attempt + 1} failed: ${response.status}`,
            );
        } catch (error) {
            console.warn(`Guestbook notification attempt ${attempt + 1} errored:`, error);
        }

        if (attempt < MAX_ATTEMPTS - 1) {
            await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
        }
    }

    console.error(
        `Guestbook notification failed after ${MAX_ATTEMPTS} attempts for entry ${entry.id}`,
    );
}
