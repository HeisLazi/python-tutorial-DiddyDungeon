import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
});
const MAX_PROMPT_CHARS = 24_000;
const MAX_TITLE_CHARS = 120;
const MAX_COMPLETION_TOKENS = 1_200;

function apiKeyFromRequest(req: Request): string {
  const supplied = req.headers.get("apikey") || "";
  if (supplied.startsWith("sb_publishable_") && supplied.length <= 512) return supplied;
  // Supabase keeps the legacy anon key available during the current key
  // migration window. New publishable keys are forwarded by the desktop app.
  return Deno.env.get("SUPABASE_ANON_KEY") || "";
}

async function resolveUser(req: Request): Promise<{ id: string; token: string; apiKey: string } | null> {
  const authorization = req.headers.get("authorization") || "";
  const token = authorization.match(/^Bearer\s+([^\s]+)$/i)?.[1] || "";
  const apiKey = apiKeyFromRequest(req);
  const projectUrl = Deno.env.get("SUPABASE_URL") || "";
  if (!token || token.length > 8_192 || !apiKey || !projectUrl.startsWith("https://")) return null;
  const response = await fetch(`${projectUrl}/auth/v1/user`, {
    headers: { apikey: apiKey, Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(8_000),
  });
  if (!response.ok) return null;
  const user = await response.json().catch(() => null);
  return typeof user?.id === "string" ? { id: user.id, token, apiKey } : null;
}

async function isPrivateHunterGroupMember(projectUrl: string, user: { id: string; token: string; apiKey: string }): Promise<boolean> {
  const query = new URLSearchParams({ select: "group_id", user_id: `eq.${user.id}`, limit: "1" });
  const response = await fetch(`${projectUrl}/rest/v1/hunter_group_members?${query}`, {
    headers: { apikey: user.apiKey, Authorization: `Bearer ${user.token}` },
    signal: AbortSignal.timeout(8_000),
  });
  if (!response.ok) return false;
  const rows = await response.json().catch(() => null);
  return Array.isArray(rows) && rows.length > 0;
}

async function consumeRequestQuota(projectUrl: string, user: { id: string; token: string; apiKey: string }): Promise<boolean> {
  const response = await fetch(`${projectUrl}/rest/v1/rpc/consume_pyr_ai_request`, {
    method: "POST",
    headers: { apikey: user.apiKey, Authorization: `Bearer ${user.token}`, "Content-Type": "application/json" },
    body: "{}",
    signal: AbortSignal.timeout(8_000),
  });
  if (!response.ok) return false;
  return await response.json().catch(() => false) === true;
}

function providerConfig() {
  const apiKey = Deno.env.get("PYR_AI_API_KEY") || "";
  // OpenCode Console exposes the OpenAI-compatible API at this endpoint.
  // OpenCode Go users can override this with its /inference/go/... endpoint.
  const baseUrl = (Deno.env.get("PYR_AI_BASE_URL") || "https://opencode.ai/inference/openai/v1").replace(/\/+$/, "");
  const model = Deno.env.get("PYR_AI_MODEL") || "deepseek-v4.1-flash";
  let parsed: URL;
  try {
    parsed = new URL(baseUrl);
  } catch {
    return null;
  }
  if (!apiKey || parsed.protocol !== "https:" || !model || model.length > 120) return null;
  return { apiKey, baseUrl, model, requiresSession: baseUrl.includes("/inference/go/") };
}

async function opencodeSessionId(userId: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(userId));
  const suffix = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("").slice(0, 32);
  return `ses_${suffix}`;
}

async function callProvider(prompt: string, title: string, userId: string) {
  const config = providerConfig();
  if (!config) return json({ error: "Shared AI provider is not configured." }, 503);
  const headers: Record<string, string> = { Authorization: `Bearer ${config.apiKey}`, "Content-Type": "application/json" };
  if (config.requiresSession) headers["x-opencode-session"] = await opencodeSessionId(userId);
  let response: Response;
  try {
    response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: config.model,
        messages: [
          { role: "system", content: "You are PYR, a text-only programming tutor. Do not use tools. Follow the supplied task and return only the requested answer." },
          { role: "user", content: `${title}\n\n${prompt}` },
        ],
        max_tokens: MAX_COMPLETION_TOKENS,
        temperature: 0.2,
      }),
      signal: AbortSignal.timeout(90_000),
    });
  } catch {
    return json({ error: "The shared AI provider could not be reached." }, 502);
  }
  if (!response.ok) {
    // Never relay provider response bodies: they can contain request details.
    return json({ error: response.status === 401 || response.status === 403
      ? "The shared AI provider key was rejected."
      : response.status === 429 ? "The shared AI provider is rate limited." : "The shared AI provider returned an error." }, 502);
  }
  const payload = await response.json().catch(() => null);
  const reply = payload?.choices?.[0]?.message?.content;
  const text = typeof reply === "string"
    ? reply
    : Array.isArray(reply) ? reply.map((part) => typeof part?.text === "string" ? part.text : "").join("") : "";
  if (!text.trim()) return json({ error: "The shared AI provider returned no answer." }, 502);
  return json({ reply: text.slice(0, 20_000), model: config.model });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "GET" && req.method !== "POST") return json({ error: "Method not allowed." }, 405);

  const user = await resolveUser(req).catch(() => null);
  if (!user) return json({ error: "Sign in to Quest Lab first." }, 401);

  const projectUrl = Deno.env.get("SUPABASE_URL") || "";
  const member = await isPrivateHunterGroupMember(projectUrl, user).catch(() => false);
  if (!member) return json({ error: "Join your private Hunter group to use shared PYR." }, 403);

  if (req.method === "GET") {
    const config = providerConfig();
    return json(config
      ? { ready: true, provider: "OpenCode", model: config.model, detail: "Shared PYR is ready for your Hunter group." }
      : { ready: false, provider: "OpenCode", detail: "The shared AI provider is not configured." }, config ? 200 : 503);
  }

  const length = Number(req.headers.get("content-length") || 0);
  if (length > 100_000) return json({ error: "Request is too large." }, 413);
  const body = await req.json().catch(() => null);
  const prompt = typeof body?.prompt === "string" ? body.prompt : "";
  const title = typeof body?.title === "string" ? body.title.slice(0, MAX_TITLE_CHARS) : "Quest Lab · PYR";
  if (!prompt.trim() || prompt.length > MAX_PROMPT_CHARS) return json({ error: "Invalid or oversized PYR prompt." }, 422);

  const withinQuota = await consumeRequestQuota(projectUrl, user).catch(() => false);
  if (!withinQuota) return json({ error: "PYR request limit reached or unavailable." }, 429);
  return await callProvider(prompt, title, user.id);
});
