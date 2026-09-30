// @ts-nocheck
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function jsonResponse(body: object, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function errorResponse(message: string, status = 400, code?: string) {
  return jsonResponse(
    {
      error: message,
      message,
      ...(code ? { code } : {}),
    },
    status
  );
}

function successResponse(message: string, data: any = {}, status = 200) {
  return jsonResponse(
    {
      success: true,
      message,
      data,
    },
    status
  );
}

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
      return errorResponse("Token de autenticação não fornecido.", 401, "unauthorized");
    }

    // 2. Valida o usuário dono do token via Supabase Auth
    const { data: { user }, error: userError } = await adminClient.auth.getUser(token);

    if (userError || !user) {
      return errorResponse("Sessão inválida ou expirada.", 401, "session_expired");
    }

    // 3. Valida se o usuário é Administrador ativo
    const isMetaAdmin =
      user.app_metadata?.role === "admin" ||
      user.user_metadata?.role === "admin";

    const { data: profile } = await adminClient
      .from("profiles")
      .select("role, ativo, deleted_at")
      .eq("id", user.id)
      .single();

    const isProfileAdmin =
      profile && profile.role === "admin" && profile.ativo === true && !profile.deleted_at;

    if (!isMetaAdmin && !isProfileAdmin) {
      return errorResponse(
        "Apenas administradores podem convidar novos usuários.",
        403,
        "forbidden"
      );
    }

    // 4. Recebe os dados da requisição
    const body = await req.json();
    const { email, role, redirectTo } = body;
    const cleanEmail = (email || "").trim().toLowerCase();

    if (!cleanEmail) {
      return errorResponse("E-mail não informado.", 400, "email_required");
    }

    // Determina a URL base para onde o usuário será redirecionado
    const requestOrigin = req.headers.get("origin");
    const baseUrl =
      Deno.env.get("SITE_URL") ||
      requestOrigin ||
      "https://peludinhosdovale.vercel.app";

    const finalRedirectTo = redirectTo || `${baseUrl.replace(/\/$/, "")}/definir-senha`;

    // 5. Fluxo de convite
    const { data: inviteData, error: inviteError } = await adminClient.auth.admin.inviteUserByEmail(
      cleanEmail,
      {
        redirectTo: finalRedirectTo,
        data: {
          role: role || "user",
        },
      }
    );

    if (inviteError) {
      const isAlreadyRegistered =
        inviteError.message?.toLowerCase().includes("already") ||
        inviteError.message?.toLowerCase().includes("registered") ||
        inviteError.status === 422;

      if (isAlreadyRegistered) {
        return errorResponse(
          "Este e-mail já está cadastrado no sistema.",
          409,
          "user_already_exists"
        );
      }

      return errorResponse(inviteError.message, 400, "invite_failed");
    }

    return successResponse(
      `Convite enviado com sucesso para ${cleanEmail}`,
      inviteData,
      200
    );
  } catch (err: any) {
    return errorResponse(
      err.message || "Erro interno no servidor.",
      500,
      "internal_server_error"
    );
  }
});
