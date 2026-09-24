# llama_index contribution: `html_to_df` drops HTML tables with `<th>` header cells

Local branch: `fix/html-to-df-th-header` (1 commit on top of `main` @ 872255c) in
`/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/llama_index`.

Nothing has been posted to GitHub. Everything below is a draft.

---

## (a) Issue

No existing open/closed issue or PR covers this (searched: `is:pr html_to_df th`,
`html_to_df OR text_as_html th header UnstructuredElementNodeParser`; closest hits
#14301 [type-check fix, merged 2024], #14695 [colspan, not planned], #22373
[no-table crash, abandoned] are all different defects). Draft below uses the repo's
"Bug Report" issue form (`.github/ISSUE_TEMPLATE/issue-form.yml`).

### Title

[Bug]: `html_to_df` returns `None` for tables with `<th>` header cells, so UnstructuredElementNodeParser silently drops them

### Bug Description

`llama_index.core.node_parser.relational.utils.html_to_df` only collects `<td>`
cells from each `<tr>`:

```python
for row in rows:
    cols = row.xpath(".//td")
```

A header row written with `<th>` cells (the standard, and what
`unstructured.partition.html` emits verbatim in `Table.metadata.text_as_html`)
therefore yields an empty first row. The following "all rows have the same number
of columns as `data[0]`" check then fails for every data row and the function
returns `None`.

`UnstructuredElementNodeParser.filter_table` treats a `None` dataframe as "not a
table", so every `<th>`-headed table is demoted to a plain `Text` element: no table
summary is generated and no `IndexNode` is produced. The only tables that survive
are ones whose header row is written with `<td>` (which is what the existing unit
test happens to use).

A secondary symptom: for the non-standard shape `<thead><th>..</th></thead>`
(header cells with no `<tr>`), the header is skipped by `.//tr` and the first data
row is silently promoted to the header. That case is not changed by this fix.

### Version

llama-index-core 0.14.25 (main @ 872255c); reproduced with lxml 6.1.3 and unstructured 0.27.8.

### Steps to Reproduce

CPU-only, no API calls (`MockLLM`). Requires `lxml` and `unstructured`.

```python
from llama_index.core.llms.mock import MockLLM
from llama_index.core.node_parser.relational.unstructured_element import (
    UnstructuredElementNodeParser,
)
from llama_index.core.node_parser.relational.utils import html_to_df
from llama_index.core.schema import Document, IndexNode

TH_TABLE = (
    "<table><thead><tr><th>Year</th><th>Benefits</th></tr></thead>"
    "<tbody><tr><td>2020</td><td>12,000</td></tr>"
    "<tr><td>2021</td><td>10,000</td></tr></tbody></table>"
)
TD_TABLE = TH_TABLE.replace("<th>", "<td>").replace("</th>", "</td>")

print(html_to_df(TH_TABLE))   # None            <-- bug
print(html_to_df(TD_TABLE))   # 2x2 DataFrame

parser = UnstructuredElementNodeParser(llm=MockLLM())
for label, table in [("<th>", TH_TABLE), ("<td>", TD_TABLE)]:
    doc = Document(text=f"<html><body><p>Intro</p>{table}<p>Outro</p></body></html>")
    nodes = parser.get_nodes_from_documents([doc])
    print(label, [type(n).__name__ for n in nodes])
```

Expected: both variants parse to a DataFrame with columns `["Year", "Benefits"]`,
and both documents produce a table `IndexNode` (plus text nodes).

Actual:

```
None
   Year Benefits
0  2020   12,000
1  2021   10,000
<th> ['TextNode']                                        <-- table lost
<td> ['TextNode', 'IndexNode', 'TextNode', 'TextNode']
```

### Relevant Logs/Tracebacks

No exception is raised; the table is dropped silently (see output above).

### Root cause / proposed fix

Include `<th>` cells when reading each row: `row.xpath(".//td|.//th")`.
One-line change in `llama_index/core/node_parser/relational/utils.py`.

---

## (b) Pull request

### Title

fix(core): parse HTML tables with `<th>` header cells in `html_to_df`

### Body (follows `.github/pull_request_template.md`)

# Description

`html_to_df` only collected `<td>` cells per row, so a table whose header row uses
`<th>` cells produced an empty first row. The subsequent "all rows have the same
number of columns" check then failed and the function returned `None`.
`UnstructuredElementNodeParser.filter_table` relies on that return value, so every
`<th>`-headed table (which is exactly what `unstructured` emits in
`text_as_html` for standard HTML tables) was silently demoted to plain text
instead of being extracted as a table / `IndexNode`.

