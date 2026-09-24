# AI / ML 开源贡献指南（2026-09 版）

> 目标：第一周对 7 个仓库各提 1 个 bug + 1 个 PR，合并后再扩展。
> 本文按 AI/ML 流水线分组列出仓库，给出每个仓库的贡献规范、活跃度判断、提 PR 的标准流程，以及市面上的辅助工具。
> 标注 **[已核实]** 的规范来自 2026-09-24 当天抓取的 CONTRIBUTING 文件；未标注的来自公开资料与经验，动手前请再看一眼该仓库的 CONTRIBUTING。

---

## 0. 先说结论：第一周选哪 7 个

综合"合并快、对新人友好、湾区大厂在用、AI 写 PR 不会被直接关掉"四个条件，推荐下面这 7 个（按优先级）：

| # | 仓库 | 为什么 | 提 PR 前必做 |
|---|------|--------|-------------|
| 1 | `vllm-project/vllm` | 推理引擎事实标准，PR 吞吐极高，有 Onboarding Tasks 看板 | `git commit -s`（DCO），pre-commit，PR 标题 `[Bugfix][Core] ...` |
| 2 | `BerriAI/litellm` | 迭代极快，几乎天天合并外部 PR，bug 多且容易复现 | 签 CLA，至少 1 个 mock 测试，`make lint` |
| 3 | `run-llama/llama_index` | 测试覆盖率 <50%，容易找到真 bug；`uv` 工具链简单 | `uv run make lint`，只改 core 或主流 integration |
| 4 | `mlflow/mlflow` | 维护者主动 triage issue，good first issue 常年有 | DCO 签名，先开 issue 等回复 |
| 5 | `sgl-project/sglang` | 与 vLLM 同赛道，人手更少，PR 更容易被看到 | pre-commit，跑对应单测 |
| 6 | `huggingface/diffusers` 或 `huggingface/peft` | HF 系里比 transformers 审核压力小，规范一致 | `make style && make quality`，先在 issue 里认领 |
| 7 | `milvus-io/milvus` 或 `qdrant/qdrant` | 向量库赛道，Go/Rust 竞争者少，好 PR 很快合并 | Milvus: DCO；Qdrant: PR 打到 `dev` 分支 |

**先不要碰的**：`huggingface/transformers`（明确要求首次贡献者不用 agent，疑似 agent 的 PR 直接关）、`langchain-ai/langchain`（必须先有维护者批准的 issue）、`pytorch/pytorch`（必须有 `actionable` 标签的 issue，CLA + 巨型 CI）。这三个等你有 3-5 个合并记录后再去。

---

## 1. 仓库全景：按 AI/ML 流水线分组

### 1.1 数据准备 / 文档解析（RAG 的输入端）

| 仓库 | 语言 | 用途 | 大厂使用 | 活跃/可贡献 |
|------|------|------|----------|-------------|
| `huggingface/datasets` | Py | 数据集加载 | 全行业 | 活跃，HF 规范 |
| `Unstructured-IO/unstructured` | Py | PDF/Office 解析 | RAG 产品普遍 | 活跃，要改 CHANGELOG + 版本号 |
| `docling-project/docling` | Py | IBM 文档解析 | 企业 RAG | 很活跃，DCO |
| `huggingface/tokenizers` | Rust/Py | 分词 | 全行业 | 稳定，改动少 |

### 1.2 模型训练 / 微调

