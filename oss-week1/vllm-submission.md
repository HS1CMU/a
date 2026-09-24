# vLLM submission: Anthropic `/v1/messages` rejects `tools: []` with an `--enable-auto-tool-choice` error

Nothing has been posted to GitHub. Everything below is local.

- Repo: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/vllm`
- Branch: `fix/anthropic-empty-tools` (based on `main` @ e78e367c6)
- Commit: `c90838dd01056bf85972b1d78592a639019af8f3`
- MRE: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/mre/mre_empty_tools.py`
- Repro was CPU-only (no GPU in the container). See "Honesty notes" at the end.

## Candidate triage (why this bug and not the suggested ones)

| Issue | Status | Outcome |
|---|---|---|
| #57997 `/v1/messages` inconsistent error envelopes | open, but fix PR #58023 already open (Sep 21) | skipped, duplicate |
| #57725 malformed structured-output spec -> HTTP 500 | open; filed against 0.27.1 | at HEAD the validation path already raises `VLLMValidationError` everywhere and `AsyncLLM.generate` passes `VLLMClientError` through; #57743 also open. Skipped |
| #58246 Anthropic SDK 1.x test incompat | open, fix PR #57780 already linked | skipped, duplicate |
| #58144 `--api-key` bypassed by `/invocations` | fix PRs #58341 / #58028 open | skipped, duplicate |
| #58191 watermark per-request opt-out | fix PR #58202 open | skipped, duplicate |
| #58135 `/score` unicode truncation | fix PR #58137 open | skipped, duplicate |
| (this) `tools: []` on `/v1/messages` | **no existing issue or PR found** (searched issues for `anthropic messages tools "enable-auto-tool-choice"` and PRs for `anthropic empty tools`) | fixed here |

---

## (a) New issue draft (no existing issue found)

**Title:** `[Bug]: /v1/messages with tools: [] fails with '"auto" tool choice requires --enable-auto-tool-choice' on servers without a tool parser`

### Your current environment

<details>
<summary>The output of <code>python collect_env.py</code></summary>