This PR collects both `<td>` and `<th>` cells per row (`.//td|.//th`) and adds
regression tests for `html_to_df` directly and for end-to-end table extraction
through `UnstructuredElementNodeParser`.

Fixes #<issue number once the issue above is filed>

AI-assistance disclosure (per CONTRIBUTING.md "How to Use AI when Contributing"):
the bug was found, the fix written and the tests drafted with the help of an AI
assistant (Claude). The change was verified by running the reproduction script
before/after the fix, confirming the new tests fail on unpatched `main` and pass
with the patch, and running the full `tests/node_parser` suite plus ruff,
ruff-format, codespell and mypy on the touched files. I have reviewed and
understand the change.

## New Package?

Did I fill in the `tool.llamahub` section in the `pyproject.toml` and provide a detailed README.md for my new integration or package?

- [ ] Yes
- [x] No

## Version Bump?

Did I bump the version in the `pyproject.toml` file of the package I am updating? (Except for the `llama-index-core` package)

- [ ] Yes
- [x] No (llama-index-core)

## Type of Change

- [x] Bug fix (non-breaking change which fixes an issue)

## How Has This Been Tested?

- [x] I added new unit tests to cover this change
  - `tests/node_parser/test_unstructured.py::test_html_to_df_with_th_header` (needs lxml)
  - `tests/node_parser/test_unstructured.py::test_html_table_extraction_with_th_header` (needs lxml + unstructured, uses `MockLLM`)
  - Both fail on unpatched `main` (`assert None is not None` / `assert 0 == 1`) and pass with the fix.

## Suggested Checklist:

- [x] I have performed a self-review of my own code
- [x] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation (n/a)
- [ ] I have added Google Colab support for the newly added notebooks. (n/a)
- [x] My changes generate no new warnings
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes
- [x] I ran `uv run make format; uv run make lint` to appease the lint gods (see note in (c): the root `uv sync` could not resolve here because `pypi.nvidia.com` is unreachable through the sandbox proxy, so the same hooks — ruff 0.11.11 check + format, codespell, mypy — were run directly on the touched files.)

---

## (c) Commands run and results

Environment note: `uv sync` (root and `llama-index-core`) fails in this sandbox because
the project's extra index `https://pypi.nvidia.com` is blocked by the egress proxy.
The core venv was populated instead with
`uv pip install --no-config --index-url https://pypi.org/simple -e llama-index-core -e llama-index-instrumentation -e llama-index-integrations/llms/llama-index-llms-openai pytest pytest-asyncio pytest-mock==3.11.1 pytest-timeout pytest-dotenv==0.5.2 "pytest-cov~=5.0" pandas tree-sitter "tree-sitter-language-pack<1.0" ruff==0.11.11 black rake-nltk==1.0.6 "numpy<2.4"`
plus `lxml`, `unstructured`, `codespell[toml]`, `mypy==1.11.0`. tiktoken's
`cl100k_base` download and NLTK downloads are also blocked; an on-disk copy of the
encoding was staged in `TIKTOKEN_CACHE_DIR` and NLTK data fetched with
`NLTK_ALLOW_PROXIED_URLOPEN=1` into `NLTK_DATA`. Neither affects the touched code.

```
# baseline (before any change): full core suite
$ .venv/bin/python -m pytest tests/ -q --continue-on-collection-errors --deselect tests/evaluation
15 failed, 1408 passed, 22 skipped, 47 deselected, 6 xfailed, 29 errors
  (all 15 failures + 29 errors are network fetches blocked by the sandbox proxy:
   image URL/path loading, non-cached tiktoken encodings; unrelated to this change)

# reproduction script (scratchpad/oss/repro_html_to_df_th.py), BEFORE fix
html_to_df(<th> header) -> None
html_to_df(<td> header) -> 2x2 DataFrame
<th> header: 1 nodes, 0 IndexNode(s) -> ['TextNode']
<td> header: 4 nodes, 1 IndexNode(s) -> ['TextNode', 'IndexNode', 'TextNode', 'TextNode']

# reproduction script, AFTER fix
html_to_df(<th> header) -> 2x2 DataFrame (Year, Benefits)
<th> header: 4 nodes, 1 IndexNode(s) -> ['TextNode', 'IndexNode', 'TextNode', 'TextNode']
<td> header: 4 nodes, 1 IndexNode(s) -> ['TextNode', 'IndexNode', 'TextNode', 'TextNode']

# new tests WITHOUT the fix (utils.py stashed)
$ .venv/bin/python -m pytest tests/node_parser/test_unstructured.py -q -k th_header
E       assert None is not None
E       assert 0 == 1
2 failed, 1 deselected in 2.20s

# new tests + touched modules WITH the fix
$ .venv/bin/python -m pytest tests/node_parser/test_unstructured.py tests/node_parser/test_markdown_element.py -q
12 passed in 3.22s

# whole node_parser suite WITH the fix
$ .venv/bin/python -m pytest tests/node_parser -q
51 passed, 6 skipped in 3.18s

# lint (same hooks as .pre-commit-config.yaml, run on the touched files)
$ ruff check <files>            -> All checks passed!
$ ruff format --check <files>   -> 2 files already formatted
$ codespell <files>             -> clean
$ mypy --ignore-missing-imports --follow-imports=skip llama_index/core/node_parser/relational/utils.py
Success: no issues found in 1 source file

# git
$ git config user.name HS1CMU && git config user.email the.heathsun@gmail.com
$ git checkout -b fix/html-to-df-th-header main
$ git commit  -> 68062dc fix(core): parse HTML tables with <th> header cells in html_to_df
```

