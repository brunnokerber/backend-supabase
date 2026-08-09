insert into public.hello_world_messages (id, message)
values (1, 'Hello, world from Supabase SQL!')
on conflict (id) do update
set message = excluded.message;
