/**
 * Fandom API Proxy for Deno Deploy.
 * Forwards MediaWiki API requests to Fandom wikis, bypassing Cloudflare bot protection.
 *
 * Usage:
 *   GET /?wikiname=dontstarve&action=query&list=search&srsearch=Wilson&format=json
 *   GET /page?wikiname=dontstarve&title=Wilson&format=markdown
 *
 * Deno Deploy runs on Google Cloud IPs, which are not blocked by Fandom's Cloudflare.
 */
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

  // Health check
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

  // Build target URL
  const fandomUrl = new URL(`https://${wikiname}.fandom.com/api.php`);
  for (const [key, value] of params.entries()) {
    if (key !== "wikiname") {
      fandomUrl.searchParams.append(key, value);
    }
  }
  if (!fandomUrl.searchParams.has("format")) {
    fandomUrl.searchParams.set("format", "json");
  }

  try {
    const fandomRes = await fetch(fandomUrl.toString(), {
      headers: { "User-Agent": USER_AGENT },
    });

    const body = await fandomRes.arrayBuffer();
    const ct = fandomRes.headers.get("content-type") || "application/json";

    return new Response(body, {
      status: fandomRes.status,
      headers: { ...corsHeaders(), "Content-Type": ct },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "Failed to fetch from Fandom", details: String(err) }),
      { status: 502, headers: { ...corsHeaders(), "Content-Type": "application/json" } }
    );
  }
}

// Deno Deploy entry point
Deno.serve(handler);
