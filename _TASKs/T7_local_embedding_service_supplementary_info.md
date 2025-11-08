可以，而且你的设想（文本与图片分别嵌入→Milvus 混合向量搜索→融合→Qwen3-Reranker 重排→交给 RAG-Anything/LLM 生成答案）在 Milvus 2.4+ 的“多向量混合搜索 + 可插拔重排器”能力下是标准玩法。下面给出 **T7：本地多模态 Embedding/Rerank 服务** 的可执行方案，按你指定的 3×1080Ti（Pascal，11GB）与 PyTorch + Transformers/Sentence-Transformers + FastAPI 技栈实现。

---

# T7：本地多模态 Embedding/Rerank 服务（PyTorch + Transformers + Sentence-Transformers + FastAPI）

## 0) 关键结论（先回答你最关心的点）

* **混合部署可行。**Milvus 从 2.4 起原生支持一个集合里放**多列向量**（最多 10 列），每列维度/度量可不同；混合搜索时可对多条 ANN 请求做**加权融合（WeightedRanker）**或 **RRF** 等，然后再接外部交叉编码器做“最终重排”。这正适合“文本向量 2560d + 图片向量 1536d”的场景。([Milvus][1])
* **模型选型与显存**（FP16，不做量化）：

  * Qwen3-Embedding-4B：最多 2560 维，Sentence-Transformers 直接可用；4B×2B≈8GB 权重 + 余量，单卡 1080Ti 可跑。([Hugging Face][2])
  * GME-Qwen2-VL-2B-Instruct（多模态嵌入）：1536 维，支持 `SentenceTransformer.encode({"image": ...})`；2B×2B≈4GB+。([Hugging Face][3])
  * Qwen3-Reranker-4B：官方给出 Transformers 交叉编码打分示例，适合作为最终重排器。([Hugging Face][4])
* **注意 Pascal 代际限制**：

  * 1080Ti（Pascal/SM61）**不支持 BF16**（仅 Ampere+ 原生），因此全链路用 FP16/FP32。([NVIDIA Developer Forums][5])
  * FlashAttention/FA2 主流实现要求 Ampere+；在 Pascal 上请使用 **eager/SDPA** 实现并关闭 FA2。([DeepWiki][6])
* **与 RAG-Anything 的关系**：其 “VLM-Enhanced Query/Answering” 用 **VLM 来解读图片**（caption/OCR/区域理解），与“前段检索是否做图片向量”是**两码事**。我们现在同时保留：

  * **A)** 图片→文本（caption/OCR）走文本嵌入/重排（兼容 RAG-Anything 既有逻辑）；
  * **B)** 图片→图片向量（GME）走 Milvus **混合向量搜索**，在文本召回不强时弥补召回盲点。([Milvus][7])

---

## 1) 最终部署方案（按你最新决定）

**GPU 映射（3×1080Ti）：**

* **GPU0**：`Qwen/Qwen3-Embedding-4B`（FP16，Sentence-Transformers 推理服务，左侧 padding，关闭 FA2）([Hugging Face][2])
* **GPU1**：`Alibaba-NLP/gme-Qwen2-VL-2B-Instruct`（FP16，Sentence-Transformers 推理服务，支持 image/text/fused embedding；输出 1536 维）([Hugging Face][3])
* **GPU2**：`Qwen/Qwen3-Reranker-4B`（Transformers 交叉编码器推理服务；按官方模板格式化输入对）([Hugging Face][4])

**Milvus（>=2.4，推荐 2.6）集合设计（named vectors）：**

* `text_vec`：`FLOAT_VECTOR(dim=2560)`（Qwen3-Embedding-4B）
* `image_vec`：`FLOAT_VECTOR(dim=1536)`（GME-Qwen2-VL-2B）
* 标量：`doc_id (VARCHAR)`, `chunk_id`, `uri`, `page`, `meta(JSON)`, `caption(Text)` 等
* 混合搜索：用 `AnnSearchRequest(text_vec)` 与 `AnnSearchRequest(image_vec)` **并发**；融合策略支持 **RRF** 或 **WeightedRanker(weights=[α, 1-α])**，可在 API 中暴露让用户选择/调权。([Milvus][8])

---

## 2) 端到端检索/生成链路

1. **摄取（MinerU 切分）**

* MinerU/你的切分组件把文档拆成 `text / image(/table/figure)`；
* 对 `text` 用 GPU0 的 `/embed` 得 2560d；对 `image` 用 GPU1 的 `/embed_image` 得 1536d；**可选**：同时生成/存储 `caption/OCR` 文本，供文本检索与重排使用（与 RAG-Anything 机制一致）。([Milvus][7])

2. **召回（Milvus 混合向量搜索）**

