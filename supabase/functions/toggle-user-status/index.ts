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

    // 3. Obtém o perfil de quem está chamando a função
    const { data: requesterProfile } = await adminClient
      .from("profiles")
      .select("role, ativo, deleted_at")
      .eq("id", user.id)
      .single();

    const isRequesterActive =
      requesterProfile && requesterProfile.ativo === true && !requesterProfile.deleted_at;

    const isAdmin =
      user.app_metadata?.role === "admin" ||
      user.user_metadata?.role === "admin" ||
      (requesterProfile?.role === "admin" && isRequesterActive);

    // 4. Recebe os parâmetros
    const body = await req.json();
    const { userId, ativo } = body;
    const targetUserId = userId || user.id; // Se não informado, assume a própria conta

    if (typeof ativo !== "boolean") {
      return errorResponse(
        "Parâmetro 'ativo' (booleano) não informado ou inválido.",
        400,
        "invalid_parameters"
      );
    }

    const isSelf = user.id === targetUserId;

    // 5. Validação de Permissões:
    // - Para ATIVAR uma conta: Apenas administradores podem ativar
    if (ativo === true && !isAdmin) {
      return errorResponse(
        "Apenas administradores podem reativar contas.",
        403,
        "forbidden"
      );
    }

    // - Para DESATIVAR outra conta que não a sua: Apenas administradores
    if (!isSelf && !isAdmin) {
      return errorResponse(
        "Você não tem permissão para alterar o status de outro usuário.",
        403,
        "forbidden"
      );
    }

    // - Se for auto-desativação de um admin, verifica se não é o único admin ativo no sistema
    if (isSelf && !ativo && isAdmin) {
      const { count: activeAdminsCount } = await adminClient
        .from("profiles")
        .select("id", { count: "exact", head: true })
        .eq("role", "admin")
        .eq("ativo", true)
        .is("deleted_at", null);

      if (activeAdminsCount !== null && activeAdminsCount <= 1) {
        return errorResponse(
          "Você é o único administrador ativo do sistema. Promova outro usuário a administrador antes de desativar sua conta.",
          400,
          "sole_admin_deactivation_blocked"
        );
      }
    }

    // 6. Atualiza o status na tabela profiles
    const { error: profileError } = await adminClient
      .from("profiles")
      .update({ ativo })
      .eq("id", targetUserId);

    if (profileError) {
      return errorResponse(profileError.message, 400, "database_update_failed");
    }

    // 7. Atualiza o ban no Supabase Auth
    // ban_duration = '876000h' (100 anos) para desativar, 'none' para reativar
    const { error: authUpdateError } = await adminClient.auth.admin.updateUserById(targetUserId, {
      ban_duration: ativo ? "none" : "876000h",
    });

    if (authUpdateError) {
      return errorResponse(authUpdateError.message, 400, "auth_update_failed");
    }

    const actionText = ativo ? "ativado" : "desativado";
    return successResponse(
      isSelf && !ativo
        ? "Sua conta foi desativada com sucesso."
        : `Usuário ${actionText} com sucesso.`,
      { userId: targetUserId, ativo },
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
