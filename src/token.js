import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";

const GRAPH_API_VERSION = "v21.0";
const GRAPH_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;

async function jsonFetch(url) {
  const res = await fetch(url);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`non-JSON 응답 (${res.status}): ${text.slice(0, 300)}`);
  }
  if (!res.ok || body.error) {
    const err = body.error ?? {};
    const e = new Error(`${err.message ?? text}`);
    e.code = err.code;
    throw e;
  }
  return body;
}

/**
 * 토큰 만료 시점 조회 (best-effort).
 * FB_APP_ID/FB_APP_SECRET 이 있으면 앱 토큰으로, 없으면 토큰 자신으로 debug_token 호출.
 * 실패해도 throw 하지 않고 null 반환 — preflight 는 참고용이므로.
 *
 * @returns {Promise<{isValid:boolean, expiresAt:Date|null, daysLeft:number|null}|null>}
 */
export async function debugToken(token, { appId, appSecret } = {}) {
  try {
    const accessToken = appId && appSecret ? `${appId}|${appSecret}` : token;
    const url = `${GRAPH_BASE.replace(`/${GRAPH_API_VERSION}`, "")}/debug_token?input_token=${encodeURIComponent(token)}&access_token=${encodeURIComponent(accessToken)}`;
    const body = await jsonFetch(url);
    const d = body.data ?? {};
    // expires_at=0 은 "만료 없음" (long-lived page token 등)
    const expiresAt = d.expires_at ? new Date(d.expires_at * 1000) : null;
    const daysLeft = expiresAt ? Math.floor((expiresAt.getTime() - Date.now()) / 86400000) : null;
    return { isValid: d.is_valid !== false, expiresAt, daysLeft };
  } catch {
    return null;
  }
}

/**
 * long-lived 토큰 갱신.
 * 1차: ig_refresh_token grant (Instagram Login 계열 토큰)
 * 2차: fb_exchange_token (Facebook Login 계열 — FB_APP_ID/SECRET 필요)
 *
 * @returns {Promise<{accessToken:string, expiresInSec:number, method:string}>}
 */
export async function refreshLongLivedToken(token, { appId, appSecret } = {}) {
  let firstErr;
  try {
    const url = `${GRAPH_BASE}/refresh_access_token?grant_type=ig_refresh_token&access_token=${encodeURIComponent(token)}`;
    const body = await jsonFetch(url);
    if (!body.access_token) throw new Error(`응답에 access_token 없음: ${JSON.stringify(body).slice(0, 200)}`);
    return { accessToken: body.access_token, expiresInSec: body.expires_in ?? 0, method: "ig_refresh_token" };
  } catch (err) {
    firstErr = err;
    if (err.code === 190) throw err; // 만료/revoke — 다른 방법으로도 불가
  }

  if (appId && appSecret) {
    const url = `${GRAPH_BASE}/oauth/access_token?grant_type=fb_exchange_token&client_id=${encodeURIComponent(appId)}&client_secret=${encodeURIComponent(appSecret)}&fb_exchange_token=${encodeURIComponent(token)}`;
    const body = await jsonFetch(url);
    if (!body.access_token) throw new Error(`fb_exchange_token 응답에 access_token 없음`);
    return { accessToken: body.access_token, expiresInSec: body.expires_in ?? 60 * 86400, method: "fb_exchange_token" };
  }

  throw new Error(
    `토큰 갱신 실패: ${firstErr.message}` +
    ` (FB Login 토큰이면 .env 에 FB_APP_ID/FB_APP_SECRET 추가 시 fb_exchange_token 방식 자동 시도)`,
  );
}

/**
 * .env 의 한 키를 새 값으로 교체 (없으면 append). 다른 줄은 그대로 보존.
 * @returns {Promise<{replaced:boolean}>}
 */
export async function updateEnvTokenLine(envPath, newValue, key = "IG_ACCESS_TOKEN") {
  let text = "";
  if (existsSync(envPath)) text = await readFile(envPath, "utf-8");
  const line = `${key}=${newValue}`;
  const re = new RegExp(`^${key}=.*$`, "m");
  let replaced = false;
  if (re.test(text)) {
    text = text.replace(re, line);
    replaced = true;
  } else {
    if (text.length && !text.endsWith("\n")) text += "\n";
    text += line + "\n";
  }
  await writeFile(envPath, text, "utf-8");
  return { replaced };
}
