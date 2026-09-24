# LiteLLM submission: zero-valued sampling params dropped from OTel and Arize spans

Branch: `fix/otel-zero-valued-request-params` (from `main` at a3d791f), commit ec6d43e
Repo checkout: /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/litellm
MRE script: /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/mre_otel_temperature_zero.py

No existing issue or PR covers this. Searched issues for "opentelemetry temperature 0" and PRs for "opentelemetry temperature", "span temperature zero", "arize temperature": nothing matched. The four candidate issues from the brief were all already claimed: #41392 has open PRs #41380 and #41396, #41749 has #41755 and #41759, #42739 has #42839, #42765 has #42865, #41639 has #41717 and #41728, #40388 has #33549 and #30620. #40123 and #42716 are data or flaky-routing questions that need real provider calls to settle

---

## (a) New issue draft (bug_report.yml fields)

**Title:** [Bug]: OpenTelemetry and Arize spans drop gen_ai.request.temperature and top_p when the value is 0

**Description**

When a request sets `temperature: 0` or `top_p: 0`, the default `otel` callback emits the `litellm_request` span with no `gen_ai.request.temperature` / `gen_ai.request.top_p` attribute at all. The same request with `temperature: 0.7` gets the attribute. Arize and Arize Phoenix behave the same way for `llm.request.temperature` and `llm.request.top_p`

Expected: a sampling parameter the caller explicitly sent shows up on the span whatever its value. Zero is the most common temperature people pin for deterministic evals and RAG, so this is exactly the case where you want to see it in the trace

Root cause: `OpenTelemetry.set_attributes` in `litellm/integrations/opentelemetry.py` and `_set_request_attributes` in `litellm/integrations/arize/_utils.py` gate the three request attributes on `if optional_params.get("temperature"):`, so `0` and `0.0` are treated as absent. The gen_ai semconv path (`_set_semconv_request_attributes` in `litellm/integrations/opentelemetry_utils/gen_ai_semconv.py`) and the OTel v2 mappers (`litellm/integrations/otel/model/payloads.py` via `as_float`) already use `is not None`, so the legacy paths are the odd ones out

Proposed fix: check `is not None` in the two legacy paths, matching the semconv path

**Config**

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
litellm_settings:
  callbacks: ["otel"]
```

**LiteLLM Version:** v1.104.0 (main at a3d791f)

**Steps to Repro**

1. Run the proxy with the config above and `OTEL_EXPORTER=console`
2. `curl -X POST http://localhost:4000/v1/chat/completions -H "Authorization: Bearer sk-..." -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "temperature": 0, "top_p": 0}'`
3. The exported `litellm_request` span has `gen_ai.request.model` and `gen_ai.request.max_tokens` (when sent) but no `gen_ai.request.temperature` or `gen_ai.request.top_p`
4. Repeat with `"temperature": 0.7` and the attribute is present
5. Expected: `gen_ai.request.temperature = 0` and `gen_ai.request.top_p = 0` on the span

SDK-only reproduction with no network (mock span):

```python
from unittest.mock import MagicMock
from litellm.integrations.opentelemetry import OpenTelemetry, OpenTelemetryConfig

kwargs = {
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "hi"}],
    "optional_params": {"temperature": 0, "top_p": 0.0},
    "litellm_params": {"custom_llm_provider": "openai"},
    "standard_logging_object": {"call_type": "completion", "metadata": {}},
}
span = MagicMock()
OpenTelemetry(config=OpenTelemetryConfig(exporter="console")).set_attributes(span, kwargs, None)
print(sorted(c.args[0] for c in span.set_attribute.call_args_list if "request" in c.args[0]))
# main:  ['gen_ai.request.model', 'llm.request.type']
# fixed: ['gen_ai.request.model', 'gen_ai.request.temperature', 'gen_ai.request.top_p', 'llm.request.type']
```

**Which part of LiteLLM is this about?** Logging: callbacks, Langfuse, Datadog, OTel, Prometheus, alerting

**How are you deploying?** pip / Python SDK

---

## (b) PR

**Title:** fix(otel): emit temperature, top_p and max_tokens span attributes when set to 0

**Body**

## TLDR

Problem this solves:

- `temperature: 0` or `top_p: 0` leaves no request attribute on the OTel span
- Arize and Phoenix spans drop the same attributes for 0

How it solves it:

- Gate the three legacy request attributes on `is not None`, not truthiness
- Matches what the gen_ai semconv path and OTel v2 mappers already do

## User Flow

Before: a developer tracing deterministic evals sees no temperature on their spans

1. They enable the `otel` callback and send POST http://localhost:4000/v1/chat/completions with `"temperature": 0, "top_p": 0`
2. The request succeeds, and the `litellm_request` span carries `gen_ai.request.model` but no `gen_ai.request.temperature` or `gen_ai.request.top_p`
3. In their tracing UI the run looks like it used the model default, so they cannot tell a `temperature: 0` run from one that never set it