| 仓库 | 语言 | 用途 | 大厂使用 | 活跃/可贡献 |
|------|------|------|----------|-------------|
| `pytorch/pytorch` | C++/Py | 训练框架 | Meta/OpenAI/Anthropic/DeepSeek 全部 | 极活跃；CLA；需 `actionable` issue |
| `huggingface/transformers` | Py | 模型库 | 全行业 | 极活跃；对 agent PR 最严 |
| `huggingface/peft` | Py | LoRA 等 | 全行业 | 活跃，友好 |
| `huggingface/trl` | Py | RLHF/GRPO | OpenAI/DeepSeek 路线相关 | 活跃 |
| `huggingface/accelerate` | Py | 分布式封装 | 全行业 | 活跃 |
| `deepspeedai/DeepSpeed` | Py/CUDA | 分布式训练 | 微软系、很多大模型团队 | 活跃，Microsoft CLA |
| `NVIDIA/Megatron-LM` | Py | 大规模训练 | DeepSeek/NVIDIA 生态 | 活跃，DCO |
| `Lightning-AI/pytorch-lightning` | Py | 训练封装 | 中小团队多 | 活跃 |
| `unslothai/unsloth` | Py | 高效微调 | 社区 | 很活跃，小团队，PR 审核快 |
| `axolotl-ai-cloud/axolotl` | Py | 微调配置化 | 社区 | 活跃 |
| `jax-ml/jax` | Py | Google 训练框架 | Google/Anthropic | 活跃，Google CLA |
| `keras-team/keras` | Py | 高层 API | Google | 活跃，Google CLA |
| `Dao-AILab/flash-attention` | CUDA | 注意力核 | 全行业 | 核心成员少，外部 PR 合并慢 |
| `triton-lang/triton` | Py/C++ | GPU DSL | OpenAI/Meta | 活跃，门槛高 |

### 1.3 推理 / 服务

| 仓库 | 语言 | 用途 | 大厂使用 | 活跃/可贡献 |
|------|------|------|----------|-------------|
| `vllm-project/vllm` | Py/CUDA | LLM 推理 | 几乎所有 LLM 公司 | 极活跃；DCO；6 个 open PR 上限 |
| `sgl-project/sglang` | Py/CUDA | LLM 推理 | xAI、DeepSeek 相关 | 极活跃 |
| `ggml-org/llama.cpp` | C++ | 本地推理 | 端侧 | 极活跃；新人限 1 个 open PR，不接受琐碎修改 |
| `ollama/ollama` | Go | 本地推理封装 | 开发者 | 活跃，官方合并选择性强 |
| `huggingface/text-generation-inference` | Rust/Py | 推理服务 | HF | 活跃 |
| `onnx/onnx`, `microsoft/onnxruntime` | C++ | 推理格式/运行时 | 微软、端侧 | 活跃，DCO/CLA |
| `openvinotoolkit/openvino` | C++ | Intel 推理 | Intel | 活跃，好 first issue 多 |

### 1.4 向量数据库 / 检索

| 仓库 | 语言 | 大厂使用 | 活跃/可贡献 |
|------|------|----------|-------------|
| `qdrant/qdrant` | Rust | 很多 RAG 产品 | 活跃；**默认分支是 `dev`**，PR 打到 `dev` |
| `milvus-io/milvus` | Go/C++ | 企业 | 活跃；DCO；`/lgtm` `/approve` 机器人合并 **[已核实]** |
| `chroma-core/chroma` | Py/Rust | 开发者原型 | 活跃 |
| `weaviate/weaviate` | Go | 企业 | 活跃 |
| `facebookresearch/faiss` | C++ | Meta 及全行业 | 稳定，Meta CLA，外部 PR 少 |
| `lancedb/lancedb` | Rust/Py | 多模态 | 活跃，小团队友好 |
| `pgvector/pgvector` | C | Postgres 用户 | 单人维护，几乎不收 PR |

### 1.5 编排 / Agent 框架

| 仓库 | 语言 | 大厂使用 | 活跃/可贡献 |
|------|------|----------|-------------|
| `langchain-ai/langchain` | Py | 广泛 | 极活跃；**必须先有维护者批准的 issue** **[已核实]**；`langchain-community` 已归档，新集成做独立包 |
| `langchain-ai/langgraph` | Py | 广泛 | 活跃；同 LangChain 规则 |
| `run-llama/llama_index` | Py | RAG 产品 | 活跃；新集成不再收进 monorepo **[已核实]** |
| `crewAIInc/crewAI` | Py | 社区 | 活跃 |
| `microsoft/autogen` | Py | 微软 | 已转向 `microsoft/agent-framework`，autogen 维护模式 |
| `openai/openai-agents-python` | Py | OpenAI | 活跃，OpenAI 员工审核 |
| `google/adk-python` | Py | Google | 活跃，Google CLA |
| `pydantic/pydantic-ai` | Py | 增长快 | 活跃；100% 覆盖率要求，`make` 工具链 |
| `huggingface/smolagents` | Py | HF | 活跃 |
| `dspy-ai/dspy` | Py | 研究/产品 | 活跃 |
| `modelcontextprotocol/python-sdk`, `modelcontextprotocol/servers` | Py/TS | Anthropic 主导 | 活跃；servers 仓库接 community server 但审核慢 |
| `vercel/ai` | TS | 前端 | 活跃；需要 changeset |
| `browser-use/browser-use` | Py | Agent | 活跃 |