* 构造两条 ANN：

  * A：`text_vec` 用内积/IP 或余弦；
  * B：`image_vec` 用内积/IP（GME 默认 cosine 语义相容）。
* 用 **RRF**（简单稳健）或 **WeightedRanker(α)** 融合（对分数自动做归一化/压缩），取前 K（如 50）。([Milvus][1])

3. **最终重排（交叉编码器）**

* 把候选（其 `caption/文本` + 可选 `query` 指令）喂给 **Qwen3-Reranker-4B** 做 point-wise/二分类打分（官方示例是 yes/no 归一化取 “yes” 概率），取前 N（如 10）。([Hugging Face][4])
* **说明**：Milvus 也内置了 CrossEncoder 重排器（`pymilvus[model]` 的 `CrossEncoderRerankFunction`），但它主要面向 sbert 风格 cross-encoder；Qwen3-Reranker 的输入格式与计算逻辑不同，**更稳妥的做法**是用你自己的 `/rerank` 服务在应用层完成这一步。([Milvus][9])

4. **答案生成（RAG-Anything/LLM）**

* 把重排 Top-k 的**文本片段**与**图片 URI**一起交给 RAG-Anything；其 VLM-增强路径会在回答阶段拉取原图给 VLM 解读（与是否使用图片向量召回 **相互独立**）。([Milvus][7])

---

## 3) FastAPI 微服务（统一接口）

### 必选接口

* `POST /embed`：`{"texts": [...], "prompt": "query|passage|..."}` → `{"embeddings": [[...]], "dim": 2560}`（Qwen3-Embedding-4B）([Hugging Face][2])
* `POST /embed_image`：`{"images": ["http(s)://..."/base64/...], "prompt": "t2i|i2i|...（可选）"}` → `{"embeddings": [[...]], "dim": 1536}`（GME）

  * **GME x ST** 支持 `encode({"image": <path_or_bytes>, "prompt": ...})`；可与文本相同接口风格。([Hugging Face][3])
* `POST /rerank`：`{"query": "...", "docs": ["...", "..."], "instruction": "...(可选)"}` → `{"scores":[...], "indices":[...]}`（Qwen3-Reranker-4B 官方 yes/no 模板；左填充，max_len 8k）([Hugging Face][4])

### 可选接口

* `POST /search`：封装 Milvus **混合搜索**+（可选）**RRF/Weighted** 融合，返回候选及分数；参数里允许用户设定 `fusion: "rrf"|"weight", weights:[α,1-α]`。([Milvus][8])
* `GET /healthz`：健康检查。

> **高并发/高吞吐设计**
> 三个服务各自实现**动态批处理**（聚合窗口 5–20ms，设 `max_batch_size` + `max_tokens` 双阈值），异步队列消费；思想同 TEI 的 **token-based dynamic batching**。([DeepWiki][10])

---

## 4) Milvus：模式、索引与混合搜索代码片段

**建表要点**

* 两列向量：`text_vec(2560)` 与 `image_vec(1536)` 可共存于同一集合；每列各自建索引（如 `HNSW`/`IVF_*`），度量可分别选择。([Milvus][1])

**混合搜索（Python, PyMilvus 2.5+ 语义）**：

```python
from pymilvus import MilvusClient, AnnSearchRequest
from pymilvus.model.reranker import RRFRanker, WeightedRanker

client = MilvusClient(uri="http://localhost:19530")

# 两条 ANN：文本向量 + 图片向量
reqs = [
    AnnSearchRequest(
        data=[q_text_vec], anns_field="text_vec",
        param={"metric_type": "IP", "params": {"ef": 64}}, limit=50
    ),
    AnnSearchRequest(
        data=[q_image_vec], anns_field="image_vec",
        param={"metric_type": "IP", "params": {"ef": 64}}, limit=50
    )
]

# 选择融合策略：RRF 或 Weighted
ranker = RRFRanker(k=60)               # 或：
# ranker = WeightedRanker(weights=[alpha, 1-alpha], norm_score=True)

hits = client.hybrid_search(
    collection_name="mm_knowledge",
    reqs=reqs, ranker=ranker, limit=50,
    output_fields=["doc_id","chunk_id","uri","caption","meta"]
)
```

（`hybrid_search` 接口与 `AnnSearchRequest` 数据结构详见 Milvus 文档/示例。）([Milvus][8])

---

## 5) 性能与工程优化（面向 Pascal）

