# MLflow contribution: `span.attributes.<key>` equality filters never match in `search_traces` (SQLAlchemy store)

- Repo: mlflow/mlflow, base commit `eca4e1d` (master, 2026-09-24)
- Local branch: `fix/span-attribute-equality-search` (commit `b84cc3e`, DCO signed-off by `HS1CMU <the.heathsun@gmail.com>`)
- Local clone: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/mlflow`
- Repro script: `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/probe/repro_span_attribute_equality.py`
- Nothing has been posted to GitHub. No existing issue or PR covers this bug (searched
  `is:issue span.attributes search_traces`, `is:pr span.attributes search_traces`, and a broader
  `"span.attributes" equality trace filter` query on 2026-09-24: no matches).

---

## (a) New issue draft (bug report template)

**Title:** `[BUG] search_traces: span.attributes.<key> = '<value>' never matches, != matches everything, IN/NOT IN raise an internal error (SQLAlchemy store)`

**Issues Policy acknowledgement**
- [x] I have read and agree to submit bug reports in accordance with the issues policy

**Where did you encounter this bug?**
Local machine

**MLflow version**
- Client: 3.16.2.dev0 (master, commit `eca4e1d`)
- Tracking server: same (SQLAlchemy store, `sqlite:///`)

**System information**
- OS Platform and Distribution: Linux 6.18 (x86_64)
- Python version: 3.11
- yarn version, if running the dev UI: n/a

**Describe the problem**

`mlflow.search_traces` / `MlflowClient.search_traces` accept `span.attributes.<key>` filters with the
comparators `=`, `!=`, `IN`, `NOT IN`, `LIKE`, `ILIKE` and `RLIKE`
(`SearchTraceUtils.VALID_SPAN_ATTRIBUTE_COMPARATORS`). On the SQLAlchemy tracking store only the
`LIKE`/`ILIKE`/`RLIKE` variants work:

- `span.attributes.model = 'gpt-4'` silently returns **no traces**, even when a span has exactly that attribute value.
- `span.attributes.model != 'gpt-4'` returns **every trace**, including the one whose span has `model = "gpt-4"`.
- `span.attributes.model IN ('gpt-4')` / `NOT IN (...)` raise
  `MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.`
  (an internal SQLAlchemy `ArgumentError` surfaced to the caller, not a validation error).

Root cause (`mlflow/store/tracking/sqlalchemy_store.py`, `_get_filter_clauses_for_search_traces`,
`span.attributes.` branch): every comparator other than `RLIKE` falls into the `LIKE/ILIKE` branch,
which builds the wildcard pattern `%"<attr>"<value>%` and hands it to
`SearchTraceUtils.get_sql_comparison_func(comparator, dialect)`. For `=` that yields
`spans.content = '%"model"gpt-4%'` (a literal comparison against a `%...%` string, which can never
match the JSON content), for `!=` the negation of that (always true), and for `IN`/`NOT IN` a string
is passed where SQLAlchemy expects a list.

Expected: `=`/`IN` match traces that have a span whose attribute has exactly that value, `!=`/`NOT IN`
the complement (with the same "exists a span such that ..." semantics `span.name != ...` already has),
consistent with the other `span.*`, `tag.*`, `metadata.*` and `feedback.*` filters documented in
`docs/docs/genai/tracing/search-traces.mdx`.

**Tracking information**
```
MLflow version: 3.16.2.dev0
Tracking URI: sqlite:////tmp/.../mlflow.db
Registry URI: sqlite:////tmp/.../mlflow.db
```