```text
Collecting environment information...
uv is set
==============================
        System Info
==============================
OS                           : Ubuntu 24.04.4 LTS (x86_64)
GCC version                  : (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
Clang version                : 18.1.3 (1ubuntu1)
CMake version                : version 3.28.3
Libc version                 : glibc-2.39

==============================
       PyTorch Info
==============================
PyTorch version              : 2.13.0+cu130
Is debug build               : False
CUDA used to build PyTorch   : 13.0
ROCM used to build PyTorch   : N/A
XPU used to build PyTorch    : N/A

==============================
      Python Environment
==============================
Python version               : 3.11.15 (main, Mar  3 2026, 09:26:23) [GCC 13.3.0] (64-bit runtime)
Python platform              : Linux-6.18.44-fc-v37-x86_64-with-glibc2.39
    
==============================
       CUDA / GPU Info
==============================
Is CUDA available            : False
CUDA runtime version         : No CUDA
CUDA_MODULE_LOADING set to   : N/A
GPU models and configuration : No CUDA
Nvidia driver version        : No CUDA
cuDNN version                : No CUDA
HIP runtime version          : N/A
MIOpen runtime version       : N/A
Is XNNPACK available         : False

==============================
          CPU Info
==============================
Architecture:                            x86_64
CPU op-mode(s):                          32-bit, 64-bit
Address sizes:                           52 bits physical, 57 bits virtual
Byte Order:                              Little Endian
CPU(s):                                  4
On-line CPU(s) list:                     0-3
Vendor ID:                               GenuineIntel
Model name:                              Intel(R) Xeon(R) Processor @ 2.10GHz
CPU family:                              6
Model:                                   207
Thread(s) per core:                      1
Core(s) per socket:                      4
Socket(s):                               1
Stepping:                                2
BogoMIPS:                                4200.00
Flags:                                   fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid tsc_known_freq pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch cpuid_fault ssbd ibrs ibpb stibp ibrs_enhanced fsgsbase tsc_adjust bmi1 hle avx2 smep bmi2 erms invpcid rtm avx512f avx512dq rdseed adx smap avx512ifma clflushopt clwb avx512cd sha_ni avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves avx_vnni avx512_bf16 wbnoinvd arat avx512vbmi umip avx512_vbmi2 gfni vaes vpclmulqdq avx512_vnni avx512_bitalg avx512_vpopcntdq rdpid cldemote movdiri movdir64b fsrm md_clear serialize tsxldtrk amx_bf16 avx512_fp16 amx_tile amx_int8 arch_capabilities
Hypervisor vendor:                       KVM
Virtualization type:                     full
L1d cache:                               192 KiB (4 instances)
L1i cache:                               128 KiB (4 instances)
L2 cache:                                8 MiB (4 instances)
L3 cache:                                260 MiB (1 instance)
NUMA node(s):                            1
NUMA node0 CPU(s):                       0-3
Vulnerability Gather data sampling:      Not affected
Vulnerability Ghostwrite:                Not affected
Vulnerability Indirect target selection: Not affected
Vulnerability Itlb multihit:             Not affected
Vulnerability L1tf:                      Not affected
Vulnerability Mds:                       Not affected
Vulnerability Meltdown:                  Not affected
Vulnerability Mmio stale data:           Not affected
Vulnerability Old microcode:             Not affected
Vulnerability Reg file data sampling:    Not affected
Vulnerability Retbleed:                  Not affected
Vulnerability Spec rstack overflow:      Not affected
Vulnerability Spec store bypass:         Mitigation; Speculative Store Bypass disabled via prctl
Vulnerability Spectre v1:                Mitigation; usercopy/swapgs barriers and __user pointer sanitization
Vulnerability Spectre v2:                Mitigation; Enhanced / Automatic IBRS; IBPB conditional; PBRSB-eIBRS SW sequence; BHI Vulnerable
Vulnerability Srbds:                     Not affected
Vulnerability Tsa:                       Not affected
Vulnerability Tsx async abort:           Not affected
Vulnerability Vmscape:                   Not affected

==============================
Versions of relevant libraries
==============================
[pip3] numpy==2.3.5
[pip3] nvidia-cublas==13.1.1.3
[pip3] nvidia-cuda-cupti==13.0.85
[pip3] nvidia-cuda-nvrtc==13.0.88
[pip3] nvidia-cuda-runtime==13.0.96
[pip3] nvidia-cudnn-cu13==9.20.0.48
[pip3] nvidia-cufft==12.0.0.61
[pip3] nvidia-cufile==1.15.1.6
[pip3] nvidia-curand==10.4.0.35
[pip3] nvidia-cusolver==12.0.4.66
[pip3] nvidia-cusparse==12.6.3.3
[pip3] nvidia-cusparselt-cu13==0.8.1
[pip3] nvidia-nccl-cu13==2.29.7
[pip3] nvidia-nvjitlink==13.4.92
[pip3] nvidia-nvshmem-cu13==3.4.5
[pip3] nvidia-nvtx==13.0.85
[pip3] pyzmq==27.2.0
[pip3] torch==2.13.0
[pip3] transformers==5.17.0
[pip3] triton==3.7.1
[conda] Could not collect

==============================
         vLLM Info
==============================
ROCM Version                 : Could not collect
vLLM Version                 : 0.30.1rc1.dev45+ge78e367c6 (git sha: e78e367c6)
vLLM Build Flags:
  CUDA Archs: Not Set; ROCm: Disabled; XPU: Disabled
GPU Topology:
  Could not collect

==============================
     Environment Variables
==============================
PYTORCH_NVML_BASED_CUDA_CHECK=1
TORCHINDUCTOR_COMPILE_THREADS=1
TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor_root

```
</details>

Note: this environment is a CPU-only container (`VLLM_TARGET_DEVICE=empty`-style pure-Python install, torch 2.13.0+cu130 with no GPU). The bug is entirely in the Python request-conversion / renderer layer and was reproduced in-process without an engine; I have not run a live `vllm serve` for it.

### 🐛 Describe the bug

The Anthropic-compatible `POST /v1/messages` (and `/v1/messages/count_tokens`) endpoint converts an **empty** `tools` list into an OpenAI `ChatCompletionRequest` with `tools=[]` and `tool_choice="auto"`. The OpenAI endpoint itself rejects `tools: []` at validation time and defaults `tool_choice` to `"none"` when no tools are sent, but the Anthropic converter assigns `req.tools` / `req.tool_choice` after the model is constructed, so the `check_tool_usage` validator never sees it.

The chat renderer then treats the request as an `"auto"` tool-choice request. On a server started without `--enable-auto-tool-choice` / `--tool-call-parser` (the default), the request is rejected with HTTP 400:

