# huggingface/peft submission: `delete_adapter` leaves no active adapter when adapters target different modules

Everything below is local. Nothing has been posted to GitHub.

Repo policy reminders (from `AGENTS.md` / `CONTRIBUTING.md`, please read before posting):

- Open the issue first and wait for a maintainer comment containing `@peft-triage approved` on its own line before
  opening the PR (drafts included). PRs without an approved issue reference are auto-closed.
- Pure code-agent PRs are not allowed: the submitting human must review every changed line, run the tests and be able
  to defend the change. AI-assisted PRs must say so and list the tests that were run (done in the PR body below).
- Do NOT add the line "This PR was authored by a human." (the PR template asks for it only when the PR was mainly
  written by a human).
- Breaching the agent contribution guidelines can result in an automatic ban.

Branch: `fix/delete-adapter-heterogeneous-targets` (1 commit on top of `main` @ `116a979`) in
`/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/peft`.

---

## (a) Issue

No existing issue covers this. The closest are:

- #3512 / PR #3515 (merged 2026-09-15): the same first-layer heuristic was fixed for `PeftMixedModel` only. The PR
  explicitly left `tuners_utils.delete_adapter` alone, reasoning that "non-mixed models have homogeneous layers".
  That assumption does not hold: `PeftModel.add_adapter` with different `target_modules` is supported and is exactly
  the case that breaks here.
- #3743 (merged): restores trainability of the fallback adapter after deletion; different code path.

New issue draft (bug-report template):

**Title:** `delete_adapter` leaves `PeftModel` without an active adapter when the remaining adapter targets different modules

**System Info**

```
peft 0.21.1.dev0 (main @ 116a979), transformers 5.17.0, accelerate 1.15.0, torch 2.14.0 (CPU), python 3.11.15, Linux x86_64
```

**Who can help?**

@BenjaminBossan @githubnemo

**Reproduction**

```python
import torch
from torch import nn
from peft import LoraConfig, get_peft_model


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.lin0 = nn.Linear(10, 20)
        self.lin1 = nn.Linear(20, 2)

    def forward(self, x):
        return self.lin1(self.lin0(x))


model = get_peft_model(MLP(), LoraConfig(target_modules=["lin0"]), adapter_name="adapter0")
model.add_adapter("adapter1", LoraConfig(target_modules=["lin1"]))
assert model.active_adapters == ["adapter0"]

model.delete_adapter("adapter0")
print(model.active_adapters)  # [] -- expected ['adapter1']
print(model.active_adapter)  # 'adapter0' -- the adapter that was just deleted
print(model.base_model.model.lin1.active_adapters)  # ['adapter1'] -- the layer itself did switch
model(torch.randn(2, 10))
```

Traceback:

```
Traceback (most recent call last):
  File "mre_delete_adapter.py", line 26, in <module>
    model(torch.randn(2, 10))  # KeyError: 'adapter0'
  File ".../torch/nn/modules/module.py", line 1783, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File ".../torch/nn/modules/module.py", line 1794, in _call_impl
    return forward_call(*args, **kwargs)
  File ".../peft/src/peft/peft_model.py", line 1019, in forward
    with self._enable_peft_forward_hooks(*args, **kwargs):
  File "/usr/lib/python3.11/contextlib.py", line 137, in __enter__
    return next(self.gen)
  File ".../peft/src/peft/peft_model.py", line 1006, in _enable_peft_forward_hooks
    if hasattr(self.base_model, "_enable_peft_forward_hooks") and self.has_active_enabled_adapter:
  File ".../peft/src/peft/peft_model.py", line 240, in has_active_enabled_adapter
    if self.peft_config[self.active_adapter].is_prompt_learning:
KeyError: 'adapter0'
```

