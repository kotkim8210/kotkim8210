import "dotenv/config";

const GRAPH_API_VERSION = "v21.0";

async function main() {
  const current = process.env.IG_ACCESS_TOKEN;
  if (!current) {
    console.error("IG_ACCESS_TOKEN 이 .env 에 없습니다.");
    process.exit(1);
  }

  const url = `https://graph.facebook.com/${GRAPH_API_VERSION}/refresh_access_token?grant_type=ig_refresh_token&access_token=${encodeURIComponent(current)}`;

  console.log("[refresh-token] 현재 토큰으로 갱신 요청 중...");
  const res = await fetch(url);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    console.error(`[refresh-token] non-JSON 응답 (${res.status}): ${text.slice(0, 300)}`);
    process.exit(1);
  }

  if (!res.ok || body.error) {
    const err = body.error ?? {};
    console.error(`[refresh-token] 실패 (${res.status}): ${err.message ?? text}`);
    if (err.code === 190) {
      console.error("        토큰이 만료됐거나 revoke 됐습니다. Graph API Explorer 에서 재발급 필요.");
      console.error("        → docs/instagram-setup.md 의 '토큰 재발급' 섹션 참고");
    }
    process.exit(1);
  }

  if (!body.access_token) {
    console.error(`[refresh-token] 응답에 access_token 없음: ${JSON.stringify(body)}`);
    process.exit(1);
  }

  const expiresInSec = body.expires_in ?? 0;
  const expiresInDays = Math.round(expiresInSec / 86400);
  const expiresAt = new Date(Date.now() + expiresInSec * 1000);

  console.log("\n=== 새 long-lived 토큰 ===");
  console.log(`expires_in: ${expiresInSec}s (~${expiresInDays}일)`);
  console.log(`expires_at: ${expiresAt.toISOString()}`);
  console.log("\n--- 새 토큰 (이 줄을 .env 의 IG_ACCESS_TOKEN 에 복사) ---");
  console.log(body.access_token);
  console.log("---\n");
  console.log("⚠️  .env 파일은 자동 수정되지 않습니다 — 수동으로 IG_ACCESS_TOKEN= 값을 위 토큰으로 교체하세요.");
}

main().catch((err) => {
  console.error("[refresh-token] fatal:", err.message);
  process.exit(1);
});