```
"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

even though the client asked for no tools at all. Clients that always populate `tools` (an empty array when nothing is registered) cannot use such a server; the repo's own test fixture captured from Claude Code traffic (`tests/entrypoints/anthropic/test_anthropic_messages_conversion.py::TestInlineSystemMessageInMessagesArray`) sends `tools=[]`.

Root cause: `vllm/entrypoints/anthropic/serving.py`, `AnthropicServingMessages._convert_tools` only returns early on `tools is None`; for `tools == []` it sets `req.tool_choice = "auto"` and `req.tools = []`.

Minimal in-process reproduction (no model / GPU needed):

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from vllm.entrypoints.anthropic.protocol import AnthropicMessagesRequest
from vllm.entrypoints.anthropic.serving import AnthropicServingMessages
from vllm.renderers.online_renderer import OnlineRenderer

req = AnthropicMessagesRequest(
    model="m", max_tokens=8, messages=[{"role": "user", "content": "hi"}], tools=[]
)
chat_req = AnthropicServingMessages.to_chat_completion_request(req)
print(chat_req.tools, chat_req.tool_choice)   # [] auto   <- expected: None / none

model_config = MagicMock(); model_config.model = "m"; model_config.hf_config.model_type = "llama"
renderer = OnlineRenderer(model_config, MagicMock(), request_logger=None,
                          chat_template=None, chat_template_content_format="auto")
renderer.validate_chat_template = MagicMock(return_value=None)
renderer.preprocess_chat = AsyncMock(return_value=([], []))
print(asyncio.run(renderer.render_chat(chat_req)))
# ErrorResponse(error=ErrorInfo(message='"auto" tool choice requires
#   --enable-auto-tool-choice and --tool-call-parser to be set', type='BadRequestError', code=400))
```

Equivalent HTTP reproduction (untested here, derived from the code path): start `vllm serve <model>` with default flags and send

```bash
curl -s localhost:8000/v1/messages -H 'content-type: application/json' -d '{
  "model": "<model>", "max_tokens": 8,
  "messages": [{"role": "user", "content": "hi"}],
  "tools": []}'
```

Expected: a normal completion (same as omitting `tools`).
Actual: HTTP 400 `{"type":"error","error":{"type":"BadRequestError","message":"\"auto\" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set"}}`.

Version: reproduced on `main` @ e78e367c6 (`0.30.1rc1.dev45+ge78e367c6`). The code path is unchanged since the Anthropic tools conversion was introduced, so released versions are affected as well.

### Before submitting a new issue...

- [x] Make sure you already searched for relevant issues, and asked the chatbot living at the bottom right corner of the documentation page, which can answer lots of frequently asked questions.

---

## (b) PR

**Title:** `[Bugfix][Frontend] Treat empty tools list as no tools in Anthropic Messages API`

**Body:**

```markdown
## Purpose

FIX #<issue number once filed>

`AnthropicServingMessages._convert_tools` only skipped conversion when `tools` was `None`. A `/v1/messages` (or `/v1/messages/count_tokens`) request with `tools: []` was converted into a `ChatCompletionRequest` with `tools=[]` and `tool_choice="auto"` via attribute assignment, bypassing the OpenAI request validator that rejects an empty tools array and defaults `tool_choice` to `"none"` when no tools are given.

On a server started without `--enable-auto-tool-choice` / `--tool-call-parser` the chat renderer then rejected the request with HTTP 400:

```
"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

even though the client asked for no tools at all.

This PR treats an empty `tools` list like an omitted `tools` field, matching the OpenAI endpoint's behaviour for a request without tools. A non-empty `tools` list still defaults `tool_choice` to `"auto"` as before.

## Test Plan

Added `TestToolsConversion` to `tests/entrypoints/anthropic/test_anthropic_messages_conversion.py` (CPU-only, no engine):

- `test_tools_default_tool_choice_to_auto`: non-empty tools still convert and default to `tool_choice="auto"` (guards against over-fixing).
- `test_empty_tools_is_treated_as_no_tools`: `tools: []` converts identically to an omitted `tools` field.
- `test_empty_tools_not_rejected_by_renderer_without_tool_parser`: drives `OnlineRenderer.render_chat` with default server flags (no tool parser, auto tools off) and asserts no `ErrorResponse` is returned.

```bash
pytest -p no:cacheprovider tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
pre-commit run --files vllm/entrypoints/anthropic/serving.py tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
```

## Test Result

Before the fix (new tests only fail):

```
FAILED tests/entrypoints/anthropic/test_anthropic_messages_conversion.py::TestToolsConversion::test_empty_tools_is_treated_as_no_tools
FAILED tests/entrypoints/anthropic/test_anthropic_messages_conversion.py::TestToolsConversion::test_empty_tools_not_rejected_by_renderer_without_tool_parser
2 failed, 63 passed, 14 warnings in 12.53s
```

