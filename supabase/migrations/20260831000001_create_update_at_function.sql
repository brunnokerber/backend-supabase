create or replace function public.handle_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = timezone('utc', now());
  new.updated_by = coalesce(auth.uid(), new.updated_by, old.updated_by);
  return new;
end;
$$;