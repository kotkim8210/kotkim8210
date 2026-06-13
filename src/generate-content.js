import Anthropic from "@anthropic-ai/sdk";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SYSTEM_PROMPT_PATH = join(__dirname, "prompts", "content-generator.md");

const DEFAULT_MODEL = "claude-sonnet-4-6";
const MAX_PAUSE_TURN_RETRIES = 5;

let cachedSystemPrompt = null;

async function loadSystemPrompt() {
  if (cachedSystemPrompt === null) {
    cachedSystemPrompt = await readFile(SYSTEM_PROMPT_PATH, "utf-8");
  }
  return cachedSystemPrompt;
}

function extractJsonFromText(text) {
  const trimmed = text.trim();
  const fenceMatch = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/);
  const candidate = fenceMatch ? fenceMatch[1] : trimmed;

  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    throw new Error("응답에서 JSON 객체를 찾지 못했습니다.\n원본:\n" + text);
  }
  const jsonStr = candidate.slice(start, end + 1);

  try {
    return JSON.parse(jsonStr);
  } catch (err) {
    throw new Error(
      `JSON 파싱 실패: ${err.message}\n응답 일부:\n${jsonStr.slice(0, 500)}...`,
    );
  }
}

function getFinalText(message) {
  for (let i = message.content.length - 1; i >= 0; i--) {
    const block = message.content[i];
    if (block.type === "text" && block.text.trim().length > 0) {
      return block.text;
    }
  }
  throw new Error("응답에 텍스트 블록이 없습니다.");
}

export async function generateContent(topic, { model = DEFAULT_MODEL } = {}) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error("ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.");
  }

  const client = new Anthropic();
  const systemPrompt = await loadSystemPrompt();

  const messages = [
    {
      role: "user",
      content: `주제: ${topic}\n\n위 주제로 인포그래픽 캐러셀 JSON을 생성하세요. 필요하면 web_search로 최신 데이터를 확인하세요.`,
    },
  ];

  const requestParams = {
    model,
    max_tokens: 8192,
    system: [
      {
        type: "text",
        text: systemPrompt,
        cache_control: { type: "ephemeral" },
      },
    ],
    tools: [
      {
        type: "web_search_20260209",
        name: "web_search",
        max_uses: 5,
      },
    ],
    messages,
  };

  let response = await client.messages.create(requestParams);

  let pauseRetries = 0;
  while (response.stop_reason === "pause_turn") {
    if (pauseRetries >= MAX_PAUSE_TURN_RETRIES) {
      throw new Error(
        `web_search 도구가 반복 한도(${MAX_PAUSE_TURN_RETRIES}회 재개)를 초과했습니다.`,
      );
    }
    messages.push({ role: "assistant", content: response.content });
    response = await client.messages.create({ ...requestParams, messages });
    pauseRetries++;
  }

  if (response.stop_reason === "refusal") {
    throw new Error("모델이 응답을 거부했습니다 (stop_reason=refusal).");
  }

  const usage = response.usage ?? {};
  const cacheRead = usage.cache_read_input_tokens ?? 0;
  const cacheWrite = usage.cache_creation_input_tokens ?? 0;
  console.log(
    `[generate-content] tokens in/out=${usage.input_tokens ?? "?"}/${usage.output_tokens ?? "?"} cache read/write=${cacheRead}/${cacheWrite}`,
  );

  const text = getFinalText(response);
  return extractJsonFromText(text);
}
