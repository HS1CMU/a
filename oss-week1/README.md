# 第一周：7 个仓库，7 个 bug，7 个 PR 草稿

全部在本地完成，**没有向任何 GitHub 仓库发过 issue / PR / 评论**。每个仓库对应两个文件：
`<repo>-submission.md`（issue 草稿 + PR 草稿 + 运行过的命令与结果 + diff）和 `<repo>.patch`（`git am` 可直接应用，作者已是 HS1CMU）。

## 一览

| 仓库 | Bug | 改动 | 已有 issue/PR？ | 提交前置条件 |
|------|-----|------|-----------------|-------------|
| BerriAI/litellm | OpenTelemetry 与 Arize 回调用真值判断 `temperature`/`top_p`/`max_tokens`，值为 0 时 span 属性丢失 | 2 个源文件各 3 行 + 4 个测试 | 无 | 签 CLA；PR 至少 1 个测试（已加） |
| huggingface/diffusers | `EDMEulerScheduler.set_timesteps(sigmas=[...])` 传 list 时 `AttributeError`，但签名声明接受 list | 1 行 + 1 个测试 | 无 | 先开 issue 等维护者回应再开 PR |
| run-llama/llama_index | `html_to_df` 只取 `<td>`，`<th>` 表头的表格被判为非表格，unstructured 解析出的表全部降级成纯文本 | 1 行 + 2 个测试 | 无 | 无硬性前置 |
| vllm-project/vllm | Anthropic `/v1/messages` 收到 `tools: []` 时绕过校验，被当成 auto tool call 而返回 400 | 5 行 + 3 个测试 | 无（候选 issue 都已有 PR） | DCO 已签；commit 已含 `Co-authored-by: Claude` 披露行 |
| mlflow/mlflow | `search_traces` 的 `span.attributes.<k> =` 永不匹配、`!=` 全匹配、`IN` 抛内部异常 | +43 行 + 2 个测试 | 无 | DCO 已签；PR 要标 `rn/bug-fix` |
| huggingface/peft | `delete_adapter` 在多 adapter 目标不同模块时把活动 adapter 清空，随后 forward `KeyError` | 1 行 + 1 个测试 | 无（同类 bug 在 PeftMixedModel 已被 #3515 修过） | **必须先开 issue，等 `@peft-triage approved` 后才能开 PR** |
| sgl-project/sglang | 流式 tool-call 解析丢掉 `bot_token` 之前的正常文本；Hermes 解析器在同一 delta 内丢整个 tool call | 2 个源文件 +14/-6 + 4 个测试 | 无（#31915 等是邻近问题） | pre-commit 已过 |

Qdrant / Milvus 未做：容器磁盘不够编译 Rust/Go 全量依赖，替换成了 peft。

## 你要做的事（按顺序）

1. **在 GitHub 上 fork 这 7 个仓库**（会话权限只绑定 HS1CMU/a，无法替你 fork）。
2. 本地应用补丁（以 litellm 为例）：
   ```bash
   git clone https://github.com/HS1CMU/litellm && cd litellm
   git checkout -b fix/otel-zero-valued-request-params
   git am ../a/oss-week1/litellm.patch
   ```
3. **自己跑一遍**该仓库 submission 文件里列出的 lint / 测试命令，逐行看懂 diff。这些仓库都要求提交者本人能解释每一行。
4. 按 submission 文件里的 issue 草稿开 issue。peft 和 diffusers 必须等维护者回应；其余可以在 issue 里说一句 "I have a fix ready" 后直接开 PR。
5. 拿到 issue 号后替换 PR 草稿里的 `Fixes #N` 占位符，push 分支，开 PR。
6. 每个仓库同时只保持 1 个 open PR，直到合并。

## 需要你自己判断的点

- vLLM：渲染层那个用 MagicMock 的测试可能被 reviewer 要求删掉，只留两个转换层测试。
- MLflow：SQLite 下 `%` / `_` 通配符未转义的限制已写进 PR 描述，维护者可能要求补 `ESCAPE`。
- LiteLLM：PR 模板要求真实 proxy 的 curl 证明，这里只有 SDK 级 mock 证明，已写在 Caveats。
- 所有 AI 披露行的措辞按各仓库要求写好了；scikit-learn 那种禁止披露格式的仓库这次没涉及。

## 环境限制说明

容器无 GPU，`download.pytorch.org`、`huggingface.co`、`pypi.nvidia.com` 被代理拦截，所以：依赖 Hub 下载的既有测试在 main 上同样失败（各 submission 文件已逐个列出）；torch 用的是 PyPI 的 CUDA wheel 仅作 import。所有新增测试都在改动前失败、改动后通过，且已在无改动的 main 上做过对照。
