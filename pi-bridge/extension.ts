// Pi bridge — HW4 Pi Memory System
// 修改項目：
//   1. Windows Python fallback (python3 → python on win32)
//   2. before_agent_start 強化 injection prompt (system-style constraint)
//   3. remember tool 繼承 PI_MEMORY_PATH / PYTHON env，失敗時顯示 stderr
//   4. callMemory 加 debug log 到 stderr
//   5. 支援 $env:PI_MEMORY_PATH 固定 demo memory 路徑
//
// 執行方式（務必在作業 repo 根目錄）：
//   $env:PYTHON = "python"
//   $env:PYTHONPATH = "."
//   $env:PI_MEMORY_PATH = "$PWD\demo-memory.json"
//   pi -e ./pi-bridge/extension.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawnSync } from "node:child_process";

// Windows fallback: use "python" if "python3" is not available
const PY = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");

// Repo root: parent directory of this extension file
// On Windows, URL.pathname gives "/E:/path/..." with URL-encoded spaces — decode and strip leading slash
const REPO_ROOT_RAW = new URL("..", import.meta.url).pathname;
const REPO_ROOT = process.platform === "win32"
  ? decodeURIComponent(REPO_ROOT_RAW.replace(/^\//, "").replace(/\//g, "\\"))
  : decodeURIComponent(REPO_ROOT_RAW);

// Debug: print resolved REPO_ROOT at startup
console.error(`[pi-memory] REPO_ROOT: ${REPO_ROOT}`);
console.error(`[pi-memory] PY: ${PY}`);
console.error(`[pi-memory] PI_MEMORY_PATH env: ${process.env.PI_MEMORY_PATH ?? "(not set)"}`);
console.error(`[pi-memory] PYTHONPATH env: ${process.env.PYTHONPATH ?? "(not set)"}`);

function callMemory(args: string[]): { stdout: string; stderr: string; ok: boolean } {
  // Inherit PI_MEMORY_PATH so demo-memory.json is used when set
  const env: Record<string, string> = {
    ...process.env as Record<string, string>,
    PYTHONPATH: REPO_ROOT,
  };
  if (process.env.PI_MEMORY_PATH) {
    env.PI_MEMORY_PATH = process.env.PI_MEMORY_PATH;
  }

  const r = spawnSync(PY, ["-m", "memory.cli", ...args], {
    encoding: "utf8",
    cwd: REPO_ROOT,
    env,
  });

  const stdout = (r.stdout ?? "").trim();
  const stderr = (r.stderr ?? "").trim();
  const ok = r.status === 0;

  // Debug log always goes to process stderr so it's visible in terminal
  console.error(`[pi-memory] cmd: ${PY} -m memory.cli ${args.join(" ")}`);
  console.error(`[pi-memory] exit: ${r.status}`);
  if (stdout) console.error(`[pi-memory] stdout: ${stdout}`);
  if (stderr) console.error(`[pi-memory] stderr: ${stderr}`);

  return { stdout, stderr, ok };
}

export default function (pi: ExtensionAPI) {
  // ── Inject: retrieve relevant memory before agent starts ──
  pi.on("before_agent_start", async (event, _ctx) => {
    const query: string = event.prompt ?? "";
    console.error(`[pi-memory] before_agent_start fired`);
    console.error(`[pi-memory] query: ${query}`);
    if (!query) return;

    const { stdout: memo, ok } = callMemory(["inject", "--query", query, "--budget", "2000"]);
    console.error(`[pi-memory] inject ok: ${ok}, memo empty: ${!memo}`);
    if (!memo || !memo.trim()) return;

    console.error(`[pi-memory] inject stdout:\n${memo}`);

    const strengthened = `\
SYSTEM MEMORY — MUST FOLLOW

The following memory was retrieved from previous sessions.
Treat it as authoritative project context.
Use it to answer the user's current request.
Do not contradict it. Do not ignore it.

${memo}

Rules:
- If the user asks what command to use, answer from the retrieved memory above.
- If the retrieved memory says to use pnpm, do NOT answer npm.
- Do not run tools unless the user explicitly asks you to execute commands.
- If the user asks for the test command, answer with only the command from memory.
`;

    return {
      message: {
        customType: "pi-memory",
        content: strengthened,
        display: true,
      },
    };
  });

  // ── Remember tool: persist a fact to memory ──
  pi.registerTool({
    name: "remember",
    label: "Remember",
    description:
      "When the user states a durable project convention, preference, or important " +
      "fact that should persist across sessions, call this to remember it.",
    promptGuidelines: [
      "Use remember when the user states a durable project convention, preference, or fact worth keeping across sessions.",
    ],
    parameters: Type.Object({
      summary: Type.String({ description: "The fact to remember, one sentence." }),
      // Accept string OR array — llama3.2 sometimes passes tags as a JSON string
      tags: Type.Optional(Type.Union([Type.Array(Type.String()), Type.String()])),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      // Normalise tags: could be string "tag1,tag2", JSON array string "[a,b]", or actual array
      let rawTags: string[] = [];
      if (Array.isArray(params.tags)) {
        rawTags = params.tags;
      } else if (typeof params.tags === "string" && params.tags.trim()) {
        // Strip brackets if model passed "[a, b, c]" as a string
        const cleaned = params.tags.replace(/^\[|\]$/g, "");
        rawTags = cleaned.split(",").map((t) => t.trim()).filter(Boolean);
      }
      const tags = rawTags.join(",");
      const { stdout, stderr, ok } = callMemory(
        tags
          ? ["capture", "--summary", params.summary, "--tags", tags]
          : ["capture", "--summary", params.summary]
      );

      const memPath = process.env.PI_MEMORY_PATH ?? "~/.pi-memory.json";

      if (!ok) {
        const msg = `[pi-memory] capture FAILED\nstderr: ${stderr || "(none)"}`;
        console.error(msg);
        return {
          content: [{ type: "text", text: `Failed to remember: ${params.summary}\n${stderr}` }],
          details: {},
        };
      }

      const successMsg = stdout || `Remembered: ${params.summary}\n(stored in: ${memPath})`;
      return {
        content: [{ type: "text", text: successMsg }],
        details: {},
      };
    },
  });
}