After the fix:

```
65 passed, 14 warnings in 13.03s
```

`pre-commit run --files ...`: ruff check, ruff format, typos, mypy (3.10), SPDX header, lazy-import, forbidden-import and test-tethering hooks all pass.

Tests were run on a CPU-only machine (pure-Python install, no GPU); the change is confined to the Python request-conversion layer.

## AI disclosure

This change was developed with AI assistance (Claude, via Claude Code). I reviewed every changed line, ran the tests and pre-commit locally, and the commit carries a `Co-authored-by: Claude <noreply@anthropic.com>` trailer per the contributing guide.
```

Checklist items considered: purpose with linked issue (yes), test plan/command (yes), test results before/after (yes), docs update (not needed, no user-facing option changed).

---

## (c) Exact commands run and results

Environment setup (no GPU; `download.pytorch.org` and `pypi.nvidia.com` are blocked by the container egress proxy, so CPU torch wheels were unavailable and PyPI's CUDA torch wheel was used; the `VLLM_TARGET_DEVICE=empty uv pip install -e .` route was abandoned because it triggers a 4.6 GB Rust frontend build that exhausted the disk, so the repo is used via `PYTHONPATH` instead):

```bash
cd <repo>
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python torch==2.13.0 -r requirements/common.txt pytest pytest-asyncio pre-commit tblib
PYTHONPATH=. .venv/bin/python -c "import vllm, torch; print(vllm.__version__, torch.__version__)"
#  0.30.1rc1.dev45+ge78e367c6 2.13.0+cu130
```

MRE (before / after):

```bash
PYTHONPATH=. .venv/bin/python /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/mre/mre_empty_tools.py
# before (main):
#   converted tools      = []
#   converted tool_choice= auto
#   openai no-tools tool_choice = none
#   renderer result: "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
#   AssertionError: BUG: empty tools list rejected
# after (fix/anthropic-empty-tools):
#   converted tools      = None
#   converted tool_choice= None
#   openai no-tools tool_choice = none
#   OK: empty tools list is treated like no tools      (exit 0)
```

Tests:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -p no:cacheprovider -q tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
# before fix: 2 failed, 63 passed  (only the two new empty-tools tests fail)
# after fix : 65 passed
PYTHONPATH=. .venv/bin/python -m pytest -p no:cacheprovider -q tests/entrypoints/anthropic/test_protocol_exports.py
# 2 passed
```

Lint:

```bash
.venv/bin/pre-commit install-hooks
PATH=$PWD/.venv/bin:$PATH .venv/bin/pre-commit run --files vllm/entrypoints/anthropic/serving.py tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
# ruff check Passed, ruff format Passed, typos Passed, check-test-tethering Passed,
# mypy 3.10 Passed, SPDX Passed, root lazy imports Passed, forbidden imports Passed, ... (all Passed/Skipped)
```

Git:

```bash
git config user.name HS1CMU && git config user.email the.heathsun@gmail.com
git checkout -b fix/anthropic-empty-tools
git add vllm/entrypoints/anthropic/serving.py tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
git commit -s -F - <<'MSG'
[Bugfix][Frontend] Treat empty `tools` list as no tools in Anthropic Messages API
...
Co-authored-by: Claude <noreply@anthropic.com>
MSG
# -> Signed-off-by: HS1CMU <the.heathsun@gmail.com> appended after the Co-authored-by trailer
```

Honesty notes:
- No live `vllm serve` run: no GPU and no model weights in this container. The HTTP-level repro in the issue is derived from the code path (`create_messages -> create_chat_completion -> render_chat_request -> render_chat`), which the in-process test exercises directly from the converted request.
- I could not confirm from Anthropic's public docs (egress-blocked) whether the upstream API accepts `tools: []`; the fix is justified on vLLM's own terms: an empty list is semantically "no tools", the OpenAI path never produces `tool_choice="auto"` without tools, and the error message it currently yields is misleading.
- `test_empty_tools_not_rejected_by_renderer_without_tool_parser` constructs `OnlineRenderer` with `MagicMock` model/renderer objects and stubs `validate_chat_template` / `preprocess_chat`; it only exercises the tool-choice validation that runs before templating. Reviewers may prefer to drop it and keep the two conversion-level tests.

---

## (d) `git diff main`