* **精度/注意力**：1080Ti 用 **FP16**；**禁用 FlashAttention/FA2**（Ampere+ 才支持），设 `attn_implementation="eager"`/SDPA。([DeepWiki][6])
* **动态批处理**：参考 TEI 的 token-based batching 思路，在 FastAPI 内用 `asyncio.Queue` 聚合请求；给每个工作器加 “最大 tokens / 最大 batch / 最大延迟”门限。([DeepWiki][10])
* **CUDA Graphs（可选）**：固定输入形状（pad 到固定 max_len）后捕获推理图，降低 kernel launch 开销（小批次收益更明显）。([Ian’s Blog][11])
* **多 GPU 策略**：本方案为**多服务多卡**（最简单且稳定）。Qwen3-4B 在 11GB 卡上**无须**再做 DataParallel；Reranker 单卡推理足够。PyTorch 文档亦建议训练用 DDP，推理侧尽量避免 DP 的主卡瓶颈。([PyTorch Documentation][12])

---

## 6) 与 RAG-Anything/LightRAG 的集成

* **切分**：保持 MinerU → `text/image/caption/...` 管线不变；caption/OCR 文本继续参与文本嵌入与重排。
* **图片返回与解读**：RAG-Anything 的 **VLM-Enhanced** 会在**回答阶段**把**原图**交给 VLM（如 DeepSeek-OCR 或 Qwen2-VL-Instruct）解读，这是对答案质量的增强，与“前段是否做图片向量召回”**独立**。([Milvus][7])
* **推荐设置**：

  * 检索：启用 Milvus 混合搜索（RRF 为默认，提供 Weighted α 可调）；
  * 重排：统一走 Qwen3-Reranker-4B 外部服务；
  * 回答：RAG-Anything 里开启 VLM-Enhanced（VLM 可设 DeepSeek-OCR/其它），是否启用与你的负载预算有关。

---

## 7) API 规范（摘要）

* `/embed`
  **Req**：`{"texts":[...], "prompt":"query|passage|...","truncate":8192}`
  **Resp**：`{"embeddings":[[...]], "dim":2560, "model":"Qwen3-Embedding-4B"}`
* `/embed_image`
  **Req**：`{"images":[{"uri":"..."}, ...], "prompt":"t2i|i2t|..."}`
  **Resp**：`{"embeddings":[[...]], "dim":1536, "model":"gme-Qwen2-VL-2B"}`
* `/rerank`
  **Req**：`{"query":"...", "docs":["..."], "instruction":"..."}`
  **Resp**：`{"scores":[...], "order":[...], "model":"Qwen3-Reranker-4B"}`

（GME 与 Qwen3 的 ST/Transformers 用法细节见各自模型卡。）([Hugging Face][2])

---

## 8) 配置管理

在`env`中进行配置：

  * `models.qwen3_embed.path`, `dtype: fp16`, `device: cuda:0`, `max_batch_tokens`, `max_wait_ms`
  * `models.gme_vl.path`, `device: cuda:1`
  * `models.qwen3_reranker.path`, `device: cuda:2`, `padding_side: left`
  * `milvus.uri`, `collection: mm_knowledge`, `index: {text_vec: HNSW, image_vec: HNSW}`
  * `fusion.default: rrf`, `weights: [0.7, 0.3]`
* `CUDA_VISIBLE_DEVICES=0`/`1`/`2` 分别启动三服务，或用 `device_map` 精确绑定。

---

## 9) 验证标准与基准

* **功能**：三接口返回维度/范数正确；Milvus 可完成混合搜索（RRF/Weighted 可切换），Qwen3-Reranker 得到可重复的 Top-k。([Milvus][8])
* **性能**：单机并发 100–500 RPS 下，p95 延迟与吞吐稳定；动态批处理生效（批量随负载上升）。参考 TEI 的 token-based batching 观测与对比。([DeepWiki][10])
* **质量**：以你的真实检索集合，分别比较

  * 仅文本→
  * 文本+caption→
  * 文本+图片（混合搜索）→
  * 混合 + 重排（Qwen3-4B）
    在 MRR@n / Recall@n 上的提升幅度。
* **回归**：升级 Milvus（2.4→2.6）与模型版本后，跑一致性测试。

---

## 10) 依赖清单（建议版本）

* `torch`（与 CUDA10/11 匹配；Pascal 建议 CUDA 11.8 + PyTorch 2.3/2.4）
* `transformers>=4.51.0`（Qwen3 系列要求；GME 远程代码提示 4.52 有兼容问题，建议 4.51.3）([Hugging Face][2])
* `sentence-transformers>=2.7.0`（同时支持图像输入的 encode 字典）([Hugging Face][3])
* `fastapi`, `uvicorn`, `pydantic`, `pymilvus>=2.5`, `numpy`, `opencv-python(headless)`
* （可选）`pymilvus[model]`（若尝试 Milvus 内置 CrossEncoder Reranker）([Milvus][9])

---

## 11) 潜在风险与缓解

