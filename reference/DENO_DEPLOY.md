# Deno Proxy Reference

This reference explains how to register Deno Deploy, deploy the Fandom proxy, and what code to use.

## 1. Register

1. Open `https://dash.deno.com/`
2. Sign in with GitHub or Google
3. Create a new app or playground
4. Copy the public deployment URL (for example, `https://burly-cobra-71.kjx-talesofai.deno.net`)

## 2. Deploy

Use a simple Deno HTTP server that forwards Fandom MediaWiki API requests:

- Input: `/?wikiname=<wiki>&action=query&...`
- Output: proxied JSON from `https://<wiki>.fandom.com/api.php?...`

Set `FANDOM_PROXY_URL` in the runtime environment to the deployed URL.

## 3. Code

Use this as the deployment entrypoint:

```ts
const USER_AGENT = "FandomProxy/1.0 (Deno Deploy; research bot)";

function corsHeaders(): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

async function handler(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const params = url.searchParams;
  const wikiname = params.get("wikiname");

  if (url.pathname === "/health") {
    return new Response(JSON.stringify({ status: "ok" }), {
      headers: { ...corsHeaders(), "Content-Type": "application/json" },
    });
  }

  if (!wikiname) {
    return new Response(
      JSON.stringify({
        error: "Missing wikiname parameter",
        usage: "GET /?wikiname=dontstarve&action=query&list=search&srsearch=Wilson&format=json",
      }),
      { status: 400, headers: { ...corsHeaders(), "Content-Type": "application/json" } }
    );
  }

  const fandomUrl = new URL(`https://${wikiname}.fandom.com/api.php`);
  for (const [key, value] of params.entries()) {
    if (key !== "wikiname") fandomUrl.searchParams.append(key, value);
  }
  if (!fandomUrl.searchParams.has("format")) fandomUrl.searchParams.set("format", "json");

  const fandomRes = await fetch(fandomUrl.toString(), {
    headers: { "User-Agent": USER_AGENT },
  });

  const body = await fandomRes.arrayBuffer();
  const contentType = fandomRes.headers.get("content-type") || "application/json";
  return new Response(body, {
    status: fandomRes.status,
    headers: { ...corsHeaders(), "Content-Type": contentType },
  });
}

Deno.serve(handler);
```

## 4. Environment

Set:

```bash
export FANDOM_PROXY_URL="https://your-deno-url.deno.net"
```

The fandom CLI reads this environment variable at runtime.
