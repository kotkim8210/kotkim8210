const GRAPH_API_VERSION = "v21.0";
const GRAPH_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;

const TERMINAL_STATUS = new Set(["FINISHED", "ERROR", "EXPIRED", "PUBLISHED"]);
const SUCCESS_STATUS = new Set(["FINISHED", "PUBLISHED"]);

async function graphFetch(url, init = {}) {
  const res = await fetch(url, init);
  const text = await res.text();
  let body;
  try {
    body = text.length ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Graph API non-JSON response (${res.status}): ${text.slice(0, 300)}`);
  }
  if (!res.ok || body.error) {
    const err = body.error ?? {};
    const msg = err.message ?? text;
    const code = err.code ? ` [code=${err.code}]` : "";
    const sub = err.error_subcode ? ` [subcode=${err.error_subcode}]` : "";
    throw new Error(`Graph API ${res.status}${code}${sub}: ${msg}`);
  }
  return body;
}

export class InstagramClient {
  constructor({ accessToken, igUserId } = {}) {
    this.accessToken = accessToken ?? process.env.IG_ACCESS_TOKEN;
    this.igUserId = igUserId ?? process.env.IG_USER_ID;
    if (!this.accessToken) {
      throw new Error("IG_ACCESS_TOKEN 환경변수가 설정되어 있지 않습니다 (long-lived 60일 토큰 필요).");
    }
    if (!this.igUserId) {
      throw new Error("IG_USER_ID 환경변수가 설정되어 있지 않습니다 (Instagram Business Account ID 숫자).");
    }
  }

  async getAccountInfo() {
    const url = `${GRAPH_BASE}/${this.igUserId}?fields=id,username,name,followers_count&access_token=${encodeURIComponent(this.accessToken)}`;
    return graphFetch(url);
  }

  async createImageContainer(imageUrl, isCarouselItem = true) {
    const url = `${GRAPH_BASE}/${this.igUserId}/media`;
    const params = new URLSearchParams();
    params.set("image_url", imageUrl);
    if (isCarouselItem) params.set("is_carousel_item", "true");
    params.set("access_token", this.accessToken);
    const body = await graphFetch(url, { method: "POST", body: params });
    if (!body.id) throw new Error(`createImageContainer: 응답에 id 없음: ${JSON.stringify(body)}`);
    return body.id;
  }

  async createCarouselContainer(childContainerIds, caption) {
    if (!Array.isArray(childContainerIds) || childContainerIds.length < 2 || childContainerIds.length > 10) {
      throw new Error(`carousel children 수가 잘못됨 (2~10 필요, 받음: ${childContainerIds?.length}).`);
    }
    const url = `${GRAPH_BASE}/${this.igUserId}/media`;
    const params = new URLSearchParams();
    params.set("media_type", "CAROUSEL");
    params.set("children", childContainerIds.join(","));
    if (caption) params.set("caption", caption);
    params.set("access_token", this.accessToken);
    const body = await graphFetch(url, { method: "POST", body: params });
    if (!body.id) throw new Error(`createCarouselContainer: 응답에 id 없음: ${JSON.stringify(body)}`);
    return body.id;
  }

  async getContainerStatus(containerId) {
    const url = `${GRAPH_BASE}/${containerId}?fields=status_code,status&access_token=${encodeURIComponent(this.accessToken)}`;
    const body = await graphFetch(url);
    return { status_code: body.status_code, status: body.status };
  }

  async waitForContainer(containerId, { timeoutMs = 120000, intervalMs = 3000 } = {}) {
    const deadline = Date.now() + timeoutMs;
    let last;
    while (Date.now() < deadline) {
      last = await this.getContainerStatus(containerId);
      if (TERMINAL_STATUS.has(last.status_code)) {
        if (SUCCESS_STATUS.has(last.status_code)) return last;
        throw new Error(`container ${containerId} 비정상 종료: status_code=${last.status_code} status=${last.status ?? "(none)"}`);
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error(`container ${containerId} ${timeoutMs}ms 안에 FINISHED 도달 못함 (마지막: ${last?.status_code ?? "?"})`);
  }

  async publishMedia(containerId) {
    const url = `${GRAPH_BASE}/${this.igUserId}/media_publish`;
    const params = new URLSearchParams();
    params.set("creation_id", containerId);
    params.set("access_token", this.accessToken);
    const body = await graphFetch(url, { method: "POST", body: params });
    if (!body.id) throw new Error(`publishMedia: 응답에 id 없음: ${JSON.stringify(body)}`);

    // Try to fetch permalink (best-effort — non-fatal if it fails)
    let permalink = null;
    try {
      const pUrl = `${GRAPH_BASE}/${body.id}?fields=permalink&access_token=${encodeURIComponent(this.accessToken)}`;
      const pBody = await graphFetch(pUrl);
      permalink = pBody.permalink ?? null;
    } catch {
      /* ignore — media is published, permalink lookup is informational */
    }

    return { mediaId: body.id, permalink };
  }

  /**
   * 게시물 인사이트 조회 (A/B 비교용, best-effort).
   * reach/saved/total_interactions 는 insights endpoint, like/comment 는 노드 필드.
   */
  async getMediaInsights(mediaId) {
    const out = { mediaId, reach: null, likes: null, comments: null, saved: null, interactions: null, timestamp: null, permalink: null };
    try {
      const f = await graphFetch(`${GRAPH_BASE}/${mediaId}?fields=like_count,comments_count,timestamp,permalink&access_token=${encodeURIComponent(this.accessToken)}`);
      out.likes = f.like_count ?? null;
      out.comments = f.comments_count ?? null;
      out.timestamp = f.timestamp ?? null;
      out.permalink = f.permalink ?? null;
    } catch (e) {
      out.error = e.message;
    }
    try {
      const ins = await graphFetch(`${GRAPH_BASE}/${mediaId}/insights?metric=reach,saved,total_interactions&access_token=${encodeURIComponent(this.accessToken)}`);
      for (const d of ins.data ?? []) {
        const v = d.values?.[0]?.value;
        if (d.name === "reach") out.reach = v;
        else if (d.name === "saved") out.saved = v;
        else if (d.name === "total_interactions") out.interactions = v;
      }
    } catch (e) {
      out.insightsError = e.message;
    }
    return out;
  }
}

/**
 * Upload a 2-10 image carousel end-to-end.
 *
 * @param {InstagramClient} client
 * @param {string[]} imageUrls - Public HTTPS URLs (e.g., from imgbb)
 * @param {string} caption
 * @returns {Promise<{mediaId: string, permalink: string|null, childContainerIds: string[], carouselContainerId: string}>}
 */
export async function uploadCarousel(client, imageUrls, caption) {
  if (!Array.isArray(imageUrls) || imageUrls.length < 2) {
    throw new Error(`uploadCarousel: 이미지 URL 2개 이상 필요 (받음: ${imageUrls?.length}).`);
  }

  // 1. Create child containers in parallel
  console.log(`  [IG] creating ${imageUrls.length} child containers...`);
  const childContainerIds = await Promise.all(
    imageUrls.map((u) => client.createImageContainer(u, true)),
  );
  console.log(`  [IG] children: ${childContainerIds.join(", ")}`);

  // 2. Wait for all children to reach FINISHED
  console.log("  [IG] waiting for children to finish...");
  await Promise.all(childContainerIds.map((id) => client.waitForContainer(id)));

  // 3. Create carousel parent
  console.log("  [IG] creating carousel container...");
  const carouselContainerId = await client.createCarouselContainer(childContainerIds, caption);

  // 4. Wait for carousel container
  await client.waitForContainer(carouselContainerId);

  // 5. Publish
  console.log("  [IG] publishing...");
  const result = await client.publishMedia(carouselContainerId);
  return { ...result, childContainerIds, carouselContainerId };
}