### 1.6 网关 / 可观测 / 评估

| 仓库 | 大厂使用 | 活跃/可贡献 |
|------|----------|-------------|
| `BerriAI/litellm` | 很多公司做统一 LLM 网关 | 极活跃；CLA；每个 PR 必须带测试 **[已核实]** |
| `langfuse/langfuse` | 可观测 | 活跃 |
| `Arize-ai/phoenix` | 可观测/评估 | 活跃 |
| `mlflow/mlflow` | 实验管理，Databricks 主导 | 活跃；DCO **[已核实]** |
| `EleutherAI/lm-evaluation-harness` | 评测标准 | 活跃，加任务类 PR 易合并 |
| `openai/evals` | OpenAI | 半维护 |
| `explodinggradients/ragas` | RAG 评估 | 活跃 |
| `confident-ai/deepeval` | 评估 | 活跃 |
| `ray-project/ray` | 分布式，Anyscale/OpenAI 用 | 活跃；PR 标题 `[core]`，改完要主动 ping reviewer **[已核实]** |

### 1.7 RAG 全栈产品

| 仓库 | 活跃/可贡献 |
|------|-------------|
| `infiniflow/ragflow` | 活跃，中文团队，issue 多 |
| `deepset-ai/haystack` | 活跃；需要用 `reno` 写 release note |
| `Cinnamon/kotaemon` | 一般 |

### 1.8 SDK（注意：多数是生成代码）

| 仓库 | 说明 |
|------|------|
| `openai/openai-python`, `anthropics/anthropic-sdk-python` | 由 Stainless 自动生成，**不接受改生成代码的 PR**，只能提 issue 或改 README/examples |
| `anthropics/claude-code` | 源码不开放，只接 issue |
| `anthropics/skills`, `anthropics/courses` | 接 PR，但门槛在于内容质量 |

### 1.9 DeepSeek / OpenAI / Anthropic 开源了什么

- **DeepSeek**：`DeepSeek-V3`、`FlashMLA`、`DeepEP`、`DeepGEMM`、`3FS`、`DualPipe`。属于研究发布，外部 PR 合并很少，主要是 issue。他们内部依赖 PyTorch、Megatron、vLLM/SGLang（自家 SGLang 支持很积极）。
- **OpenAI**：`openai-python`、`openai-agents-python`、`whisper`、`evals`、`tiktoken`、`gpt-oss`。内部大量用 PyTorch、Triton、Ray。
- **Anthropic**：`anthropic-sdk-*`、`claude-code`（闭源）、`skills`、`courses`、MCP 协议全家桶。内部用 JAX/PyTorch。
- **湾区大厂通用栈**：PyTorch + transformers/peft/trl + vLLM/SGLang + Ray + MLflow/W&B + 向量库（Milvus/Qdrant/pgvector）+ LangGraph/自研编排 + LiteLLM/自研网关。

---

## 2. 各仓库的具体规范

### 2.1 HuggingFace 系（transformers / diffusers / peft / trl / datasets / accelerate）**[transformers 已核实]**

- 目标分支 `main`，squash 合并。
- **不要一次提太多**：明确写了"如果能 1 行修好就 1 行"，避免小的 typo/style "busywork" PR，机械性清理要合并成一个系统性的 PR。
- 首次贡献者**不要用 code agent** 开 issue 或 PR，疑似 agent 写的 PR 会不经审查直接关，屡犯封号（HF 已经对个别账号做过 PR creation block）。
- 如果用了 AI 辅助：逐行审查、端到端跑通、在 PR 里披露、先在 issue 里协调。
- 命令：`make fix-repo`（提 PR 前）、`make typing`、`utils/tests_fetcher.py` 选测试。其他 HF 仓库是 `make style && make quality && pytest tests/xxx`。
- 新模型必须先开 issue；v5 之后很多模型改成 Hub-first，不需要上游 PR。
- 标签：`Good First Issue`、`Good Second Issue`；`https://github.com/huggingface/transformers/contribute`。
- 无 CLA。