Files changed:
- `llama-index-core/llama_index/core/node_parser/relational/utils.py`
- `llama-index-core/tests/node_parser/test_unstructured.py`

Reproduction script (not in repo): `/tmp/claude-0/-home-user-a/9c0f4845-67eb-57b5-b011-a5843a24456f/scratchpad/oss/repro_html_to_df_th.py`

---

## (d) `git diff main`

```diff
diff --git a/llama-index-core/llama_index/core/node_parser/relational/utils.py b/llama-index-core/llama_index/core/node_parser/relational/utils.py
index 4d51c83..6725276 100644
--- a/llama-index-core/llama_index/core/node_parser/relational/utils.py
+++ b/llama-index-core/llama_index/core/node_parser/relational/utils.py
@@ -59,7 +59,10 @@ def html_to_df(html_str: str) -> Any:
 
     data = []
     for row in rows:
-        cols = row.xpath(".//td")
+        # Header rows commonly use <th> cells; include them so the header is
+        # not dropped (which would leave the first row empty and make the
+        # column-count check below fail for every table with a <th> header).
+        cols = row.xpath(".//td|.//th")
         cols = [c.text.strip() if c.text is not None else "" for c in cols]
         data.append(cols)
 
diff --git a/llama-index-core/tests/node_parser/test_unstructured.py b/llama-index-core/tests/node_parser/test_unstructured.py
index 4c97959..7ad24a7 100644
--- a/llama-index-core/tests/node_parser/test_unstructured.py
+++ b/llama-index-core/tests/node_parser/test_unstructured.py
@@ -103,3 +103,38 @@ def test_html_table_extraction() -> None:
     assert isinstance(nodes[3], TextNode)
     assert isinstance(nodes[4], IndexNode)
     assert isinstance(nodes[5], TextNode)
+
+
+TH_HEADER_TABLE = (
+    "<table><thead><tr><th>Year</th><th>Benefits</th></tr></thead>"
+    "<tbody><tr><td>2020</td><td>12,000</td></tr>"
+    "<tr><td>2021</td><td>10,000</td></tr></tbody></table>"
+)
+
+
+@pytest.mark.skipif(html is None, reason="lxml not installed")
+def test_html_to_df_with_th_header() -> None:
+    """Tables whose header row uses <th> cells must still be parsed."""
+    from llama_index.core.node_parser.relational.utils import html_to_df
+
+    table_df = html_to_df(TH_HEADER_TABLE)
+
+    assert table_df is not None
+    assert list(table_df.columns) == ["Year", "Benefits"]
+    assert table_df.values.tolist() == [["2020", "12,000"], ["2021", "10,000"]]
+
+
+@pytest.mark.skipif(partition_html is None, reason="unstructured not installed")
+@pytest.mark.skipif(html is None, reason="lxml not installed")
+def test_html_table_extraction_with_th_header() -> None:
+    """A <th>-headed table is extracted as a table node, not demoted to text."""
+    test_data = Document(
+        text=f"<html><body><p>Intro</p>{TH_HEADER_TABLE}<p>Outro</p></body></html>"
+    )
+
+    node_parser = UnstructuredElementNodeParser(llm=MockLLM())
+    nodes = node_parser.get_nodes_from_documents([test_data])
+
+    index_nodes = [n for n in nodes if isinstance(n, IndexNode)]
+    assert len(index_nodes) == 1
+    assert "Benefits" in index_nodes[0].get_content()
```