**Code to reproduce issue**
```python
import tempfile

import mlflow
from mlflow import MlflowClient

tmp = tempfile.mkdtemp()
mlflow.set_tracking_uri(f"sqlite:///{tmp}/mlflow.db")
client = MlflowClient()
exp_id = mlflow.set_experiment("repro").experiment_id

with mlflow.start_span("root_a", attributes={"model": "gpt-4"}):
    pass
with mlflow.start_span("root_b", attributes={"model": "claude-3"}):
    pass
mlflow.flush_trace_async_logging()

names = {t.info.trace_id: t.data.spans[0].name for t in client.search_traces([exp_id])}


def search(filter_string):
    try:
        traces = client.search_traces([exp_id], filter_string=filter_string)
        return sorted(names[t.info.trace_id] for t in traces)
    except Exception as e:
        return f"{type(e).__name__}: {e}"


for f in [
    "span.attributes.model = 'gpt-4'",         # expected ['root_a']
    "span.attributes.model != 'gpt-4'",        # expected ['root_b']
    "span.attributes.model IN ('gpt-4')",      # expected ['root_a']
    "span.attributes.model NOT IN ('gpt-4')",  # expected ['root_b']
    "span.attributes.model LIKE '%gpt-4%'",    # works today: ['root_a']
]:
    print(f"{f:45s} -> {search(f)}")
```

Output on master (`eca4e1d`):
```
span.attributes.model = 'gpt-4'               -> []
span.attributes.model != 'gpt-4'              -> ['root_a', 'root_b']
span.attributes.model IN ('gpt-4')            -> MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.
span.attributes.model NOT IN ('gpt-4')        -> MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.
span.attributes.model LIKE '%gpt-4%'          -> ['root_a']
```

**Stack trace**
```
mlflow.exceptions.MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.
```
(raised from `sqlalchemy.sql.coercions` via `SearchUtils.get_sql_comparison_func` -> `column.in_(value)` in
`_get_filter_clauses_for_search_traces`; `=` and `!=` do not raise, they return wrong results.)

**Other info / logs**
The `span.attributes` filter is implemented as a substring match over the JSON `spans.content` column
(`# TODO: we should improve this by saving only the attributes into the table.`). Attribute values are
stored JSON-encoded inside that JSON, i.e. a string value appears as `"model": "\"gpt-4\""` and a
number/boolean as `"temperature": "0.7"` / `"streaming": "true"`.

**Willingness to contribute**
- [x] Yes. I can contribute a fix for this bug independently.

**What component(s) does this bug affect?**
- [x] `area/tracking`
- [x] `area/tracing`

---

## (b) Pull request

**Title:** `Fix span.attributes equality filters in search_traces for the SQLAlchemy store`

(Per the PR template: code references in the title use backticks, i.e.
``Fix `span.attributes.<key>` equality filters in `search_traces` for the SQLAlchemy store``.)

**Labels to request:** `area/tracking`, `area/tracing`, `rn/bug-fix`

**Body:**

```markdown
### Related Issues/PRs

Closes #<NEW_ISSUE_NUMBER>

### What changes are proposed in this pull request?

On the SQLAlchemy tracking store, `span.attributes.<key> = '<value>'` never matched any trace,
`!=` matched every trace, and `IN` / `NOT IN` raised an internal SQLAlchemy `ArgumentError`
("IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(...)%'").

The `span.attributes.` branch of `_get_filter_clauses_for_search_traces` reused the `LIKE`/`ILIKE`
wildcard pattern `%"<key>"<value>%` for every comparator except `RLIKE`, so `=` compared
`spans.content` against a literal `%...%` string, `!=` negated that (always true), and `IN` received
a string where SQLAlchemy expects a list.

This PR:

- Adds a dedicated branch for `=`, `!=`, `IN` and `NOT IN` that matches the JSON-encoded
  `"<key>": <value>` fragment of the span content exactly, using `LIKE` through the existing
  dialect-aware `SearchTraceUtils.get_sql_comparison_func` (so MySQL keeps its case-sensitive
  `BINARY` comparison and MSSQL its collation). Both the string-typed encoding
  (`"model": "\"gpt-4\""`) and the non-string encoding (`"temperature": "0.7"`, `"streaming": "true"`)
  are accepted, so `span.attributes.temperature = '0.7'` works for numeric attributes as the existing
  `LIKE "%0.7%"` test already expects. `!=` / `NOT IN` are the negation inside the same correlated
  `EXISTS` clause, matching the semantics `span.name != ...` already has.
- Adds `_span_attribute_like_pattern`, which escapes the fragment per dialect: MySQL and PostgreSQL
  treat backslash as the default `LIKE` escape character (so the `\"` produced by JSON encoding must
  be doubled, otherwise string values would still never match there), and MSSQL uses bracket escapes
  for `%`/`_`. SQLite has no default escape character, so the fragment is used as-is.