### 2.2 LangChain / LangGraph **[已核实]**

- 分支 `master`（langchain）/ `main`（langgraph）。monorepo，`uv` + `make lint format test`，在对应 `libs/xxx` 目录下跑。
- **每个 PR 必须链接一个维护者已批准方案的 issue 或 discussion**，否则直接关。
- 原则："如果写 PR 的力气比 review 的力气还小，别提"；"大规模自动化贡献等同于对人力的 DoS 攻击"。2026-09-20 文档又加了一条：禁止批量代码扫描生成的 PR/issue。
- `langchain-community` 已于 2026-06 归档。新集成做成独立 `langchain-<x>` 包自己维护，再在 docs 仓库登记。
- 最低摩擦入口是 `langchain-ai/docs`。

### 2.3 vLLM **[已核实]**

- 分支 `main`。**DCO**：每个 commit `git commit -s`。
- pre-commit 强制（ruff、mypy 只查你改的文件），`pre-commit run -a`。
- PR 标题：`[Bugfix][Scheduler] 描述`，type 标签 Bugfix/Feature/Perf/Refactor/CI/Test/Doc，scope 标签 Model/Frontend/Core/Kernel 等。
- 无写权限的人最多 **6 个 open PR**。
- AI 政策：不接受"纯 agent" PR；避免 busywork PR（单个 typo、孤立 style）；在 PR 描述里披露；commit 加 `Co-authored-by: Claude <noreply@anthropic.com>` 之后再加 `Signed-off-by`。
- 流程：reviewer 批准或加 `ready` 标签后 `/ci run`；分支必须与 main 零落后。reviewer 每 2-3 天更新，7 天没动静你可以 ping。
- 找任务：`good first issue`、Onboarding Tasks 看板 `https://github.com/orgs/vllm-project/projects/6`。

### 2.4 PyTorch **[已核实]**

- 分支 `main`。**Meta CLA** 必签。
- 新贡献者**不要提没有 `actionable` 标签 issue 的 PR**。先开 issue，等维护者打标签。
- lint：`spin lint` / `spin quicklint`（lintrunner）。
- 合并：批准后评论 `@pytorchmergebot merge`。没人 assign 的话 triage squad 几个工作日内会分配；4 个工作日没动静可以 ping。
- AI 政策（`AI_POLICY.md`）：披露且用 code block 隔离 AI 内容；issue 里不要放 AI 生成的解决方案说明；全自动贡献直接拒。
- 好入口：pytorch-bot 自动开的 `DISABLED test_xxx` 不稳定测试 issue（`https://hud.pytorch.org/disabled`），修好并重新启用是被认可的贡献。周五有 Dev Infra Office Hours。

### 2.5 LlamaIndex **[已核实]**

- 分支 `main`。monorepo：`llama-index-core` + `llama-index-integrations/`。
- `uv sync && uv run pre-commit install`，`uv run make lint`，`uv run -- pytest`。
- 测试覆盖 <50%，改动必须带测试，外部系统要 mock。
- **不再接受新集成**进 monorepo，新集成自己发 PyPI 包。
- AI：可用于重构、样板、测试、文档；不要用于复杂逻辑、架构、大改、安全代码；必须披露。

### 2.6 LiteLLM **[已核实]**

- 目标分支用 `python3 scripts/default_branch.py --branch` 查（通常是 `main`）。
- 签 CLA。**至少 1 个测试是硬性要求**，只能 mock，测试文件路径镜像源码路径。
- `make lint`（ruff + basedpyright + 循环导入检查）、`make format`、`uv run pytest tests/test_litellm/...`。
- Conventional Commits + Conventional Branches；一个 PR 只解决一个问题。
- 用 AI 工具要读 `AGENTS.md`，提交前 `make format`。

### 2.7 llama.cpp **[已核实]**

