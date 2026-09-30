# Demo: Cross-Session Memory Recall

This demo shows the Pi Memory System's **Capture → Store → Retrieve → Inject** pipeline working across two sessions.

Session A tells the agent a project convention. Session B starts fresh — the agent remembers it automatically via injected memory, without being told again.

---

## Environment Setup

```powershell
cd "E:\USER\NKUST\4-2\Generative AI Application Systems and Engineering\HW4"

$env:PYTHON         = "python"
$env:PYTHONPATH     = "."
$env:PI_MEMORY_PATH = "$PWD\demo-memory.json"

Remove-Item "$env:PI_MEMORY_PATH" -ErrorAction SilentlyContinue
Test-Path "$env:PI_MEMORY_PATH"
# Expected: False
```

---

## Step 1 — Session A: Tell the agent the project rule

```powershell
pi -e ./pi-bridge/extension.ts
```

Input to Pi:
```
Please use the remember tool to remember this project rule: this project uses pnpm, not npm. The test command is pnpm test.
```

Expected Pi output:
```
remember
Remembered: This project uses pnpm, not npm. The test command is pnpm test.
```

Then type `/exit`.

---

## Step 2 — Verify memory was persisted

```powershell
Get-Content "$env:PI_MEMORY_PATH" -Encoding UTF8
```

Expected: JSON array containing `"pnpm test"`.

---

## Step 3 — Verify inject output

```powershell
python -m memory.cli inject --query "run project tests" --budget 2000
```

Expected:
```
[記憶 - 來自過去的 session]
- This project uses pnpm, not npm. The test command is pnpm test.
```

---

## Step 4 — Session B: Agent answers from memory (no re-telling)

```powershell
pi -e ./pi-bridge/extension.ts
```

Input to Pi:
```
Do not execute any commands. Just tell me: what is the test command for this project?
```

Terminal shows injection fired:
```
[pi-memory] before_agent_start fired
[pi-memory] exit: 0
[pi-memory] stdout: [記憶 - 來自過去的 session]
- This project uses pnpm, not npm. The test command is pnpm test.
```

Expected agent answer:
```
The test command is pnpm test.
```

✅ Agent answered correctly from cross-session memory — without being told again in Session B.

---

## Demo Video

Demo video: https://youtu.be/Yhh-RkFCPe0
