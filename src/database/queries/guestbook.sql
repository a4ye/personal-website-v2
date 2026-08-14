-- name: InsertGuestbookEntry :one
insert into public.guestbook_entries (name, message)
values ($1, $2)
returning *;

-- name: GetGuestbookEntriesPaginated :many
select *
from public.guestbook_entries
order by created_at desc
limit 10 offset $1;

-- name: CountGuestbookEntries :one
select count(*) as count
from public.guestbook_entries;

-- name: GetGuestbookEntry :one
select *
from public.guestbook_entries
where id = $1;

-- name: DeleteGuestbookEntry :one
delete
from public.guestbook_entries
where id = $1
returning *;