- 分支 `master`。feature 必须先有 issue；bug fix 必须附可复现 issue + 回归测试。
- **新贡献者最多 1 个 open PR，不接受琐碎修改**。
- AI：必须披露；人工审核（约 200-400 行/小时）；禁止用 AI 写 PR 描述和讨论；未披露永久封号；被问到时要能解释每一行。
- squash 提交格式 `<module> : <title> (#issue)`；C++ 风格 snake_case、4 空格、避免模板花活。
- ggml 算子改动要跑 `test-backend-ops`。

### 2.8 Milvus **[已核实]**

- 分支 `master`。**DCO** `git commit -s`。
- 大改先开 issue；feature 要在 `docs/design-docs/` 写 MEP 设计文档。
- Go：`make static-check && make fmt`；C++ Google 风格；覆盖率 ≥90%。
- 机器人流程：reviewer `/lgtm`，approver `/approve`，CI 过后 `sre-ci-robot` 自动合并。

### 2.9 MLflow **[已核实]**

- 分支 `master`。**DCO** 签名。
- 先开 issue 描述贡献，committer 会 triage；大改会打 `needs design`。
- `ruff format && ruff check`，或 `pre-commit install --install-hooks`；测试放 `tests/`，`pytest tests --quiet`。

### 2.10 Ray **[已核实部分]**

- 分支 `master`。PR 标题 `[core] / [serve] / [data] ...`。
- `pre-commit` 或 `scripts/format.sh`。
- 外部贡献者：改完评论后**主动 ping assignee**，否则会被遗忘。

### 2.11 Qdrant

- **默认分支是 `dev`**，PR 打到 `dev`，`master` 只用于发布。Rust：`cargo fmt`、`cargo clippy`、`cargo test`。无 CLA。

### 2.12 其他快速备忘

| 仓库 | 分支 | 签名 | 特殊要求 |
|------|------|------|----------|
| DeepSpeed | master | Microsoft CLA | pre-commit，`unit/` 测试 |
| Megatron-LM | main | DCO | 主要看 `megatron/core` |
| JAX / Keras / ADK | main / master | Google CLA | Keras 改动要同时考虑 3 个 backend |
| ONNX | main | DCO | 改 proto 要重新生成 |
| scikit-learn | main | 无 | 自动化贡献政策：披露 + 人工验证，**不允许 AI 作为 Co-authored-by** |
| Haystack | main | 无 | `hatch` + `reno new` 写 release note |
| vercel/ai | main | 无 | `pnpm changeset` 必须 |
| Unstructured | main | 无 | 改 `CHANGELOG.md` 并 bump `__version__` |
| Docling | main | DCO | Conventional Commits |
| pydantic-ai | main | 无 | `make` 全套，覆盖率要求 100% |
| MCP python-sdk | main | 无 | `uv`，pyright strict |

---

## 3. 怎么提一个能合并的 PR

### 3.1 标准流程（"先 issue 后 PR"）

1. **选仓库**：确认它 30 天内有外部 PR 被合并（看 Pull requests → closed，过滤 `is:merged`），并读一遍 CONTRIBUTING、AI 政策、PR 模板。
2. **找 bug**（见 3.2）。
3. **本地复现**：写一个 <50 行、不依赖外部数据的最小可复现例子（MRE），记录 OS/Python/torch/CUDA 版本，完整 traceback。
4. **搜重复**：`is:issue <关键词>` 和 `is:pr <关键词>`，避免撞车；有已开的 PR 就去那里评论而不是另开。
5. **开 issue**：用 bug 模板。写"预期 vs 实际 + MRE + 环境 + 你定位到的根因和建议修法"。PyTorch 除外：issue 里不要写 AI 生成的方案说明。
6. **等确认**：LangChain/PyTorch 必须等维护者批准或打 `actionable`；vLLM/LiteLLM/LlamaIndex/MLflow 可以在 issue 里说一句"我来修"然后直接提 PR 引用 issue。
7. **写 PR**：
   - fork → 从默认分支切 `fix/<issue号>-<简述>`。
   - 只改必要行；带回归测试；跑仓库的 lint/format/测试命令。
   - 需要签名的用 `git commit -s`；需要 CLA 的在 bot 提示后点签。
   - 标题按仓库约定（vLLM `[Bugfix][X]`、Ray `[core]`、LiteLLM `fix(scope): ...`）。
   - 描述：`Fixes #123`、改了什么、为什么、怎么测的；用了 AI 就按该仓库要求披露。
