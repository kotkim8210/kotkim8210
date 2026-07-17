import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { withRetry, TransientError } from "./retry.js";

const IMGBB_ENDPOINT = "https://api.imgbb.com/1/upload";

/**
 * Upload a local image file to imgbb and return its public CDN URL.
 * Uses base64 multipart payload (simplest, supports all image formats).
 *
 * 일시 오류(네트워크, 429 rate limit, 5xx)는 지수 백오프로 최대 4회 재시도.
 * 400(잘못된 키) 등 영구 오류는 즉시 실패.
 *
 * @param {string} localPath - Absolute path to local image file
 * @returns {Promise<string>} Public HTTPS URL (display_url, suitable for IG fetch)
 */
export async function uploadImage(localPath) {
  const apiKey = process.env.IMGBB_API_KEY;
  if (!apiKey) {
    throw new Error("IMGBB_API_KEY 환경변수가 설정되어 있지 않습니다 (https://api.imgbb.com/ 가입 후 API 키 발급).");
  }

  const buf = await readFile(localPath);
  const b64 = buf.toString("base64");

  return withRetry(async () => {
    const params = new URLSearchParams();
    params.set("key", apiKey);
    params.set("image", b64);
    params.set("name", basename(localPath));

    let res;
    try {
      res = await fetch(IMGBB_ENDPOINT, { method: "POST", body: params });
    } catch (err) {
      throw new TransientError(`imgbb 네트워크 오류: ${err.message}`, err);
    }

    if (!res.ok) {
      const text = await res.text().catch(() => "(body unavailable)");
      const msg = `imgbb upload failed: ${res.status} ${res.statusText}\n${text.slice(0, 300)}`;
      // 429(rate limit)·5xx 는 일시 오류 → 재시도, 그 외(400 잘못된 키 등)는 영구 실패
      if (res.status === 429 || res.status >= 500) throw new TransientError(msg);
      throw new Error(msg);
    }

    const json = await res.json();
    if (!json.success || !json.data?.display_url) {
      throw new Error(`imgbb response missing display_url: ${JSON.stringify(json).slice(0, 300)}`);
    }
    return json.data.display_url;
  }, { label: "imgbb" });
}