- Leaves the `LIKE`/`ILIKE`/`RLIKE` paths untouched.

Known limitation (unchanged from the existing substring-based implementation and its TODO): on SQLite,
`%` and `_` inside the compared value still act as `LIKE` wildcards because that dialect has no default
escape character.

### How is this PR tested?

- [x] Existing unit/integration tests
- [x] New unit/integration tests
- [x] Manual tests

New tests in `tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py`
(run for both `workspace-disabled` and `workspace-enabled`):

- `test_search_traces_with_span_attributes_equality_filters`: `=`, `!=`, `IN`, `NOT IN` on string,
  numeric and boolean attributes, exact (non-substring) matching, nonexistent keys/values, and
  combination with `span.type` in the same `EXISTS` clause.
- `test_span_attribute_like_pattern_escapes_per_dialect`: the per-dialect `LIKE` pattern escaping.

Manual: the repro script in the linked issue prints the expected results after the fix:

    span.attributes.model = 'gpt-4'               -> ['root_a']
    span.attributes.model != 'gpt-4'              -> ['root_b']
    span.attributes.model IN ('gpt-4')            -> ['root_a']
    span.attributes.model NOT IN ('gpt-4')        -> ['root_b']
    span.attributes.model LIKE '%gpt-4%'          -> ['root_a']

The new filter was also compiled against the `mysql`, `mssql`, `postgresql` and `sqlite` SQLAlchemy
dialects to confirm the generated SQL and bound parameters (e.g. MySQL:
`(spans.content LIKE %s AND BINARY spans.content LIKE %s) OR (...)` with
`'%"model\_name": "\\"gpt-4\\""%'`).

### Does this PR require documentation update?

- [x] No.

### Does this PR require updating the [MLflow Skills](https://github.com/mlflow/skills) repository?

- [x] No.

### Release Notes

#### Is this a user-facing change?

- [x] Yes. `search_traces` filters of the form `span.attributes.<key> = '<value>'`, `!=`, `IN` and
  `NOT IN` now work on the SQLAlchemy tracking store; previously `=` returned no traces, `!=` returned
  all traces and `IN`/`NOT IN` raised an internal error.

#### What component(s), interfaces, languages, and integrations does this PR affect?

Components

- [x] `area/tracking`: Tracking Service, tracking client APIs, autologging
- [x] `area/tracing`: MLflow Tracing features, tracing APIs, and LLM tracing functionality

<a name="release-note-category"></a>

#### How should the PR be classified in the release notes? Choose one:

- [x] `rn/bug-fix` - A user-facing bug fix worth mentioning in the release notes

#### Is this PR a critical bugfix or security fix that should go into the next patch release?