Root cause: `peft.tuners.tuners_utils.delete_adapter` takes the new active adapter from the *first* tuner layer it
visits (`if new_adapter is None: new_adapter = target.active_adapters[:]`). When the deleted adapter was the only
adapter on that layer (here `lin0`), the layer has no adapter left and reports `[]`, which is then used as the new
active adapter for the whole model (`self.active_adapter = new_adapter or []`) and passed to the auxiliary wrappers.
Other layers (here `lin1`) do switch to `adapter1`, so the model is in an inconsistent state, and
`PeftModel.delete_adapter` keeps the stale `active_adapter` because `len(new_active_adapters) != 1`.

The same defect was fixed for `PeftMixedModel` in #3515, which left this function untouched on the assumption that
non-mixed models always have homogeneous layers. The order of the layers matters: swapping the two `target_modules`
above (adapter0 on `lin1`, adapter1 on `lin0`) works, because the first visited layer then still hosts `adapter1`.

**Expected behavior**

After deleting the active adapter, the remaining adapter becomes active (`model.active_adapters == ["adapter1"]`),
like it already does when both adapters target the same modules, and `forward` works.

I intend to provide the PR (one-line fix in `tuners_utils.delete_adapter` plus a regression test in
`tests/test_custom_models.py`).

---

## (b) PR

**Title:** FIX Choose new active adapter across all layers after delete_adapter

**Body:**

Fixes #N (replace with the issue number once it is approved with `@peft-triage approved`).

When the deleted adapter and the remaining adapter(s) target different modules, the first tuner layer visited by
`delete_adapter` may no longer host any adapter after the deletion. Its empty `active_adapters` was then used as the
new active adapter for the whole model, leaving `PeftModel.active_adapter` pointing at the deleted adapter and
`forward` raising `KeyError`. This is the non-mixed counterpart of #3515: keep looking until a layer with a remaining
active adapter is found.

Changes:

- `src/peft/tuners/tuners_utils.py`: in `delete_adapter`, replace `if new_adapter is None:` with
  `if not new_adapter:` (plus a comment). The return value stays a list (or `[]`/`None` when nothing is active), so
  callers are unchanged.
- `tests/test_custom_models.py`: add
  `TestPeftCustomModel::test_delete_active_adapter_with_adapters_targeting_different_modules`, which fails on `main`
  with `KeyError: 'adapter0'` and passes with the fix.

Tests run (CPU only, Hub access blocked in my environment, so tests needing model downloads fail with a proxy 403
before and after the change):

- `pytest tests/test_custom_models.py -k "delete_adapter or delete_active_adapter"`: 666 passed, 6 skipped, 1 failed
  (`test_delete_adapter_multiple_adapters_with_trainable_token_indices`, Hub download 403; identical on `main`).
- `pytest tests/test_mixed.py -k delete`: 5 passed.
- `pytest tests/test_tuners_utils.py`: 216 passed, 15 skipped, 31 failed (all `httpx.ProxyError: 403` on Hub
  downloads; identical on `main`).
- `ruff check` / `ruff format --check` (ruff 0.16.4) on `src tests examples docs scripts`: clean. `make quality` was
  not run in full because `hf-doc-builder` was not installed.

AI assistance disclosure: this PR was prepared with AI assistance (Claude Code, model `claude-fable-5-1`). The
diagnosis, fix and test were produced by the model; the submitting human has reviewed every changed line and re-run
the tests listed above before submitting.