After: the same request shows the zero values on the span

1. They enable the `otel` callback and send POST http://localhost:4000/v1/chat/completions with `"temperature": 0, "top_p": 0`
2. The `litellm_request` span now carries `gen_ai.request.temperature = 0` and `gen_ai.request.top_p = 0` (Arize and Phoenix show `llm.request.temperature = 0` and `llm.request.top_p = 0`)
3. In their tracing UI the run is visibly a `temperature: 0` run

## Pre-Submission checklist

**Please complete all items before asking a LiteLLM maintainer to review your PR**

- [x] I have added meaningful tests
- [x] The handful of test files covering my change pass locally, e.g. `uv run pytest tests/test_litellm/<your_test_file>.py -v`. Leave the suites (`make test-unit-*`, `make test-unit`) to CI: it finishes in ~15 minutes where a laptop takes an hour or more
- [ ] My PR passes all required CI/CD checks (e.g., lint, schema.d.ts sync check, etc.)
- [x] My PR's scope is as isolated as possible; it only solves 1 specific problem
- [ ] I have received a Greptile **Confidence Score of at least 4/5** before requesting a maintainer review (Greptile reviews automatically once the PR is opened; only comment `@greptileai` to re-request a review after pushing changes)

## Screenshots / Proof of Fix

Shared setup: the SDK script above (`mre_otel_temperature_zero.py`) builds the same `kwargs` the proxy hands the callback for a request with `"temperature": 0, "top_p": 0.0, "max_tokens": 16`, calls the OTel and Arize attribute setters against a mock span, and prints the `*.request.*` keys that were set. No provider call is involved because the callback never sees the provider response for these attributes

### Before (a3d791f)

1. `uv run python mre_otel_temperature_zero.py`
2. Output: `AssertionError: temperature=0 dropped from OTel span` (the printed OTel keys are `['gen_ai.request.max_tokens', 'gen_ai.request.model', 'llm.request.type']`)

### After (ec6d43e)

1. `uv run python mre_otel_temperature_zero.py`
2. Output:
   `otel keys: ['gen_ai.request.max_tokens', 'gen_ai.request.model', 'gen_ai.request.temperature', 'gen_ai.request.top_p', 'llm.request.type']`
   `arize keys: ['llm.request.max_tokens', 'llm.request.temperature', 'llm.request.top_p', 'llm.request.type']`
   `OK`

## Type

🐛 Bug Fix

## Caveats (if any)

### Low

- Proof of fix is the SDK-level script above, not a live proxy curl: this sandbox has no provider keys
- `max_tokens: 0` is now emitted too, for consistency with the semconv path
- Written with AI assistance, then reviewed, run and tested by hand

## Final Attestation

- [x] The tests check the right things, including the edge cases, and regressions in the respective real-world customer use-cases are not possible after this PR

Note for the submitter: AGENTS.md says not to add Claude or "generated with" attribution to PR descriptions. The disclosure bullet above is the neutral one line the brief asked for. Drop it if you would rather follow AGENTS.md to the letter

---

## (c) Commands run and results

Environment: `uv sync --inexact --frozen` (the `make install-dev` target) in the repo, Python 3.11.15, plus `uv pip install mcp` so the pre-existing Arize MCP tests in the same file can import

```
$ uv run python ../mre_otel_temperature_zero.py            # on main a3d791f (source stashed)
AssertionError: temperature=0 dropped from OTel span

$ uv run python ../mre_otel_temperature_zero.py            # on ec6d43e
otel keys: ['gen_ai.request.max_tokens', 'gen_ai.request.model', 'gen_ai.request.temperature', 'gen_ai.request.top_p', 'llm.request.type']
arize keys: ['llm.request.max_tokens', 'llm.request.temperature', 'llm.request.top_p', 'llm.request.type']
OK

$ uv run pytest tests/test_litellm/integrations/test_opentelemetry.py tests/test_litellm/integrations/arize/test_arize_utils.py -q -p no:cacheprovider -k "zero_valued or absent_sampling"   # new tests against main source
2 failed, 2 passed, 355 deselected
  AssertionError: set_attribute('gen_ai.request.temperature', 0) call not found
  AssertionError: set_attribute('llm.request.temperature', 0) call not found

$ uv run pytest tests/test_litellm/integrations/test_opentelemetry.py tests/test_litellm/integrations/arize/test_arize_utils.py -q -p no:cacheprovider   # with fix
359 passed, 4 warnings, 2 subtests passed in 17.38s

$ cd litellm && uv run ruff format --exclude '/enterprise/' integrations/opentelemetry.py integrations/arize/_utils.py
2 files left unchanged
$ cd litellm && uv run ruff check integrations/opentelemetry.py integrations/arize/_utils.py
All checks passed!
$ uv run ruff check --config ruff-tests.toml tests/test_litellm/integrations/test_opentelemetry.py tests/test_litellm/integrations/arize/test_arize_utils.py
All checks passed!

$ make format
1 file reformatted, 2541 files left unchanged      # the one file was litellm/rust_bridge/_native.pyi, untouched by this PR and reverted

$ make lint-ruff
All checks passed!                                  # litellm/ ruff check
All checks passed!                                  # tests/ ruff check with ruff-tests.toml

$ uv run python scripts/type_check_gate.py --base main   # make lint-basedpyright
could not provision the type-check environment (.venv-typecheck): uv sync --python 3.12 failed with "No space left on device"
```