- [ ] This PR is critical and needs to be in the next patch release
- [x] This PR can wait for the next minor release
```

---

## (c) Commands run and results

Environment (Python 3.11 on PATH; `uv` for installs):

```bash
cd /tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/mlflow
uv venv .venv --python python3
uv pip install --python .venv/bin/python -e . -r requirements/test-requirements.txt "ruff==0.16.4" -e dev/clint
#  (pyspark was excluded from test-requirements on the rebuild after `uv run` recreated the venv;
#   it is not needed by the touched tests)
uv venv ../clint-venv --python /usr/bin/python3.10 && uv pip install --python ../clint-venv/bin/python -e dev/clint packaging
```

Note: `uv run --only-group lint ...` cannot be used here because the sandbox's `uv` is older than the
`exclude-newer = "P7D"` / `uv.lock` syntax the repo uses; `ruff` (pinned `0.16.4` as `pyproject.toml`
requires) and `clint` were run directly instead.

Reproduction (before fix, on `master`):

```bash
git stash && .venv/bin/python ../probe/repro_span_attribute_equality.py ; git stash pop
```
```
span.attributes.model = 'gpt-4'               -> []
span.attributes.model != 'gpt-4'              -> ['root_a', 'root_b']
span.attributes.model IN ('gpt-4')            -> MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.
span.attributes.model NOT IN ('gpt-4')        -> MlflowException: IN expression list, SELECT construct, or bound parameter object expected, got '%"model"(\'gpt-4\',)%'.
span.attributes.model LIKE '%gpt-4%'          -> ['root_a']
```

Reproduction (after fix):

```bash
.venv/bin/python ../probe/repro_span_attribute_equality.py
```
```
span.attributes.model = 'gpt-4'               -> ['root_a']
span.attributes.model != 'gpt-4'              -> ['root_b']
span.attributes.model IN ('gpt-4')            -> ['root_a']
span.attributes.model NOT IN ('gpt-4')        -> ['root_b']
span.attributes.model LIKE '%gpt-4%'          -> ['root_a']
```

Lint:

```bash
.venv/bin/ruff format mlflow/store/tracking/sqlalchemy_store.py tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
.venv/bin/ruff check  mlflow/store/tracking/sqlalchemy_store.py tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
#   -> "2 files already formatted" / "All checks passed!"
../clint-venv/bin/clint mlflow/store/tracking/sqlalchemy_store.py tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
#   -> "No errors found!"
```

Tests:

```bash
# baseline sanity on master before choosing the bug (unrelated pyspark-dependent test failed for env reasons):
.venv/bin/python -m pytest tests/utils tests/entities -x -q
#   -> 229 passed, 1 failed (tests/utils/test_databricks_utils.py::test_get_dbconnect_udf_sandbox_info, needs Spark/Java; unrelated)
.venv/bin/python -m pytest tests/store/tracking/test_file_store.py tests/store/artifact/test_local_artifact_repo.py tests/tracking/test_rest_tracking.py -q -x
#   -> passed (exit 0)

# new + existing span attribute tests (workspace-disabled and workspace-enabled variants):
.venv/bin/python -m pytest tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py -q -k "span_attribute"
#   -> 12 passed, 658 deselected

# broader search/span subset:
.venv/bin/python -m pytest tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py tests/utils/test_search_utils.py -q -k "search or span"
#   -> 581 passed, 258 deselected in 40.84s 
```

Dialect compilation check (script, not committed): the new clause was compiled with
`sqlalchemy.dialects.{mysql,mssql,postgresql,sqlite}` and produced valid SQL with the expected escaped
bound parameters for each dialect (see PR body). A real MySQL/PostgreSQL/MSSQL server was not available
in the sandbox (no Docker daemon), so those backends are covered by CI (`tests/db`) rather than locally.

Git:

```bash
git config user.name HS1CMU && git config user.email the.heathsun@gmail.com
git checkout -b fix/span-attribute-equality-search master
git add mlflow/store/tracking/sqlalchemy_store.py tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
git commit -s -F - <<'MSG' ... MSG     # -> b84cc3e, "Signed-off-by: HS1CMU <the.heathsun@gmail.com>", no Co-authored-by trailer
```

---

## (d) `git diff master`

```diff
diff --git a/mlflow/store/tracking/sqlalchemy_store.py b/mlflow/store/tracking/sqlalchemy_store.py
index b04176a..0f6299b 100644
--- a/mlflow/store/tracking/sqlalchemy_store.py
+++ b/mlflow/store/tracking/sqlalchemy_store.py
@@ -116,7 +116,7 @@ from mlflow.protos.databricks_pb2 import (
 )
 from mlflow.store.analytics import trace_correlation
 from mlflow.store.artifact.artifact_repository_registry import get_artifact_repository
