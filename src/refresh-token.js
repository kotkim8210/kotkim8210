import "dotenv/config";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { refreshLongLivedToken, debugToken, updateEnvTokenLine } from "./token.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ENV_PATH = join(__dirname, "..", ".env");

async function main() {
  const writeEnv = process.argv.includes("--write");
  const current = process.env.IG_ACCESS_TOKEN;
  if (!current) {
    console.error("IG_ACCESS_TOKEN 이 .env 에 없습니다.");
    process.exit(1);
  }

  console.log("[refresh-token] 현재 토큰으로 갱신 요청 중...");
  let result;
  try {
    result = await refreshLongLivedToken(current, {
      appId: process.env.FB_APP_ID,
      appSecret: process.env.FB_APP_SECRET,
    });
  } catch (err) {
    console.error(`[refresh-token] 실패: ${err.message}`);
    if (err.code === 190) {
      console.error("        토큰이 만료됐거나 revoke 됐습니다. Graph API Explorer 에서 재발급 필요.");
      console.error("        → docs/instagram-setup.md 의 '토큰 재발급' 섹션 참고");
    }
    process.exit(1);
  }

  const expiresInDays = Math.round(result.expiresInSec / 86400);
  const expiresAt = new Date(Date.now() + result.expiresInSec * 1000);

  console.log(`\n=== 새 long-lived 토큰 (${result.method}) ===`);
  console.log(`expires_in: ${result.expiresInSec}s (~${expiresInDays}일)`);
  console.log(`expires_at: ${expiresAt.toISOString()}`);

  if (writeEnv) {
    const { replaced } = await updateEnvTokenLine(ENV_PATH, result.accessToken);
    console.log(`\n✓ .env 의 IG_ACCESS_TOKEN ${replaced ? "교체" : "추가"} 완료 (--write)`);
  } else {
    console.log("\n--- 새 토큰 (이 줄을 .env 의 IG_ACCESS_TOKEN 에 복사) ---");
    console.log(result.accessToken);
    console.log("---\n");
    console.log("팁: `npm run refresh-token -- --write` 로 실행하면 .env 를 자동으로 갱신합니다.");
  }

  // 갱신 후 만료일 확인 (best-effort)
  const dbg = await debugToken(result.accessToken, {
    appId: process.env.FB_APP_ID,
    appSecret: process.env.FB_APP_SECRET,
  });
  if (dbg?.expiresAt) console.log(`확인된 만료일: ${dbg.expiresAt.toISOString()} (${dbg.daysLeft}일 남음)`);
}

main().catch((err) => {
  console.error("[refresh-token] fatal:", err.message);
  process.exit(1);
});
