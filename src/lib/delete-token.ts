import { createHmac, timingSafeEqual } from "node:crypto";

const TOKEN_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function sign(payload: string): string {
    const secret = import.meta.env.GUESTBOOK_DELETE_SECRET;
    if (!secret) {
        throw new Error("GUESTBOOK_DELETE_SECRET is not set");
    }
    return createHmac("sha256", secret).update(payload).digest("base64url");
}

export function createDeleteToken(entryId: number): string {
    const payload = `${entryId}.${Date.now() + TOKEN_TTL_MS}`;
    return `${payload}.${sign(payload)}`;
}

export function verifyDeleteToken(token: string): number | null {
    const [id, expiresAt, signature] = token.split(".");
    if (!id || !expiresAt || !signature) {
        return null;
    }

    const expected = Buffer.from(sign(`${id}.${expiresAt}`));
    const received = Buffer.from(signature);
    if (expected.length !== received.length || !timingSafeEqual(expected, received)) {
        return null;
    }

    const expiry = Number(expiresAt);
    const entryId = Number(id);
    if (!Number.isFinite(expiry) || expiry < Date.now() || !Number.isInteger(entryId)) {
        return null;
    }
    return entryId;
}
