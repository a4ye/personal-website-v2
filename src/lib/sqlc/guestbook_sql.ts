import { Sql } from "postgres";

export const insertGuestbookEntryQuery = `-- name: InsertGuestbookEntry :one
insert into public.guestbook_entries (name, message)
values ($1, $2)
returning id, name, message, created_at`;

export interface InsertGuestbookEntryArgs {
    name: string;
    message: string;
}

export interface InsertGuestbookEntryRow {
    id: number;
    name: string;
    message: string;
    createdAt: Date | null;
}

export async function insertGuestbookEntry(sql: Sql, args: InsertGuestbookEntryArgs): Promise<InsertGuestbookEntryRow | null> {
    const rows = await sql.unsafe(insertGuestbookEntryQuery, [args.name, args.message]).values();
    if (rows.length !== 1) {
        return null;
    }
    const row = rows[0];
    return {
        id: row[0],
        name: row[1],
        message: row[2],
        createdAt: row[3]
    };
}

export const getGuestbookEntriesPaginatedQuery = `-- name: GetGuestbookEntriesPaginated :many
select id, name, message, created_at
from public.guestbook_entries
order by created_at desc
limit 10 offset $1`;

export interface GetGuestbookEntriesPaginatedArgs {
    offset: string;
}

export interface GetGuestbookEntriesPaginatedRow {
    id: number;
    name: string;
    message: string;
    createdAt: Date | null;
}

export async function getGuestbookEntriesPaginated(sql: Sql, args: GetGuestbookEntriesPaginatedArgs): Promise<GetGuestbookEntriesPaginatedRow[]> {
    return (await sql.unsafe(getGuestbookEntriesPaginatedQuery, [args.offset]).values()).map(row => ({
        id: row[0],
        name: row[1],
        message: row[2],
        createdAt: row[3]
    }));
}

export const countGuestbookEntriesQuery = `-- name: CountGuestbookEntries :one
select count(*) as count
from public.guestbook_entries`;

export interface CountGuestbookEntriesRow {
    count: string;
}

export async function countGuestbookEntries(sql: Sql): Promise<CountGuestbookEntriesRow | null> {
    const rows = await sql.unsafe(countGuestbookEntriesQuery, []).values();
    if (rows.length !== 1) {
        return null;
    }
    const row = rows[0];
    return {
        count: row[0]
    };
}

export const getGuestbookEntryQuery = `-- name: GetGuestbookEntry :one
select id, name, message, created_at
from public.guestbook_entries
where id = $1`;

export interface GetGuestbookEntryArgs {
    id: number;
}

export interface GetGuestbookEntryRow {
    id: number;
    name: string;
    message: string;
    createdAt: Date | null;
}

export async function getGuestbookEntry(sql: Sql, args: GetGuestbookEntryArgs): Promise<GetGuestbookEntryRow | null> {
    const rows = await sql.unsafe(getGuestbookEntryQuery, [args.id]).values();
    if (rows.length !== 1) {
        return null;
    }
    const row = rows[0];
    return {
        id: row[0],
        name: row[1],
        message: row[2],
        createdAt: row[3]
    };
}

export const deleteGuestbookEntryQuery = `-- name: DeleteGuestbookEntry :one
delete
from public.guestbook_entries
where id = $1
returning id, name, message, created_at`;

export interface DeleteGuestbookEntryArgs {
    id: number;
}

export interface DeleteGuestbookEntryRow {
    id: number;
    name: string;
    message: string;
    createdAt: Date | null;
}

export async function deleteGuestbookEntry(sql: Sql, args: DeleteGuestbookEntryArgs): Promise<DeleteGuestbookEntryRow | null> {
    const rows = await sql.unsafe(deleteGuestbookEntryQuery, [args.id]).values();
    if (rows.length !== 1) {
        return null;
    }
    const row = rows[0];
    return {
        id: row[0],
        name: row[1],
        message: row[2],
        createdAt: row[3]
    };
}