```diff
diff --git a/tests/entrypoints/anthropic/test_anthropic_messages_conversion.py b/tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
index 226908d..0b2bf6d 100644
--- a/tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
+++ b/tests/entrypoints/anthropic/test_anthropic_messages_conversion.py
@@ -12,11 +12,12 @@ blocks echoed back by Anthropic clients, and streaming conversion in
 Also covers cache usage computation in ``_build_anthropic_usage``.
 """
 
+import asyncio
 import json
 from argparse import Namespace
 from http import HTTPStatus
 from typing import Annotated
-from unittest.mock import MagicMock
+from unittest.mock import AsyncMock, MagicMock
 
 import pytest
 from fastapi import FastAPI
@@ -44,11 +45,16 @@ from vllm.entrypoints.openai.chat_completion.protocol import (
     ChatCompletionStreamResponse,
     ChatMessage,
 )
-from vllm.entrypoints.serve.engine.protocol import PromptTokenUsageInfo, UsageInfo
+from vllm.entrypoints.serve.engine.protocol import (
+    ErrorResponse,
+    PromptTokenUsageInfo,
+    UsageInfo,
+)
 from vllm.entrypoints.serve.exception_handling.handlers.validation import (
     validation_exception_handler,
 )
 from vllm.exceptions import VLLMValidationError
+from vllm.renderers.online_renderer import OnlineRenderer
 
 _convert = AnthropicServingMessages.to_chat_completion_request
 _img_url = AnthropicServingMessages._convert_image_source_to_url
@@ -231,6 +237,66 @@ class TestVllmXargs:
         }
 
 
+# ======================================================================
+# tools conversion
+# ======================================================================
+
+
+class TestToolsConversion:
+    _USER = [{"role": "user", "content": "Hello"}]
+    _TOOL = {
+        "name": "get_weather",
+        "description": "Get the weather",
+        "input_schema": {"type": "object", "properties": {}},
+    }
+
+    def test_tools_default_tool_choice_to_auto(self):
+        result = _convert(_make_request(self._USER, tools=[self._TOOL]))
+
+        assert result.tools is not None
+        assert [t.function.name for t in result.tools] == ["get_weather"]
+        assert result.tool_choice == "auto"
+
+    def test_empty_tools_is_treated_as_no_tools(self):
+        """``tools: []`` must convert like an omitted ``tools`` field.
+
+        Converting it to ``tools=[]`` + ``tool_choice="auto"`` makes the
+        renderer reject the request with an error about
+        ``--enable-auto-tool-choice`` on servers that run without a tool
+        parser, even though the client asked for no tools at all.
+        """
+        result = _convert(_make_request(self._USER, tools=[]))
+        baseline = _convert(_make_request(self._USER))
+
+        assert result.tools is None
+        assert result.tool_choice == baseline.tool_choice
+        assert result.tool_choice != "auto"
+
+    def test_empty_tools_not_rejected_by_renderer_without_tool_parser(self):
+        """End-to-end through the chat renderer with default server flags."""
+        model_config = MagicMock()
+        model_config.model = "test-model"
+        model_config.hf_config.model_type = "llama"
+        renderer = OnlineRenderer(
+            model_config,
+            MagicMock(),
+            request_logger=None,
+            chat_template=None,
+            chat_template_content_format="auto",
+        )
+        assert renderer.parser is None
+
+        chat_request = _convert(_make_request(self._USER, tools=[]))
+        # Stop before templating: any error here would come from the
+        # tool_choice validation that runs first.
+        renderer.validate_chat_template = MagicMock(return_value=None)
+        renderer.preprocess_chat = AsyncMock(return_value=([], []))
+
+        result = asyncio.run(renderer.render_chat(chat_request))
+
+        assert not isinstance(result, ErrorResponse), result
+
+
 # ======================================================================
 # tool_result content handling
 # ======================================================================
diff --git a/vllm/entrypoints/anthropic/serving.py b/vllm/entrypoints/anthropic/serving.py
index 6cc1271..bf41103 100644
--- a/vllm/entrypoints/anthropic/serving.py
+++ b/vllm/entrypoints/anthropic/serving.py
@@ -566,7 +566,12 @@ class AnthropicServingMessages(OpenAIServingChat):
         req: ChatCompletionRequest,
     ) -> None:
         """Convert Anthropic tools to OpenAI format."""
-        if anthropic_request.tools is None:
+        # Treat ``tools: []`` like an omitted ``tools`` field. Converting it
+        # to ``tools=[]`` with ``tool_choice="auto"`` bypasses the OpenAI
+        # request validation (which rejects an empty tools array) and makes
+        # the renderer reject the request with an error about
+        # ``--enable-auto-tool-choice`` when no tool parser is configured.
+        if not anthropic_request.tools:
             return
 
         tools = []
```
