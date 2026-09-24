# sglang submission: text before a tool call dropped in streaming (base detector / qwen25 / llama3 / hermes)

Repo: sgl-project/sglang, main @ f4d9d2e ("[RL] Add RL weight-update sessions ...")
Local branch: `fix/stream-prefix-text-before-tool-call` (1 commit, ce1d8a6) in
`/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/sglang`
Nothing has been posted to GitHub.

## (a) Issue

### Existing-issue check (done 2026-09-24)

Searched open/closed issues and PRs for this symptom. Related but NOT the same bug:

- #31915 "Tool-call parsers lose or corrupt data at streaming chunk boundaries" — covers the
  base detector's name-send branch losing arguments, `]` stripping, kimik2/step3/llama32 regex
  issues; it does not mention text before the first `<tool_call>` being dropped when the marker
  is in the same delta.
- #35564 / PR #35625 (open) — 8 parsers (cohere, gemma4, glm*, minimax-m2, mistral, step3);
  does not touch `base_format_detector.py` prefix handling, `qwen25_detector.py` or `hermes_detector.py`.
- #37634 (closed) — multiple complete calls in one increment losing arguments; different symptom.
- #34214 "Streaming response truncates content when both content and tool_calls are present
  (SGLang 0.5.17)" — same user-visible symptom but for the `deepseekv4` detector (own streaming
  implementation, not the base path) and it already has PR #36154; not this bug.

