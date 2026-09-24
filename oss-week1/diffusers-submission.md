# diffusers submission: EDMEulerScheduler.set_timesteps crashes when `sigmas` is a list

Branch: `fix/edm-euler-sigmas-list` (local only, commit 85b26f2 on top of main e0118ad)
Repo: /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/diffusers
MRE: /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/probe/mre_edm_euler_sigmas.py

Nothing has been posted to GitHub. Per the repo's AI policy, open the issue first, wait for a maintainer
acknowledgment, then open the PR.

---

## (a) Issue

Existing issue: none found (searched issues/PRs for "EDMEulerScheduler sigmas list", "EDMEuler"; the only
related PR is #10734, merged Feb 2025, which added the `sigmas` argument and only exercised a tensor).

### New issue draft (bug-report template)

**Title:** `EDMEulerScheduler.set_timesteps(sigmas=[...])` raises AttributeError even though `sigmas` is typed `list[float]`

**Describe the bug**

`EDMEulerScheduler.set_timesteps` declares `sigmas: torch.Tensor | list[float] | None` and its docstring says
"Custom sigmas to use for the denoising process", but the implementation only handles a tensor or a bare float.
Passing a Python list, which is the type the pipelines' `retrieve_timesteps` helper forwards for the `sigmas`
argument, fails with `AttributeError: 'list' object has no attribute 'to'`.

I intend to submit a PR for this (one-line fix: treat `list` like `float` in the `torch.tensor(...)` branch,
plus a regression test in `tests/schedulers/test_scheduler_edm_euler.py`).

**Reproduction**

```python
import torch
from diffusers import EDMEulerScheduler

scheduler = EDMEulerScheduler()
ramp = [0.0, 0.5, 1.0]

scheduler.set_timesteps(sigmas=torch.tensor(ramp))  # works
scheduler.set_timesteps(sigmas=ramp)                # AttributeError
```

**Logs**

```shell
Traceback (most recent call last):
  File "mre_edm_euler_sigmas.py", line 10, in <module>
    scheduler.set_timesteps(sigmas=ramp)
  File "src/diffusers/schedulers/scheduling_edm_euler.py", line 299, in set_timesteps
    sigmas = sigmas.to(sigmas_dtype)
             ^^^^^^^^^
AttributeError: 'list' object has no attribute 'to'
```

**System Info**

```
- 🤗 Diffusers version: 0.41.0.dev0
- Platform: Linux-6.18.44-fc-v37-x86_64-with-glibc2.39
- Running on Google Colab?: No
- Python version: 3.11.15
- PyTorch version (GPU?): 2.14.0+cu130 (False)
- Huggingface_hub version: 1.32.0
- Transformers version: 5.17.0
- Accelerate version: not installed
- PEFT version: not installed
- Safetensors version: 0.8.0
- xFormers version: not installed
- Accelerator: NA
- Using GPU in script?: <fill in>
- Using distributed or parallel set-up in script?: <fill in>
- Using GPU in script?: No
- Using distributed or parallel set-up in script?: No
```

**Who can help?**

@yiyixuxu

---

## (b) Pull request

**Title:** Fix `EDMEulerScheduler.set_timesteps` crashing when `sigmas` is a list

**Body (PR template):**

# What does this PR do?

`EDMEulerScheduler.set_timesteps` accepts `sigmas: torch.Tensor | list[float] | None`, but only the tensor and
float cases were handled, so a list raised `AttributeError: 'list' object has no attribute 'to'`. This converts a
list with `torch.tensor` the same way a float already is, and adds a regression test checking that a list and the
equivalent tensor produce identical `scheduler.sigmas`.

Fixes #N  <!-- replace with the issue number once opened -->

Coordination: <link to the issue comment where a maintainer acknowledged the fix>

**Tests run**

```
$ pytest tests/schedulers/test_scheduler_edm_euler.py -q
24 passed, 1 skipped in 3.61s

# new test fails on main (source change stashed), passes with the fix:
$ pytest tests/schedulers/test_scheduler_edm_euler.py::EDMEulerSchedulerTest::test_custom_sigmas_as_list -q
E   AttributeError: 'list' object has no attribute 'to'      # before
1 passed                                                     # after

$ ruff check examples scripts src tests utils benchmarks setup.py   # ruff==0.9.10 as pinned in setup.py
All checks passed!
$ ruff format --check examples scripts src tests utils benchmarks setup.py
2090 files already formatted
$ python utils/check_copies.py   # exit 0
```

AI-assistance disclosure: this change was found and drafted with the help of an AI coding agent (Claude Code);
I reviewed the diff, ran the reproduction and the tests above myself, and I am responsible for the change.

Self-review notes: the diff is one line in the scheduler plus one test. No `# Copied from` block is affected
(`utils/check_copies.py` passes). Not changed on purpose: the pre-existing `float` branch produces a 0-dim
tensor, which is out of scope for this fix.

## Before submitting
- [x] Did you use an AI agent to help with this PR? Yes, see disclosure above.
  - [x] Read the "Coding with AI agents" guide
  - [x] Ran the self-review skill on the diff (notes above)
  - [x] Shared the self-review notes in the description
- [x] Did you read the contributor guideline?
- [ ] Was this discussed/approved via a GitHub issue? Link: #N
- [x] Did you write any new necessary tests?

## Who can review?

Schedulers: @yiyixuxu @dg845

---

## (c) Exact commands and results

```
cd /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/diffusers
uv venv && uv pip install --no-deps torch && uv pip install sympy networkx jinja2 fsspec filelock typing_extensions setuptools
uv pip install -e ".[test]" "ruff==0.9.10"
# (download.pytorch.org is blocked by the sandbox proxy; the PyPI torch wheel runs fine on CPU.)

.venv/bin/python ../probe/mre_edm_euler_sigmas.py
# before: AttributeError: 'list' object has no attribute 'to'
# after : list ok: tensor([8.0000e+01, 2.5152e+00, 2.0000e-03, 0.0000e+00])

.venv/bin/python -m pytest tests/schedulers/test_scheduler_edm_euler.py -q     # 24 passed, 1 skipped
.venv/bin/python -m pytest tests/schedulers -q                                  # 968 passed, 13 skipped, 1 failed
#   the 1 failure (SchedulerBaseTests::test_default_arguments_not_in_config) is an httpx 403 from the sandbox
#   proxy when downloading a Hub checkpoint; unrelated to this change and fails identically on main.
.venv/bin/ruff check examples scripts src tests utils benchmarks setup.py       # All checks passed!
.venv/bin/ruff format --check examples scripts src tests utils benchmarks setup.py
.venv/bin/python utils/check_copies.py                                          # exit 0
```

## (d) git diff main

```diff
diff --git a/src/diffusers/schedulers/scheduling_edm_euler.py b/src/diffusers/schedulers/scheduling_edm_euler.py
index dfb70ce..a7b78ff 100644
--- a/src/diffusers/schedulers/scheduling_edm_euler.py
+++ b/src/diffusers/schedulers/scheduling_edm_euler.py
@@ -293,7 +293,7 @@ class EDMEulerScheduler(SchedulerMixin, ConfigMixin):
         sigmas_dtype = torch.float32 if torch.backends.mps.is_available() else torch.float64
         if sigmas is None:
             sigmas = torch.linspace(0, 1, self.num_inference_steps, dtype=sigmas_dtype)
-        elif isinstance(sigmas, float):
+        elif isinstance(sigmas, (float, list)):
             sigmas = torch.tensor(sigmas, dtype=sigmas_dtype)
         else:
             sigmas = sigmas.to(sigmas_dtype)
diff --git a/tests/schedulers/test_scheduler_edm_euler.py b/tests/schedulers/test_scheduler_edm_euler.py
index acac4b1..c4abe27 100644
--- a/tests/schedulers/test_scheduler_edm_euler.py
+++ b/tests/schedulers/test_scheduler_edm_euler.py
@@ -80,6 +80,19 @@ class EDMEulerSchedulerTest(SchedulerCommonTest):
         assert abs(result_sum.item() - 34.1855) < 1e-3
         assert abs(result_mean.item() - 0.044) < 1e-3
 
+    def test_custom_sigmas_as_list(self):
+        scheduler = self.scheduler_classes[0](**self.get_scheduler_config())
+        ramp = [0.0, 0.5, 1.0]
+
+        scheduler.set_timesteps(sigmas=ramp)
+        sigmas_from_list = scheduler.sigmas
+
+        scheduler.set_timesteps(sigmas=torch.tensor(ramp))
+        assert torch.equal(sigmas_from_list, scheduler.sigmas)
+
+        scheduler.set_timesteps(num_inference_steps=len(ramp))
+        assert torch.allclose(sigmas_from_list, scheduler.sigmas)
+
     # Override test_from_save_pretrained to use EDMEulerScheduler-specific logic
     def test_from_save_pretrained(self):
         kwargs = dict(self.forward_default_kwargs)
```
