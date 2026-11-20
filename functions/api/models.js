export async function onRequestGet({ env }) {
  if (!env.DB) {
    return new Response(
      JSON.stringify({
        error: "Cloudflare D1 database binding 'DB' is not configured yet.",
        docs: "Bind 'DB' in Cloudflare Dashboard -> Pages -> Settings -> Functions -> D1 Database Bindings",
      }),
      {
        status: 503,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }

  try {
    const { results } = await env.DB.prepare(
      "SELECT id, name, intelligence_score FROM models ORDER BY name ASC"
    ).all();

    return new Response(JSON.stringify({ models: results }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=300, s-maxage=300",
      },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  }
}