No existing PR fixes this (searched "streaming text before tool_call dropped base_format_detector
normal_text prefix" and related phrasings).

### New issue draft (per .github/ISSUE_TEMPLATE/1-bug-report.yml)

Title: `[Bug] Streaming tool-call parsing drops the text that precedes `<tool_call>` when it arrives in the same delta (qwen25/qwen, llama3, base detector); hermes loses the tool call instead`

Checklist
- [x] I searched related issues but found no solution. (#31915, #35564, #37634 are neighbours, not this; #34214 is the deepseekv4-specific variant with its own PR #36154.)
- [x] The bug persists in the latest version. (main @ f4d9d2e)
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion ...
- [x] Please use English.

Describe the bug

`BaseFormatDetector.parse_streaming_increment` gates on `has_tool_call(buffer)`. As soon as the
buffer contains `bot_token` it jumps to JSON parsing at the marker position and never emits
`buffer[:bot_pos]`. Any visible text sitting in front of the first tool call is therefore
silently discarded when the text and the marker share a streaming increment. That happens
whenever a delta carries more than one token (speculative decoding / EAGLE / MTP, per-request
`stream_interval`, detokenizer batching) and also in the single-token case: a partial
`bot_token` is *held back* together with the preceding text (line 160-165), and when the
marker completes the held-back text is dropped with it.

Detectors affected through the base path: `qwen25`/`qwen`, `llama3`, `trinity`, `ling3`
(anything that calls `super().parse_streaming_increment`). The one-shot parser
(`detect_and_parse`) keeps that text, so non-streaming and streaming responses disagree.

`hermes` has its own guard for this case, but it returns the prefix and leaves the tool
call in the buffer without parsing it. If that was the final delta, `finish()` flushes
nothing and `_check_for_unstreamed_tool_args` has no `prev_tool_call_arr`, so the tool call
is lost entirely (the client gets content only, no `tool_calls`).

Reproduction (pure Python, no server, no GPU)

```python
from sglang.srt.entrypoints.openai.protocol import Function, Tool
from sglang.srt.function_call.function_call_parser import FunctionCallParser

tools = [Tool(type="function", function=Function(name="get_weather",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}}))]

def stream(parser_name, chunks):
    p = FunctionCallParser(tools, parser_name)
    text, calls = "", []
    for c in chunks:
        t, cs = p.parse_stream_chunk(c); text += t or ""; calls += cs
    t, cs = p.parse_stream_end(); text += t or ""; calls += cs
    return text, [(c.tool_index, c.name, c.parameters) for c in calls]

full = 'Sure, let me check.\n<tool_call>\n{"name": "get_weather", "arguments": {"city": "Paris"}}\n</tool_call>'
print(FunctionCallParser(tools, "qwen25").parse_non_stream(full)[0])   # 'Sure, let me check.'

print(stream("qwen25", ['Sure, let me check.\n<tool_call>\n',
                        '{"name": "get_weather", "arguments": {"city": "Paris"}}', '\n</tool_call>']))
print(stream("qwen25", ['Sure, let me check.\n<tool_', 'call>\n{"name": "get_weather", "arguments": {"city": "Paris"}}\n</tool_call>']))
print(stream("llama3", ['Sure, let me check. <|python_tag|>{"name": "get_weather", "parameters": ', '{"city": "Paris"}}']))
print(stream("hermes", ['Sure, let me check.\n<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>']))
```

Output on main @ f4d9d2e:

```
Sure, let me check.
('', [(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')])      # qwen25: content lost
('', [(0, 'get_weather', '')])                                       # qwen25: content lost (partial marker held back)
('', [(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')])      # llama3: content lost
('Sure, let me check.\n', [])                                        # hermes: tool call lost
```

Expected: content `'Sure, let me check.\n'` (resp. `'Sure, let me check. '`) is streamed and the tool call is
still emitted, matching `parse_non_stream`.

Environment

CPU-only container, no GPU, so `python3 -m sglang.check_env` cannot run the full probe. The
reproduction only touches `sglang.srt.function_call` (pure Python):
- sglang main @ f4d9d2e (0.0.0.dev50+gf4d9d2e67, run from source with PYTHONPATH=python)
- Python 3.11.15, Linux x86_64
- torch 2.14.0 (import only), transformers 5.17.0, pydantic 2.13.5, partial-json-parser, orjson, xgrammar (PyPI)

## (b) Pull request

Title: `[function_call] Keep text preceding a tool call when it streams in the same delta`

Body (per .github/pull_request_template.md):

```
## Motivation

Fixes #<N>   <!-- number of the issue above, once filed -->

`BaseFormatDetector.parse_streaming_increment` discards any normal text that sits in front of
the first `bot_token` once the marker is in the buffer: the increment jumps straight to JSON
parsing at the marker and the prefix is never emitted. This happens whenever the text and the
marker arrive in one delta (multi-token deltas from speculative decoding or `stream_interval`)
and whenever the marker was held back as a partial token, so `qwen25`/`qwen`, `llama3`,
`trinity`, `ling3` (every detector that uses the base streaming path) silently drop visible
content such as `"Sure, let me check.\n"` while `detect_and_parse` keeps it.

`HermesDetector` had its own guard for this that returned the prefix and left the tool call in
the buffer; if that was the final delta the tool call was never parsed at all (`finish()` has
nothing to flush and `prev_tool_call_arr` is empty).

## Modifications

- `base_format_detector.py`: before parsing, if no tool has started yet (`current_tool_id == -1`)
  and `bot_token` sits at `bot_pos > 0`, emit `current_text[:bot_pos]` as normal text, trim the
  buffer to the marker and continue parsing the tool call in the same increment (re-entering the
  base implementation once with an empty increment). Only the text before the *first* tool call
  is emitted, which matches `detect_and_parse`; markup between calls is still dropped.
- `hermes_detector.py`: remove the early return that duplicated this in a lossy way; the base
  path now handles it, and `_clean_normal_text` still strips `</tool_call>` from the result.
  This also stops a stray `</tool_call>` from leaking into content when the next `<tool_call>`
  arrives in the same chunk as the previous end tag.
- Tests: `TestBaseFormatDetector` (same-increment and held-back-partial-marker cases),
  `TestQwen25Detector.test_streaming_normal_text_prefix_in_same_chunk`,
  `TestHermesDetector.test_streaming_text_and_tool_call_in_one_chunk`. All four fail on main
  and pass with the fix.

## Accuracy Tests

N/A (parser-only change, no model forward code).

## Speed Tests and Profiling

N/A. The extra `find` runs only until the first tool call has started.

## Checklist

- [x] Format your code according to the Format code with pre-commit (`pre-commit run --files ...` clean apart from `no-commit-to-branch`, which only complained because I ran it on `main` before branching).
- [x] Add unit tests according to the Run and add unit tests.
- [ ] Update documentation (no doc change needed).
- [ ] Provide accuracy and speed benchmark results (N/A).
- [x] Follow the SGLang code style guidance.

Disclosure: this fix and its tests were developed with AI assistance (Claude Code); I reviewed
the change, reproduced the bug and ran the tests myself.
```

## (c) Commands and results

Setup (CPU-only, from source; `download.pytorch.org` and `huggingface.co` are blocked in this container):

```
uv venv sglang-venv --python 3.11
uv pip install pydantic fastapi transformers numpy pytest orjson partial-json-parser openai msgspec aiohttp psutil \
    requests pillow xgrammar pre-commit pyzmq setproctitle pybase64 IPython jsonschema sentencepiece loguru gguf \
    compressed_tensors datasets torch
uv pip install --no-deps torchvision
export PYTHONPATH=$PWD/python
```

MRE (`sglang-mre-stream-prefix.py`, same as the issue script), before / after:

```
# main @ f4d9d2e
one-shot : 'Sure, let me check.'
qwen25 / prefix + marker in one delta      content=''                       calls=[(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')]
qwen25 / whole answer in one delta         content=''                       calls=[(0, 'get_weather', '')]
qwen25 / partial marker held back          content=''                       calls=[(0, 'get_weather', '')]
llama3 / prefix + marker in one delta      content=''                       calls=[(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')]
hermes / whole answer in one delta         content='Sure, let me check.\n'  calls=[]

# fix/stream-prefix-text-before-tool-call
one-shot : 'Sure, let me check.'
qwen25 / prefix + marker in one delta      content='Sure, let me check.\n'  calls=[(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')]
qwen25 / whole answer in one delta         content='Sure, let me check.\n'  calls=[(0, 'get_weather', '')]
qwen25 / partial marker held back          content='Sure, let me check.\n'  calls=[(0, 'get_weather', '')]
llama3 / prefix + marker in one delta      content='Sure, let me check. '   calls=[(0, 'get_weather', ''), (0, None, '{"city": "Paris"}')]
hermes / whole answer in one delta         content='Sure, let me check.\n'  calls=[(0, 'get_weather', '')]
```
(The "whole answer in one delta" rows show only the name because the MRE does not emulate the
serving layer's `_check_for_unstreamed_tool_args` flush; the arguments are flushed there. The
name-only-in-final-chunk behaviour of the base class is the separate, already reported #31915.)

New tests, fix applied:
```
python -m pytest test/registered/unit/function_call/test_function_call_parser.py test/registered/unit/function_call/test_hermes_detector.py \
  -k "test_normal_text_before_bot_token_in_same_increment or test_normal_text_before_held_back_partial_bot_token or test_streaming_normal_text_prefix_in_same_chunk or test_streaming_text_and_tool_call_in_one_chunk"
4 passed, 262 deselected
```
New tests, source reverted (`git stash push -- python/`):
```
FAILED ...::TestBaseFormatDetector::test_normal_text_before_bot_token_in_same_increment
FAILED ...::TestBaseFormatDetector::test_normal_text_before_held_back_partial_bot_token
FAILED ...::TestQwen25Detector::test_streaming_normal_text_prefix_in_same_chunk
FAILED ...::TestHermesDetector::test_streaming_text_and_tool_call_in_one_chunk
4 failed, 262 deselected
```
Whole directory `pytest test/registered/unit/function_call/`:
```
main:        15 failed, 606 passed, 1605 subtests passed
fix branch:  15 failed, 610 passed, 1605 subtests passed
```
The 15 failures are identical on both (TestDeepSeekV32Detector / TestDeepSeekV4Detector: they
download `deepseek-ai/DeepSeek-V3.2` tokenizers and huggingface.co is blocked here).
`test/registered/unit/entrypoints/openai/test_serving_chat.py` + `test/registered/unit/parser/test_reasoning_parser.py`:
5 failed / 275 passed, identical failure set on main and on the branch (all HF-download based).

pre-commit:
```
pre-commit run --files python/sglang/srt/function_call/base_format_detector.py python/sglang/srt/function_call/hermes_detector.py \
  test/registered/unit/function_call/test_function_call_parser.py test/registered/unit/function_call/test_hermes_detector.py
isort / ruff / ruff format / codespell / registered-test registry checks: Passed
no-commit-to-branch: Failed only because it was run while on `main` (before branching)
```

Differential fuzz (one-shot vs. streaming over random chunkings, special tokens kept atomic,
serving-layer flush emulated; `work/fuzz2.py`): after the fix `qwen25`, `hermes`, `llama3`
agree with `detect_and_parse` on the prefix text for every chunking; the only remaining
difference is trailing text after the last tool call, which one-shot drops and streaming emits
(pre-existing, out of scope).

## (d) git diff main

```diff
diff --git a/python/sglang/srt/function_call/base_format_detector.py b/python/sglang/srt/function_call/base_format_detector.py
index 53c3067..61ab986 100644
--- a/python/sglang/srt/function_call/base_format_detector.py
+++ b/python/sglang/srt/function_call/base_format_detector.py
@@ -164,6 +164,20 @@ class BaseFormatDetector(ABC):
                 # Might be partial bot_token, keep buffering
                 return StreamingParseResult()
 
+        # Text preceding the first bot_token is normal content. It ends up in the
+        # buffer together with the marker when both arrive in the same increment
+        # (multi-token deltas, e.g. speculative decoding) or when a partial
+        # marker was held back above. Emit it instead of discarding it, then
+        # keep parsing the tool call that follows in this same increment.
+        if self.current_tool_id == -1:
+            bot_pos = current_text.find(self.bot_token) if self.bot_token else -1
+            if bot_pos > 0:
+                prefix_text = current_text[:bot_pos]
+                self._buffer = current_text[bot_pos:]
+                res = BaseFormatDetector.parse_streaming_increment(self, "", tools)
+                res.normal_text = prefix_text + res.normal_text
+                return res
+
         # Build tool indices if not already built
         if not hasattr(self, "_tool_indices"):
             self._tool_indices = self._get_tool_indices(tools)
diff --git a/python/sglang/srt/function_call/hermes_detector.py b/python/sglang/srt/function_call/hermes_detector.py
index ff55461..4048cf5 100644
--- a/python/sglang/srt/function_call/hermes_detector.py
+++ b/python/sglang/srt/function_call/hermes_detector.py
@@ -101,12 +101,8 @@ class HermesDetector(BaseFormatDetector):
                 self._buffer = ""
             return StreamingParseResult(normal_text=self._clean_normal_text(safe_text))
 
-        bot_pos = current_text.find(self.bot_token)
-        if bot_pos > 0:
-            normal_text = current_text[:bot_pos]
-            self._buffer = current_text[bot_pos:]
-            return StreamingParseResult(normal_text=normal_text)
-
+        # The base class emits any text preceding the first bot_token and keeps
+        # parsing the tool call that follows it within the same increment.
         result = super().parse_streaming_increment(new_text="", tools=tools)
         if result.normal_text:
             result.normal_text = self._clean_normal_text(result.normal_text)
diff --git a/test/registered/unit/function_call/test_function_call_parser.py b/test/registered/unit/function_call/test_function_call_parser.py
index 9397125..f777732 100644
--- a/test/registered/unit/function_call/test_function_call_parser.py
+++ b/test/registered/unit/function_call/test_function_call_parser.py
@@ -1211,6 +1211,43 @@ class TestBaseFormatDetector(unittest.TestCase):
             params["city"], "杭州", "Should correctly parse Chinese city name"
         )
 
+    def _stream(self, chunks):
+        normal_text, calls = "", []
+        for chunk in chunks:
+            result = self.detector.parse_streaming_increment(chunk, self.tools)
+            normal_text += result.normal_text
+            calls.extend(result.calls)
+        return normal_text, calls
+
+    def test_normal_text_before_bot_token_in_same_increment(self):
+        """Text preceding the first bot_token must be emitted, not dropped, when
+        it arrives in the same increment as the marker (e.g. multi-token deltas),
+        and the tool call in that increment must still be parsed."""
+        chunks = [
+            'Sure, let me check. <tool_call>{"name": "get_weather", '
+            '"arguments": {"city": "Paris"}}',
+            "</tool_call>",
+        ]
+        normal_text, calls = self._stream(chunks)
+        self.assertEqual(normal_text, "Sure, let me check. ")
+        self.assertEqual([c.name for c in calls if c.name], ["get_weather"])
+        params = "".join(c.parameters for c in calls if c.parameters)
+        self.assertEqual(json.loads(params), {"city": "Paris"})
+
+    def test_normal_text_before_held_back_partial_bot_token(self):
+        """A partial bot_token holds back the preceding text; once the marker
+        completes, that text must be released as normal text."""
+        chunks = [
+            "Sure, let me check. <tool_",
+            'call>{"name": "get_weather", "arguments": {"city": "Paris"}}',
+            "</tool_call>",
+        ]
+        normal_text, calls = self._stream(chunks)
+        self.assertEqual(normal_text, "Sure, let me check. ")
+        self.assertEqual([c.name for c in calls if c.name], ["get_weather"])
+        params = "".join(c.parameters for c in calls if c.parameters)
+        self.assertEqual(json.loads(params), {"city": "Paris"})
+
 
 class TestLlama32Detector(unittest.TestCase):
     def setUp(self):
@@ -5477,6 +5514,25 @@ class TestQwen25Detector(unittest.TestCase):
         cities = [json.loads(result[i]["parameters"])["city"] for i in sorted(result)]
         self.assertEqual(cities, ["NYC", "Baltimore", "LA"])
 
+    def test_streaming_normal_text_prefix_in_same_chunk(self):
+        """Regression: text before <tool_call> that arrives in the same chunk as
+        the marker was silently dropped; the one-shot parser keeps it."""
+        chunks = [
+            "Sure, let me check the weather.\n<tool_call>\n",
+            '{"name": "get_current_weather", "arguments": {"city": "NYC", "state": "NY", "unit": "celsius"}}',
+            "\n</tool_call>",
+        ]
+        normal_text = ""
+        calls = []
+        for chunk in chunks:
+            result = self.detector.parse_streaming_increment(chunk, self.tools)
+            normal_text += result.normal_text
+            calls.extend(result.calls)
+        self.assertEqual(normal_text, "Sure, let me check the weather.\n")
+        self.assertEqual([c.name for c in calls if c.name], ["get_current_weather"])
+        params = "".join(c.parameters for c in calls if c.parameters)
+        self.assertEqual(json.loads(params)["city"], "NYC")
+
     def test_streaming_multiple_tool_calls_fused_chunks(self):
         """Test when separator and next bot_token arrive in a single chunk."""
         chunks = [
diff --git a/test/registered/unit/function_call/test_hermes_detector.py b/test/registered/unit/function_call/test_hermes_detector.py
index b6afb16..58cf085 100644
--- a/test/registered/unit/function_call/test_hermes_detector.py
+++ b/test/registered/unit/function_call/test_hermes_detector.py
@@ -172,6 +172,26 @@ class TestHermesDetector(CustomTestCase):
         params = json.loads(full_params)
         self.assertEqual(params["city"], "Tokyo")
 
+    def test_streaming_text_and_tool_call_in_one_chunk(self):
+        """Regression: when leading text and a complete tool call arrive in the
+        same (possibly final) chunk, the text was emitted but the tool call was
+        left in the buffer and never parsed."""
+        detector = HermesDetector()
+        result = detector.parse_streaming_increment(
+            'Sure, let me check. <tool_call>{"name": "get_weather", '
+            '"arguments": {"city": "Tokyo"}}',
+            self.tools,
+        )
+        self.assertEqual(result.normal_text, "Sure, let me check. ")
+        func_calls = [c for c in result.calls if c.name]
+        self.assertEqual(len(func_calls), 1)
+        self.assertEqual(func_calls[0].name, "get_weather")
+
+        result = detector.parse_streaming_increment("</tool_call>", self.tools)
+        self.assertEqual(result.normal_text, "")
+        full_params = "".join(c.parameters for c in result.calls if c.parameters)
+        self.assertEqual(json.loads(full_params), {"city": "Tokyo"})
+
 
 if __name__ == "__main__":
     import unittest
```
