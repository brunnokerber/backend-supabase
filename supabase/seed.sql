-- Seed data for local development

DO $$
DECLARE
  admin_user_id uuid := 'a0000000-0000-0000-0000-000000000001';
  admin_email text := 'admin@admin.com';
  admin_password text := 'admin123';
  existing_user_id uuid;
BEGIN
  -- 1. Verifica se já existe um usuário com esse email no auth.users
  SELECT id INTO existing_user_id FROM auth.users WHERE email = admin_email;

  IF existing_user_id IS NOT NULL THEN
    -- Se já existe, atualizamos o ID de referência para evitar erro de FK e garantimos role admin
    admin_user_id := existing_user_id;

    UPDATE auth.users
    SET
      encrypted_password = extensions.crypt(admin_password, extensions.gen_salt('bf')),
      email_confirmed_at = coalesce(email_confirmed_at, now()),
      raw_app_meta_data = jsonb_set(
        coalesce(raw_app_meta_data, '{}'::jsonb),
        '{role}',
        '"admin"'
      ) || '{"provider":"email","providers":["email"]}'::jsonb,
      raw_user_meta_data = jsonb_set(
        coalesce(raw_user_meta_data, '{}'::jsonb),
        '{role}',
        '"admin"'
      ) || '{"name":"Administrador"}'::jsonb,
      updated_at = now()
    WHERE id = admin_user_id;
  ELSE
    -- 1.1 Insere o usuário padrão no Supabase Auth com role: admin em app e user metadata
    INSERT INTO auth.users (
      instance_id,
      id,
      aud,
      role,
      email,
      encrypted_password,
      email_confirmed_at,
      recovery_sent_at,
      last_sign_in_at,
      raw_app_meta_data,
      raw_user_meta_data,
      created_at,
      updated_at,
      confirmation_token,
      email_change,
      email_change_token_new,
      recovery_token,
      is_sso_user
    )
    VALUES (
      '00000000-0000-0000-0000-000000000000',
      admin_user_id,
      'authenticated',
      'authenticated',
      admin_email,
      extensions.crypt(admin_password, extensions.gen_salt('bf')),
      now(),
      now(),
      now(),
      '{"provider":"email","providers":["email"],"role":"admin"}'::jsonb,
      '{"role":"admin","name":"Administrador"}'::jsonb,
      now(),
      now(),
      '',
      '',
      '',
      '',
      false
    );
  END IF;

  -- 2. Insere a identidade correspondente no auth.identities caso não exista
  IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = admin_user_id) THEN
    INSERT INTO auth.identities (
      id,
      user_id,
      identity_data,
      provider,
      provider_id,
      last_sign_in_at,
      created_at,
      updated_at
    )
    VALUES (
      admin_user_id,
      admin_user_id,
      jsonb_build_object('sub', admin_user_id::text, 'email', admin_email),
      'email',
      admin_user_id::text,
      now(),
      now(),
      now()
    );
  END IF;

  -- 3. Garante que o profile é admin na tabela public.profiles
  INSERT INTO public.profiles (id, email, role, ativo, created_at, updated_at)
  VALUES (
    admin_user_id,
    admin_email,
    'admin'::public.app_role,
    true,
    now(),
    now()
  )
  ON CONFLICT (id) DO UPDATE
  SET
    role = 'admin'::public.app_role,
    email = EXCLUDED.email,
    ativo = true,
    updated_at = now();

END $$;
