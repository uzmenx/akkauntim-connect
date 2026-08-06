import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders } from "npm:@supabase/supabase-js@2/cors";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });

const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, "");

async function sha256(value: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { persistSession: false } },
  );

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Noto'g'ri so'rov" }, 400);
  }

  const action = String(body.action ?? "");

  // ---------- 1-qadam: login + server tekshirish ----------
  if (action === "verify") {
    const login = String(body.mt5_login ?? "").trim();
    const server = String(body.mt5_server ?? "").trim();

    if (!/^[A-Za-z0-9._-]{3,32}$/.test(login) || server.length < 3 || server.length > 64) {
      return json({ error: "Login yoki server formati noto'g'ri" }, 400);
    }

    // Brute-force cheklovi: 15 daqiqada 5 urinish
    const since = new Date(Date.now() - 15 * 60 * 1000).toISOString();
    const { count } = await admin
      .from("password_reset_tokens")
      .select("id", { count: "exact", head: true })
      .eq("mt5_login", login)
      .gte("created_at", since);

    if ((count ?? 0) >= 5) {
      return json({ error: "Juda ko'p urinish. 15 daqiqadan keyin qayta urinib ko'ring." }, 429);
    }

    const { data: settings } = await admin
      .from("bot_settings")
      .select("user_id, mt5_login, mt5_server")
      .eq("mt5_login", login)
      .maybeSingle();

    const match =
      settings?.user_id &&
      settings.mt5_server &&
      norm(settings.mt5_server) === norm(server);

    if (!match) {
      await admin.from("password_reset_tokens").insert({ mt5_login: login, success: false });
      return json({ error: "Login yoki server ma'lumotlari mos kelmadi" }, 400);
    }

    const token = crypto.randomUUID() + "." + crypto.randomUUID();
    const { error: insErr } = await admin.from("password_reset_tokens").insert({
      user_id: settings!.user_id,
      mt5_login: login,
      token_hash: await sha256(token),
      success: true,
    });
    if (insErr) return json({ error: "Server xatosi. Keyinroq urinib ko'ring." }, 500);

    return json({ token });
  }

  // ---------- 2-qadam: yangi parol qo'yish ----------
  if (action === "reset") {
    const token = String(body.token ?? "");
    const password = String(body.password ?? "");

    if (token.length < 20) return json({ error: "Tasdiqlash muddati tugagan" }, 400);
    if (password.length < 6 || password.length > 72) {
      return json({ error: "Parol kamida 6 belgidan iborat bo'lishi kerak" }, 400);
    }

    const { data: row } = await admin
      .from("password_reset_tokens")
      .select("id, user_id, mt5_login, expires_at, used_at")
      .eq("token_hash", await sha256(token))
      .maybeSingle();

    if (!row?.user_id || row.used_at || new Date(row.expires_at) < new Date()) {
      return json({ error: "Tasdiqlash muddati tugagan. Qaytadan boshlang." }, 400);
    }

    const { error: updErr } = await admin.auth.admin.updateUserById(row.user_id, { password });
    if (updErr) return json({ error: "Parolni yangilash muvaffaqiyatsiz: " + updErr.message }, 400);

    await admin
      .from("bot_settings")
      .update({ mt5_password: password })
      .eq("user_id", row.user_id);

    await admin
      .from("password_reset_tokens")
      .update({ used_at: new Date().toISOString() })
      .eq("id", row.id);

    return json({ ok: true, mt5_login: row.mt5_login });
  }

  return json({ error: "Noma'lum amal" }, 400);
});
