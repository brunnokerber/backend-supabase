// @ts-nocheck
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  // Trata pre-flight CORS do navegador
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

    const adminClient = createClient(supabaseUrl, supabaseServiceKey);

    // 1. Extrai o token do cabeçalho Authorization
    const authHeader = req.headers.get("Authorization") ?? "";
    const token = authHeader.replace(/^Bearer\s+/i, "").trim();

    if (!token) {
      return new Response(JSON.stringify({ error: "Token de autenticação não fornecido." }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // 2. Valida o usuário dono do token via Supabase Auth
    const { data: { user }, error: userError } = await adminClient.auth.getUser(token);

    if (userError || !user) {
      return new Response(JSON.stringify({ error: "Sessão inválida ou expirada." }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // 3. Valida se o usuário é Administrador (via metadata ou via tabela profiles)
    const isMetaAdmin =
      user.app_metadata?.role === "admin" ||
      user.user_metadata?.role === "admin";

    const { data: profile } = await adminClient
      .from("profiles")
      .select("role, ativo")
      .eq("id", user.id)
      .single();

    const isProfileAdmin = profile && profile.role === "admin" && profile.ativo !== false;

    if (!isMetaAdmin && !isProfileAdmin) {
      return new Response(JSON.stringify({ error: "Apenas administradores podem convidar usuários." }), {
        status: 403,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // 4. Recebe os dados do convite e dispara via Supabase Auth Admin
    const body = await req.json();
    const { email, role, redirectTo } = body;

    if (!email) {
      return new Response(JSON.stringify({ error: "E-mail não informado." }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Determina a URL base para onde o usuário será redirecionado após aceitar o convite
    const requestOrigin = req.headers.get("origin");
    const baseUrl =
      Deno.env.get("SITE_URL") ||
      requestOrigin ||
      "https://peludinhosdovale.vercel.app";

    const finalRedirectTo = redirectTo || `${baseUrl.replace(/\/$/, "")}/definir-senha`;

    const { data, error: inviteError } = await adminClient.auth.admin.inviteUserByEmail(
      email.trim().toLowerCase(),
      {
        redirectTo: finalRedirectTo,
        data: {
          role: role || "user",
        },
      }
    );

    if (inviteError) {
      return new Response(JSON.stringify({ error: inviteError.message }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Convite enviado com sucesso para ${email}`,
        data,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message || "Erro interno no servidor." }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