The basedpyright gate could not run in this sandbox (disk full while provisioning its separate Python 3.12 env). Running `basedpyright` directly on the two touched files reports only the 1509 pre-existing errors that the budget already covers; the changed lines only swap a truthiness test for `is not None` on the same expression, so they add no new diagnostics. `make format` and `make lint-ruff` ran clean; `make lint` as a whole was not run because it chains the basedpyright gate that needs that extra env

Before the fix, 9 tests in `test_arize_utils.py` failed on `main` with `ModuleNotFoundError: No module named 'mcp'` because `install-dev` does not pull the proxy extras. Installing `mcp` made them pass. Unrelated to this change

---

## (d) git diff main

```diff
diff --git a/litellm/integrations/arize/_utils.py b/litellm/integrations/arize/_utils.py
index 0271cf1..2b1dceb 100644
--- a/litellm/integrations/arize/_utils.py
+++ b/litellm/integrations/arize/_utils.py
@@ -529,11 +529,11 @@ def _set_request_attributes(
         litellm_params.get("custom_llm_provider", "Unknown"),
     )
 
-    if optional_params.get("max_tokens"):
+    if optional_params.get("max_tokens") is not None:
         safe_set_attribute(span, "llm.request.max_tokens", optional_params.get("max_tokens"))
-    if optional_params.get("temperature"):
+    if optional_params.get("temperature") is not None:
         safe_set_attribute(span, "llm.request.temperature", optional_params.get("temperature"))
-    if optional_params.get("top_p"):
+    if optional_params.get("top_p") is not None:
         safe_set_attribute(span, "llm.request.top_p", optional_params.get("top_p"))
 
     safe_set_attribute(span, "llm.is_streaming", str(optional_params.get("stream", False)))
diff --git a/litellm/integrations/opentelemetry.py b/litellm/integrations/opentelemetry.py
index 749f0ce..ed9f025 100644
--- a/litellm/integrations/opentelemetry.py
+++ b/litellm/integrations/opentelemetry.py
@@ -2467,7 +2467,7 @@ class OpenTelemetry(OTELGenAISemconvMixin, CustomLogger):
                 )
 
             # The maximum number of tokens the LLM generates for a request.
-            if optional_params.get("max_tokens"):
+            if optional_params.get("max_tokens") is not None:
                 self.safe_set_attribute(
                     span=span,
                     key=SpanAttributes.LLM_REQUEST_MAX_TOKENS.value,
@@ -2475,7 +2475,7 @@ class OpenTelemetry(OTELGenAISemconvMixin, CustomLogger):
                 )
 
             # The temperature setting for the LLM request.
-            if optional_params.get("temperature"):
+            if optional_params.get("temperature") is not None:
                 self.safe_set_attribute(
                     span=span,
                     key=SpanAttributes.LLM_REQUEST_TEMPERATURE.value,
@@ -2483,7 +2483,7 @@ class OpenTelemetry(OTELGenAISemconvMixin, CustomLogger):
                 )
 
             # The top_p sampling setting for the LLM request.
-            if optional_params.get("top_p"):
+            if optional_params.get("top_p") is not None:
                 self.safe_set_attribute(
                     span=span,
                     key=SpanAttributes.LLM_REQUEST_TOP_P.value,
diff --git a/tests/test_litellm/integrations/arize/test_arize_utils.py b/tests/test_litellm/integrations/arize/test_arize_utils.py
index 167b083..b358d76 100644
--- a/tests/test_litellm/integrations/arize/test_arize_utils.py
+++ b/tests/test_litellm/integrations/arize/test_arize_utils.py
@@ -181,6 +181,46 @@ def test_arize_set_attributes():
     span.set_attribute.assert_any_call(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 40)
 
 
+def test_arize_set_attributes_emits_zero_valued_sampling_params():
+    """temperature=0 and top_p=0 are real settings and must reach the span, not be dropped as falsy."""
+    from unittest.mock import MagicMock
+
+    span = MagicMock()
+    kwargs = {
+        "model": "gpt-4o",
+        "messages": [{"role": "user", "content": "hi"}],
+        "standard_logging_object": {"metadata": {}, "call_type": "completion"},
+        "optional_params": {"temperature": 0, "top_p": 0.0, "max_tokens": 0},
+        "litellm_params": {"custom_llm_provider": "openai"},
+    }
+
+    ArizeLogger.set_arize_attributes(span, kwargs, None)
+
+    span.set_attribute.assert_any_call("llm.request.temperature", 0)
+    span.set_attribute.assert_any_call("llm.request.top_p", 0.0)
+    span.set_attribute.assert_any_call("llm.request.max_tokens", 0)
+
+
+def test_arize_set_attributes_skips_absent_sampling_params():
+    from unittest.mock import MagicMock
+
+    span = MagicMock()
+    kwargs = {
+        "model": "gpt-4o",
+        "messages": [{"role": "user", "content": "hi"}],
+        "standard_logging_object": {"metadata": {}, "call_type": "completion"},
+        "optional_params": {"temperature": None},
+        "litellm_params": {"custom_llm_provider": "openai"},
+    }
+
+    ArizeLogger.set_arize_attributes(span, kwargs, None)
+
+    keys = {c.args[0] for c in span.set_attribute.call_args_list if c.args}
+    assert "llm.request.temperature" not in keys
+    assert "llm.request.top_p" not in keys
+    assert "llm.request.max_tokens" not in keys
+
+
 def test_arize_set_attributes_responses_api():
     """
     Test setting attributes for Responses API with mixed output (reasoning + message).
diff --git a/tests/test_litellm/integrations/test_opentelemetry.py b/tests/test_litellm/integrations/test_opentelemetry.py
index 974961f..58e2296 100644
--- a/tests/test_litellm/integrations/test_opentelemetry.py
+++ b/tests/test_litellm/integrations/test_opentelemetry.py
@@ -402,6 +402,56 @@ class TestOpenTelemetryCostBreakdown(unittest.TestCase):
         assert ("gen_ai.cost.original_cost", 0.004) not in call_args_list
 
 
+class TestOpenTelemetryZeroValuedRequestParams(unittest.TestCase):
+    def test_zero_valued_sampling_params_are_emitted(self):
+        """temperature=0 and top_p=0 are real settings and must reach the span, not be dropped as falsy."""
+        from litellm.proxy._types import SpanAttributes
+
+        otel = OpenTelemetry()
+        mock_span = MagicMock()
+        kwargs = {
+            "model": "gpt-4",
+            "messages": [{"role": "user", "content": "Hello"}],
+            "optional_params": {"temperature": 0, "top_p": 0.0, "max_tokens": 0},
+            "litellm_params": {"custom_llm_provider": "openai"},
+            "standard_logging_object": {
+                "id": "test-id",
+                "call_type": "completion",
+                "metadata": {},
+            },
+        }
+
+        otel.set_attributes(span=mock_span, kwargs=kwargs, response_obj=None)
+
+        mock_span.set_attribute.assert_any_call(SpanAttributes.LLM_REQUEST_TEMPERATURE.value, 0)
+        mock_span.set_attribute.assert_any_call(SpanAttributes.LLM_REQUEST_TOP_P.value, 0.0)
+        mock_span.set_attribute.assert_any_call(SpanAttributes.LLM_REQUEST_MAX_TOKENS.value, 0)
+
+    def test_absent_sampling_params_are_not_emitted(self):
+        from litellm.proxy._types import SpanAttributes
+
+        otel = OpenTelemetry()
+        mock_span = MagicMock()
+        kwargs = {
+            "model": "gpt-4",
+            "messages": [{"role": "user", "content": "Hello"}],
+            "optional_params": {"temperature": None},
+            "litellm_params": {"custom_llm_provider": "openai"},
+            "standard_logging_object": {
+                "id": "test-id",
+                "call_type": "completion",
+                "metadata": {},
+            },
+        }
+
+        otel.set_attributes(span=mock_span, kwargs=kwargs, response_obj=None)
+
+        keys = {c.args[0] for c in mock_span.set_attribute.call_args_list if c.args}
+        self.assertNotIn(SpanAttributes.LLM_REQUEST_TEMPERATURE.value, keys)
+        self.assertNotIn(SpanAttributes.LLM_REQUEST_TOP_P.value, keys)
+        self.assertNotIn(SpanAttributes.LLM_REQUEST_MAX_TOKENS.value, keys)
+
+
 class TestOpenTelemetryProviderInitialization(unittest.TestCase):
     """Test suite for verifying provider initialization respects existing providers"""
 
```
