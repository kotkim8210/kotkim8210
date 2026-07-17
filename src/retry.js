/**
 * 지수 백오프 재시도 헬퍼.
 *
 * 일시 오류(네트워크 끊김, 429, 5xx, Graph 스로틀 코드)는 err.transient=true 로
 * 표시하고, withRetry 가 2s → 4s → 8s → 16s 간격으로 재시도한다.
 * 영구 오류(잘못된 키, 권한, 만료 토큰)는 즉시 throw.
 */

const defaultSleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 일시 오류 표시용 — cause 를 보존한다. */
export class TransientError extends Error {
  constructor(message, cause) {
    super(message);
    this.name = "TransientError";
    this.transient = true;
    if (cause) this.cause = cause;
  }
}

export function isTransient(err) {
  return err?.transient === true;
}

/**
 * @param {(attempt:number)=>Promise<any>} fn - 시도할 작업 (attempt 는 0부터)
 * @param {object} [opts]
 * @param {number}   [opts.retries=4]       최대 재시도 횟수 (총 시도 = retries+1)
 * @param {number}   [opts.baseDelayMs=2000] 첫 재시도 대기
 * @param {number}   [opts.factor=2]         백오프 배수
 * @param {(err)=>boolean} [opts.shouldRetry=isTransient]
 * @param {(err,attempt,delayMs)=>void} [opts.onRetry] 재시도 직전 콜백 (기본: console.warn)
 * @param {(ms:number)=>Promise} [opts.sleepFn]        테스트 주입용
 * @param {string}   [opts.label]            로그 접두어
 */
export async function withRetry(fn, opts = {}) {
  const {
    retries = 4,
    baseDelayMs = 2000,
    factor = 2,
    shouldRetry = isTransient,
    sleepFn = defaultSleep,
    label = "",
    onRetry = (err, attempt, delayMs) =>
      console.warn(`  [retry${label ? ":" + label : ""}] ${err.message} → ${delayMs / 1000}s 후 재시도 (${attempt}/${retries})`),
  } = opts;

  let attempt = 0;
  for (;;) {
    try {
      return await fn(attempt);
    } catch (err) {
      attempt++;
      if (attempt > retries || !shouldRetry(err)) throw err;
      const delayMs = baseDelayMs * factor ** (attempt - 1);
      onRetry(err, attempt, delayMs);
      await sleepFn(delayMs);
    }
  }
}