Reviewer to tag: @BenjaminBossan (also @githubnemo, who reviewed #3515).

---

## (c) Commands and results

```
# venv: python3 -m venv venv; pip install torch (PyPI wheel, --no-deps; download.pytorch.org blocked) transformers
#       accelerate pytest pytest-cov diffusers datasets pyyaml parameterized scikit-learn scipy ruff==0.16.4; pip install -e peft --no-deps
$ cd peft && git checkout -b fix/delete-adapter-heterogeneous-targets main

# MRE before the fix (probes/mre_delete_adapter.py)
$ python ../probes/mre_delete_adapter.py
KeyError: 'adapter0'

# MRE after the fix
$ python ../probes/mre_delete_adapter.py
active_adapters: ['adapter1']
active_adapter: adapter1
lin1 active: ['adapter1']

# new test fails without the source change (only the test applied), passes with it
$ git stash push src/peft/tuners/tuners_utils.py && pytest tests/test_custom_models.py -q -o addopts="" -k "delete_adapter or delete_active_adapter"
FAILED tests/test_custom_models.py::TestPeftCustomModel::test_delete_active_adapter_with_adapters_targeting_different_modules
16 failed, 651 passed, 6 skipped   (15 of the failures: 14 AdaMSS without scikit-learn at the time, 1 Hub 403)
$ git stash pop

$ pytest tests/test_custom_models.py -q -o addopts="" -k "delete_adapter or delete_active_adapter"
1 failed, 666 passed, 6 skipped   (failure: ..._with_trainable_token_indices, httpx.ProxyError: 403 Forbidden on Hub)
$ pytest tests/test_mixed.py -q -o addopts="" -k delete
5 passed, 33 deselected
$ pytest tests/test_tuners_utils.py -q -o addopts=""
31 failed, 216 passed, 15 skipped   (all 31: httpx.ProxyError: 403 Forbidden on Hub downloads)

$ ruff check src tests examples docs scripts
All checks passed!
$ ruff format --check src tests examples docs scripts
427 files already formatted

$ git log --oneline -1
9e3667b FIX Choose new active adapter across all layers after delete_adapter
```

(`-o addopts=""` only drops the `--cov` options from `pyproject.toml`.)

---

## (d) `git diff main`

```diff
diff --git a/src/peft/tuners/tuners_utils.py b/src/peft/tuners/tuners_utils.py
index e9094bb..d05b06a 100644
--- a/src/peft/tuners/tuners_utils.py
+++ b/src/peft/tuners/tuners_utils.py
@@ -2701,7 +2701,9 @@ def delete_adapter(
             continue
         if isinstance(target, layer_cls):
             target.delete_adapter(adapter_name)
-            if new_adapter is None:
+            # Adapters can target different layers, so a layer that only hosted the deleted adapter is left without
+            # any active adapter. Keep looking until a layer with a remaining active adapter is found.
+            if not new_adapter:
                 new_adapter = target.active_adapters[:]
 
     _delete_auxiliary_adapter(model, adapter_name=adapter_name, new_active_adapters=new_adapter)
diff --git a/tests/test_custom_models.py b/tests/test_custom_models.py
index b7af802..be346d9 100644
--- a/tests/test_custom_models.py
+++ b/tests/test_custom_models.py
@@ -4094,6 +4094,26 @@ class TestPeftCustomModel(PeftCommonTester):
         assert model.active_adapters == ["adapter1"]
         model(**inputs)  # does not raise
 
+    def test_delete_active_adapter_with_adapters_targeting_different_modules(self):
+        # The active adapter targets lin0 and the other adapter targets lin1. After deleting the active adapter, the
+        # remaining adapter should become active and forward should work. Previously, the new active adapter was
+        # taken from the first tuner layer (lin0), which had no adapter left, so the model ended up with no active
+        # adapter and forward raised a KeyError.
+        config0 = LoraConfig(target_modules=["lin0"])
+        config1 = LoraConfig(target_modules=["lin1"])
+        model = get_peft_model(MLP(), config0, adapter_name="adapter0").to(self.torch_device)
+        model.add_adapter("adapter1", config1)
+
+        inputs = self.prepare_inputs_for_testing()
+        assert model.active_adapters == ["adapter0"]
+        model(**inputs)  # does not raise
+
+        model.delete_adapter("adapter0")
+        assert model.active_adapters == ["adapter1"]
+        assert model.active_adapter == "adapter1"
+        assert model.base_model.model.lin1.active_adapters == ["adapter1"]
+        model(**inputs)  # does not raise
+
     def test_delete_adapter_multiple_adapters_with_modules_to_save(self):
         # There are 3 adapters. Adapter 0 has modules_to_save. Delete it, we should switch to adapter 1, which does not
         # have modules_to_save. Then, we delete it too, switching to adapter 2, which has modules_to_save. Finally, we
```

Files:
- MRE: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/probes/mre_delete_adapter.py`
- Diff: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/peft-fix.diff`
