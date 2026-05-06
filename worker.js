// VoxTerrae — Cloudflare Worker
// voxterrae.app — Multilingual geospatial voice intelligence platform
// Author: Indica Independent Media (https://osintnet.uk)
// License: MIT
//
// Stack: Cloudflare Workers + Claude 3.5 Sonnet + D1 + KV
//
// Required bindings (wrangler.toml):
//   ANTHROPIC_API_KEY — Worker Secret
//   DB — D1 Database (voxterrae-db)
//   VOXTERRAE_KV — KV Namespace

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });

    if (url.pathname === '/api/reports') return handleReports(request, env, cors);
    if (url.pathname === '/api/submit') return handleSubmit(request, env, cors);
    if (url.pathname === '/api/translate') return handleTranslate(request, env, cors);
    if (url.pathname === '/api/synthesize') return handleSynthesize(request, env, cors);

    return new Response('VoxTerrae', { headers: { 'Content-Type': 'text/plain' } });
  }
};

async function handleReports(request, env, cors) {
  const { results } = await env.DB.prepare(
    'SELECT * FROM reports WHERE status = ? ORDER BY created_at DESC LIMIT 100'
  ).bind('active').all();
  return new Response(JSON.stringify(results), {
    headers: { ...cors, 'Content-Type': 'application/json' }
  });
}

async function handleSubmit(request, env, cors) {
  const { text, lat, lon, language, region } = await request.json();
  // Translate if needed, then store
  const translated = language !== 'en' ? await translateText(text, language, env) : text;
  await env.DB.prepare(
    'INSERT INTO reports (content_original, content_translated, lat, lon, language, region, status, created_at) VALUES (?,?,?,?,?,?,?,?)'
  ).bind(text, translated, lat, lon, language, region, 'active', new Date().toISOString()).run();
  return new Response(JSON.stringify({ success: true }), {
    headers: { ...cors, 'Content-Type': 'application/json' }
  });
}

async function translateText(text, lang, env) {
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022', max_tokens: 512,
      messages: [{ role: 'user', content: \`Translate to English: "\${text}" (source: \${lang}). Return only the translation.\` }]
    })
  });
  const d = await r.json();
  return d?.content?.[0]?.text || text;
}

async function handleTranslate(request, env, cors) {
  const { text, from_lang } = await request.json();
  const translated = await translateText(text, from_lang, env);
  return new Response(JSON.stringify({ translated }), {
    headers: { ...cors, 'Content-Type': 'application/json' }
  });
}

async function handleSynthesize(request, env, cors) {
  const { region, question } = await request.json();
  const { results } = await env.DB.prepare(
    'SELECT content_translated, region, created_at FROM reports WHERE region LIKE ? ORDER BY created_at DESC LIMIT 20'
  ).bind(\`%\${region}%\`).all();
  
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022', max_tokens: 1024,
      messages: [{ role: 'user', content: \`Based on these community reports from \${region}, answer: "\${question}". Reports: \${JSON.stringify(results)}\` }]
    })
  });
  const d = await r.json();
  return new Response(JSON.stringify({ answer: d?.content?.[0]?.text }), {
    headers: { ...cors, 'Content-Type': 'application/json' }
  });
}