8. **跟进**：CI 红了立刻修；review 意见 24-48 小时内回复；一周没人看就礼貌 ping 一次；两周还没动静就先去做下一个。
9. **合并后**：不要连着开多个同类小 PR，尤其 HF / llama.cpp。

### 3.2 怎么自己找 bug（不是 typo）

- **新版本依赖破坏**：在干净环境装最新 torch/numpy/pydantic/httpx，跑仓库测试或 examples，看哪里报 `DeprecationWarning`/`AttributeError`。这类 bug 真实、可复现、修法明确。
- **CI 里的 flaky / DISABLED 测试**：PyTorch `hud.pytorch.org/disabled`；transformers 每天有 "integration failure triage" issue；其他仓库看 Actions 里最近失败的 job。
- **最近没人认领的 bug issue**：
  ```
  repo:vllm-project/vllm is:open is:issue label:bug no:assignee -linked:pr created:>2026-08-15
  ```
  挑评论少（`comments:<3`）、有 traceback 的，先复现，能复现就在 issue 里贴上根因分析，再提 PR。
- **类型检查**：对一个模块跑 `mypy --strict` / `pyright`，只修会影响运行时的真问题（比如 `Optional` 没判空），不要批量加注解。
- **边界条件**：空输入、`batch_size=1`、非 UTF-8、Windows 路径、`None` 默认参数被就地修改（mutable default）。这类在 integration/adapter 代码里非常多。
- **文档与代码不一致**：docstring 说的默认值和实际不同，函数签名变了 README 没更新。可以修，但**打包成一个 PR**，不要一个 typo 一个 PR。

### 3.3 GitHub 搜索语法速查

```
is:open is:issue label:"good first issue" no:assignee -linked:pr language:Python created:>2026-06-01
org:huggingface label:"Good First Issue" is:open
repo:BerriAI/litellm is:open label:bug comments:<3
```
CLI：`gh issue list -R owner/repo --label "good first issue" --search "no:assignee"`
每个仓库的自动页面：`https://github.com/<owner>/<repo>/contribute`

---

## 4. 第一周执行表

| 天 | 动作 |
|----|------|
| D1 | 装好 7 个仓库的开发环境（各仓库的 `uv sync` / `pip install -e ".[dev]"` / `make install-dev`），签 PyTorch/LiteLLM 类 CLA，配置 `git config commit.gpgsign` 与 `-s` 别名 |
| D2 | 每个仓库用 3.2 的方法找 1 个可复现 bug，本地复现，写 MRE |
| D3 | 开 7 个 issue（附 MRE + 根因） |
| D4-D5 | 对已被确认或不需要确认的仓库提 PR；每个 PR 带测试、过 lint |
| D6-D7 | 处理 review、修 CI；没被确认的 issue 礼貌 ping 一次 |

**节奏红线**：HF 系和 llama.cpp 同时只保持 1 个 open PR；vLLM 最多 6 个；LangChain 没有批准的 issue 不提。

---

## 5. 市面上的辅助工具 / Skills

### 5.1 找 issue

- goodfirstissue.dev（DeepSource 维护，有筛选门槛）、goodfirstissues.com、up-for-grabs.net、firsttimersonly.com、CodeTriage（每天邮件推一个 issue）、`github.com/topics/good-first-issue`。
- `gh extension install vilmibm/gh-contribute`；`pip install gh-contrib-scout`（按仓库健康度给 good first issue 打分）。

### 5.2 Agent skills（Claude Code / Cursor 等）

- `rokokol/contributing-skill`：`npx skills add -g rokokol/contributing-skill`。有 `repo`（拉 CONTRIBUTING/模板）、`dupes`（查重）、`draft`、`send` 子命令，推送前弹审批卡。
- `sunny0826/open-source-skills`：issue-triage、pr-description、open-source-analysis（仓库健康度）、release-notes 等 14 个。
- `ovachiever/droid-tings` 里的 `open-source-contributions`：提交前检查分支里的调试文件、IDE 配置、`validate-pr.sh`。
- `aidankinzett/claude-git-pr-skill`：做 PR review 用。
- 本会话自带的 `/code-review`、`/simplify`、`/security-review`：提 PR 前自查。
- 官方 `anthropics/skills` 目前**没有** OSS 贡献类 skill。
- 索引站：skills.sh、agent-skills.md、`vercel-labs/skills`。

