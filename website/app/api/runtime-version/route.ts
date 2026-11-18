export const dynamic = 'force-dynamic';

export async function GET() {
  const target = process.env.API_PROXY_TARGET || 'https://api.yance.ai';
  try {
    const response = await fetch(`${target.replace(/\/$/, '')}/api/v1/system/version`, {
      cache: 'no-store', signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return Response.json({error:'运行版本暂不可用'}, {status:503});
    const version = await response.json();
    return Response.json({application_version:version.application_version,
      source_revision:version.source_revision,
      database_revisions:version.database_revisions}, {headers:{'Cache-Control':'no-store'}});
  } catch {
    return Response.json({error:'运行版本暂不可用'}, {status:503});
  }
}
