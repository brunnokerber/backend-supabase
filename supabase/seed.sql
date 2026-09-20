-- Seed data for local development

DO $$
DECLARE
  admin_user_id uuid := 'a0000000-0000-0000-0000-000000000001';
  admin_email text := 'admin@admin.com';
  admin_password text := 'admin123';
BEGIN
  -- 1. Insere o usuário padrão no Supabase Auth (auth.users)
  -- Isso automaticamente aciona a trigger 'on_auth_user_created' que insere o registro em public.profiles com role 'user'
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = admin_user_id OR email = admin_email) THEN
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
      recovery_token
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
      '{"provider":"email","providers":["email"]}'::jsonb,
      '{"name":"Administrador"}'::jsonb,
      now(),
      now(),
      '',
      '',
      '',
      ''
    );
  END IF;

  -- 2. Insere a identidade correspondente no auth.identities para viabilizar login por e-mail/senha
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

  -- 3. Promove o usuário recém-criado para 'admin' na tabela public.profiles
  UPDATE public.profiles
  SET role = 'admin'
  WHERE id = admin_user_id;

END $$;