### 5.3 自动修 issue 的 agent（谨慎）

- SWE-agent / mini-swe-agent、OpenHands（`openhands-resolver` 给 issue 打 `fix-me` 标签自动出 PR）、Aider。
- **注意**：用这些直接往别人仓库开 PR，正是 transformers、LangChain、llama.cpp 明确拒绝的。用它们在本地帮你定位和起草可以，提交前必须自己逐行看懂、跑通、按要求披露。

### 5.4 通用指南

- opensource.guide "How to Contribute"；StackOverflow 的 minimal reproducible example 指南。
- Conventional Commits 1.0.0。
- DCO vs CLA：DCO 是 `git commit -s` 加 `Signed-off-by` 行；CLA 是签协议（PyTorch/Meta、Google、Microsoft、LiteLLM 用 CLA；vLLM、Milvus、MLflow、Megatron、ONNX、Docling 用 DCO）。
- 各项目 AI 政策汇总：`melissawm/open-source-ai-contribution-policies`。

---

## 6. 你没问但必须知道的

1. **2026 年的大环境变了**：AI 生成的 PR 从 2025-09 的 400 万涨到 2026-03 的 1700 万+，GitHub 在 2026-06 上线了每用户 PR 上限、2026-08 上线了仓库级"限制外部 open PR 数"的开关。很多仓库对新账号的第一个 PR 极其敏感。**第一个 PR 的质量决定你在这个仓库以后的待遇**。
2. **不要评论"please assign me"**：HF、vLLM、PyTorch、scikit-learn 都不给外部人 assign。直接说"我在修，预计 X 天"或直接提 PR 引用 issue。
3. **AI 披露要用每个仓库自己的措辞**：vLLM 要求 `Co-authored-by: Claude`；scikit-learn、Kubernetes **禁止** AI 作为 Co-authored-by；PyTorch 要求 code block 隔离；llama.cpp 未披露直接封号。别用一套模板走天下。
4. **Draft PR 是安全的**：GitHub 的 PR 上限不算 draft，PyTorch 明确推荐 WIP 用 draft。
5. **合并时间预期**：vLLM 小 PR 1-2 周；PyTorch 首次 review 约 4 个工作日、合并看 CI 常要数周；transformers 修 bug 几天到几周；LangChain 只收预批准 issue，数周；scikit-learn 功能 PR 历史上以月计。"一周 7 个合并"不现实，**一周 7 个高质量 PR 进入 review 队列**是合理目标。
6. **一个 PR 一个问题，一个 issue 一个 PR**。发现同一根因影响多个文件可以一个 PR；发现两个不相关 bug 就两个 PR。
7. **贡献不只是代码**：修 flaky 测试、补 mock 测试、把 issue 复现并贴根因（PyTorch 把"复现 issue"列为新人推荐起点），这些在维护者眼里价值经常高于一个 typo PR，而且不会撞上 AI 政策。
8. **选仓库时看"外部 PR 合并率"而不是 star 数**：faiss、pgvector、flash-attention、DeepSeek 各仓库 star 很高但几乎不合外部 PR；unsloth、lancedb、sglang、litellm star 相对低但合并快。
9. **简历角度**：湾区面试官更认 vLLM / PyTorch / transformers / Ray 这种"公司内部真的在跑"的仓库里的**一个有测试的 bug fix**，而不是 10 个文档 PR。
10. **账号准备**：GitHub profile 写清楚真名和背景，开 2FA，commit email 与账号一致（CLA/DCO 校验会看），提前签好 Meta/Google/Microsoft 三家 CLA。

---

## 附：常用命令片段

```bash
# DCO 签名 + AI 披露（vLLM 风格）
git commit -s -m "[Bugfix][Core] Handle empty prompt in scheduler

Fixes #12345

Co-authored-by: Claude <noreply@anthropic.com>"

# 同步 fork 并 rebase 到最新
git fetch upstream && git rebase upstream/main

# 找未认领 bug
gh search issues --repo vllm-project/vllm --label bug --state open \
  --no-assignee --created ">2026-08-15" --sort created --limit 30
```