* **FA2/BF16 不可用** → 统一 FP16 + Eager/SDPA；控制 max_len/批量，必要时启用 CUDA Graphs。([NVIDIA Developer Forums][5])
* **GME 版本兼容**：模型卡提示 `transformers>=4.52.0` 有问题，请钉死 **4.51.3** 或用 ST 调用路径。([Hugging Face][3])
* **Milvus 版本差异**：2.4 与 2.6 在 `hybrid_search`/`ranker` API 细节略有不同（ORM vs MilvusClient 语义），以部署版本文档为准。([Milvus][13])
* **Reranker 位置**：Milvus 内置 `CrossEncoderRerankFunction` 更适配 sbert 风格；Qwen3-Reranker 推荐自托管服务在**应用层重排**。([Milvus][9])

---

## 12) 你关心的两个“为什么”

1. **既然有 caption，为何还要图片向量？**

   * caption/ocr 把“看图”降维成文本，**鲁棒但易丢视觉细节**；GME 的图片向量能在“视觉形状/布局/图表样式”等场景里补盲。**混合搜索 + RRF/Weighted** = 召回更全面，再交给文本重排器统一打分。([Milvus][1])
2. **Milvus 能“重排”到什么程度？**

   * Milvus 的 **Weighted/RRF/Boost/Decay** 属于**结果融合/分数重标定**；真正的“语义重排”（交叉编码）建议用 **Qwen3-Reranker-4B** 在应用层完成（或尝试其内置 CrossEncoderRerankFunction 路径）。([Milvus][14])

---

### 附：极简启动建议

* 三个服务分别用 `CUDA_VISIBLE_DEVICES=0/1/2` 绑定；
* ST/Transformers 加载模型时：

  * Qwen3-Embedding-4B：`SentenceTransformer("Qwen/Qwen3-Embedding-4B", model_kwargs={"attn_implementation":"eager"})`（文档示例里推荐 FA2，但我们在 Pascal 上禁用）。([Hugging Face][2])
  * GME：`SentenceTransformer("Alibaba-NLP/gme-Qwen2-VL-2B-Instruct")`，用 `encode({"image":..., "prompt":...})`。([Hugging Face][3])
  * Reranker：按模型卡给出的包装（yes/no 模板，左填充），暴露 `/rerank`。([Hugging Face][4])

---

如果你愿意，我可以把上面内容整理成你仓库路径 **`_TASKs/T7_local_embedding_service.md`** 的“任务文档”格式（含 Phase 拆解、目录结构与测试用例清单）并附上 FastAPI + Milvus 的最小可运行样例。

[1]: https://milvus.io/docs/multi-vector-search.md?utm_source=chatgpt.com "Multi-Vector Hybrid Search | Milvus Documentation"
[2]: https://huggingface.co/Qwen/Qwen3-Embedding-4B "Qwen/Qwen3-Embedding-4B · Hugging Face"
[3]: https://huggingface.co/Alibaba-NLP/gme-Qwen2-VL-2B-Instruct "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct · Hugging Face"
[4]: https://huggingface.co/Qwen/Qwen3-Reranker-4B "Qwen/Qwen3-Reranker-4B · Hugging Face"
[5]: https://forums.developer.nvidia.com/t/quadro-rtx-6000-does-not-handle-bf16-please-make-an-update/312545?utm_source=chatgpt.com "Quadro RTX 6000 does not handle BF16? Please make an update?"
[6]: https://deepwiki.com/Dao-AILab/flash-attention?utm_source=chatgpt.com "Dao-AILab/flash-attention | DeepWiki"
[7]: https://milvus.io/docs/rrf-ranker.md?utm_source=chatgpt.com "RRF Ranker | Milvus Documentation"
[8]: https://milvus.io/api-reference/pymilvus/v2.5.x/MilvusClient/Vector/hybrid_search.md?utm_source=chatgpt.com "hybrid_search() - Milvus pymilvus sdk v2.5.x/MilvusClient/Vector"
[9]: https://milvus.io/docs/rerankers-cross-encoder.md "Cross Encoder | Milvus Documentation"
[10]: https://deepwiki.com/huggingface/text-embeddings-inference?utm_source=chatgpt.com "huggingface/text-embeddings-inference | DeepWiki"
[11]: https://ianbarber.blog/2023/06/28/cuda-graphs-in-pytorch/?utm_source=chatgpt.com "CUDA graphs in PyTorch – Ian’s Blog"
[12]: https://docs.pytorch.org/tutorials/intermediate/ddp_tutorial.html?utm_source=chatgpt.com "Getting Started with Distributed Data Parallel - PyTorch"
[13]: https://milvus.io/docs/v2.4.x/multi-vector-search.md?utm_source=chatgpt.com "Hybrid Search Milvus v2.4.x documentation"
[14]: https://milvus.io/docs/weighted-ranker.md "Weighted Ranker | Milvus Documentation"