-from mlflow.store.db.db_types import MSSQL, MYSQL
+from mlflow.store.db.db_types import MSSQL, MYSQL, POSTGRES
 from mlflow.store.entities.paged_list import PagedList
 from mlflow.store.tracking import (
     MAX_RESULTS_QUERY_TRACE_METRICS,
@@ -10423,6 +10423,24 @@ def _get_session_scoped_trace_ids(scoped_trace_query: Query, assessment_filters)
     )
 
 
+def _span_attribute_like_pattern(attr_name: str, encoded_value: str, dialect: str) -> str:
+    """
+    Build a LIKE pattern that matches the literal ``"<attr_name>": <encoded_value>`` fragment
+    inside a span's content JSON, escaping the fragment for the given dialect.
+
+    MySQL and PostgreSQL treat a backslash as the default LIKE escape character, so the
+    backslashes produced by JSON-encoding (e.g. the escaped quotes around string values) must
+    themselves be escaped there. MSSQL escapes wildcards with brackets. SQLite has no default
+    escape character, so backslashes are matched literally and wildcards cannot be escaped.
+    """
+    fragment = f"{json.dumps(attr_name)}: {encoded_value}"
+    if dialect in (MYSQL, POSTGRES):
+        fragment = fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
+    elif dialect == MSSQL:
+        fragment = fragment.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
+    return f"%{fragment}%"
+
+
 def _get_filter_clauses_for_search_traces(filter_string, session, dialect, scoped_trace_query):
     """
     Creates trace attribute filters and subqueries that will be inner-joined
@@ -10623,6 +10641,29 @@ def _get_filter_clauses_for_search_traces(filter_string, session, dialect, scope
                         val_filter = SearchTraceUtils.get_sql_comparison_func(comparator, dialect)(
                             SqlSpan.content, search_pattern
                         )
+                    elif comparator in ("=", "!=", "IN", "NOT IN"):
+                        # Attribute values are JSON-encoded inside the content JSON, so a
+                        # string value is stored as `"<attr>": "\"<value>\""` and a
+                        # non-string value (e.g. a number or boolean) as `"<attr>": "<value>"`.
+                        # Match either serialized form exactly instead of reusing the LIKE
+                        # wildcard pattern below, which never matches under `=`/`IN`.
+                        values = value if isinstance(value, (list, tuple)) else [value]
+                        like = SearchTraceUtils.get_sql_comparison_func("LIKE", dialect)
+                        matches_any = or_(
+                            *(
+                                like(
+                                    SqlSpan.content,
+                                    _span_attribute_like_pattern(attr_name, encoded, dialect),
+                                )
+                                for v in values
+                                for encoded in (json.dumps(json.dumps(v)), json.dumps(v))
+                            )
+                        )
+                        val_filter = (
+                            matches_any
+                            if comparator in ("=", "IN")
+                            else sqlalchemy.not_(matches_any)
+                        )
                     else:
                         # For LIKE/ILIKE, use wildcards for broad matching
                         val_filter = SearchTraceUtils.get_sql_comparison_func(comparator, dialect)(
diff --git a/tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py b/tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
index 619729f..26eb523 100644
--- a/tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
+++ b/tests/store/tracking/sqlalchemy_store/test_sqlalchemy_store_traces.py
@@ -54,7 +54,7 @@ from mlflow.protos.databricks_pb2 import (
     ErrorCode,
 )
 from mlflow.store.artifact.artifact_repo import ArtifactRepository
-from mlflow.store.db.db_types import MSSQL, MYSQL, POSTGRES
+from mlflow.store.db.db_types import MSSQL, MYSQL, POSTGRES, SQLITE
 from mlflow.store.tracking.dbmodels.models import (
     SqlSpan,
     SqlSpanMetrics,
@@ -1556,6 +1556,84 @@ def test_search_traces_with_span_attributes_filter(store: SqlAlchemyStore):
     assert traces[0].request_id == trace3_id
 
 
+def test_search_traces_with_span_attributes_equality_filters(store: SqlAlchemyStore):
+    exp_id = store.create_experiment("test_span_attributes_equality_search")
+
+    _create_trace(store, "trace1", exp_id)
+    _create_trace(store, "trace2", exp_id)
+    _create_trace(store, "trace3", exp_id)
+
+    store.log_spans(
+        exp_id,
+        [
+            create_test_span_with_content(
+                "trace1",
+                span_id=111,
+                custom_attributes={"model": "gpt-4", "temperature": 0.7, "streaming": True},
+            )
+        ],
+    )
+    store.log_spans(
+        exp_id,
+        [
+            create_test_span_with_content(
+                "trace2",
+                span_id=222,
+                custom_attributes={"model": "gpt-4-turbo", "temperature": 0.5},
+            )
+        ],
+    )
+    store.log_spans(
+        exp_id,
+        [
+            create_test_span_with_content(
+                "trace3",
+                span_id=333,
+                custom_attributes={"model": "claude-3", "temperature": 0.7},
+            )
+        ],
+    )
+
+    def search(filter_string):
+        traces, _ = store.search_traces([exp_id], filter_string=filter_string)
+        return sorted(t.request_id for t in traces)
+
+    # `=` must match the attribute value exactly, not as a substring
+    assert search("span.attributes.model = 'gpt-4'") == ["trace1"]
+    assert search("span.attributes.model = 'gpt-4-turbo'") == ["trace2"]
+    assert search("span.attributes.model = 'gpt'") == []
+    assert search("span.attributes.model = 'nonexistent'") == []
+    assert search("span.attributes.nonexistent = 'gpt-4'") == []
+
+    # Non-string attribute values are matched by their JSON representation
+    assert search("span.attributes.temperature = '0.7'") == ["trace1", "trace3"]
+    assert search("span.attributes.streaming = 'true'") == ["trace1"]
+
+    assert search("span.attributes.model != 'gpt-4'") == ["trace2", "trace3"]
+    assert search("span.attributes.model IN ('gpt-4', 'claude-3')") == ["trace1", "trace3"]
+    assert search("span.attributes.model NOT IN ('gpt-4', 'claude-3')") == ["trace2"]
+
+    # Equality filters combine with other span filters in the same EXISTS clause
+    assert search("span.attributes.model = 'gpt-4' AND span.type = 'LLM'") == ["trace1"]
+    assert search("span.attributes.model = 'gpt-4' AND span.type = 'RETRIEVER'") == []
+
+
+@pytest.mark.parametrize(
+    ("dialect", "expected"),
+    [
+        (SQLITE, '%"model_name": "\\"gpt-4\\""%'),
+        (MYSQL, '%"model\\_name": "\\\\"gpt-4\\\\""%'),
+        (POSTGRES, '%"model\\_name": "\\\\"gpt-4\\\\""%'),
+        (MSSQL, '%"model[_]name": "\\"gpt-4\\""%'),
+    ],
+)
+def test_span_attribute_like_pattern_escapes_per_dialect(dialect, expected):
+    pattern = sqlalchemy_store_module._span_attribute_like_pattern(
+        "model_name", json.dumps(json.dumps("gpt-4")), dialect
+    )
+    assert pattern == expected
+
+
 def test_search_traces_with_feedback_and_expectation_filters(store: SqlAlchemyStore):
     exp_id = store.create_experiment("test_feedback_expectation_search")
 
```
