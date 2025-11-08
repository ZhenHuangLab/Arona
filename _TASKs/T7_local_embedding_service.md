<Task>
  <Header>
    <Title>TASK: 本地Embedding服务迁移与部署</Title>
    <Overview>
      <Purpose>
        <Label>Purpose:</Label>
        <Text>将在线embedding模型迁移到本地部署方案，使用3张NVIDIA 1080 Ti GPU，实现高性能、低成本的embedding和reranking服务。</Text>
      </Purpose>
      <Usage>
        <Label>How to use:</Label>
        <Text>按照Phase顺序执行：P1环境准备 → P2模型下载 → P3核心服务实现 → P4集成测试 → P5性能优化。每个Phase完成后更新Execution和Results。</Text>
      </Usage>
    </Overview>
  </Header>

  <Section id="meta">
    <Heading>0) META</Heading>
    <Meta>
      <TaskId>T7</TaskId>
      <Title>本地Embedding服务迁移与部署</Title>
      <RepoRoot>./</RepoRoot>
      <Branch>feature/T7-local-embedding-service</Branch>
      <Status>planning</Status>
      <Goal>在3张NVIDIA 1080 Ti GPU上部署本地embedding和reranking服务，替代在线API，实现零API成本、高性能、支持多模态的RAG系统</Goal>
      <NonGoals>
        <Item>不支持模型微调或训练</Item>
        <Item>不实现分布式推理（单机多卡即可）</Item>
        <Item>不创建独立的embedding微服务（集成到backend即可）</Item>
        <Item>不编写单元测试（除非用户明确要求）</Item>
        <Item>不创建额外文档（除本任务文档外）</Item>
      </NonGoals>
      <Dependencies>
        <Item>硬件：3× NVIDIA 1080 Ti (Pascal架构, 11GB VRAM each)</Item>
        <Item>Python 3.10+</Item>
        <Item>PyTorch 2.0+ (CUDA 11.8)</Item>
        <Item>transformers==4.51.3 (GME兼容性要求，避免4.52+)</Item>
        <Item>sentence-transformers >= 2.7.0</Item>
        <Item>accelerate >= 0.25.0</Item>
        <Item>safetensors >= 0.4.0</Item>
        <Item>pillow >= 10.0.0 (多模态支持)</Item>
        <Item>FastAPI (已有)</Item>
        <Item>现有backend架构（BaseEmbeddingProvider, BaseRerankerProvider, ModelFactory）</Item>
      </Dependencies>
      <Constraints>
        <Item>Pascal架构限制：不支持Flash Attention, 不支持BF16, 仅支持FP16</Item>
        <Item>显存限制：单卡11GB，采用4B模型单卡部署</Item>
        <Item>零技术债务：所有代码必须符合项目规范，职责清晰</Item>
        <Item>Fail-Fast原则：不添加fallback机制，问题必须暴露</Item>
        <Item>向后兼容：不破坏现有在线embedding功能</Item>
        <Item>性能要求：批处理吞吐量 >= 100 texts/sec (embedding), reranker延迟 < 500ms (10 docs)</Item>
        <Item>transformers版本锁定：必须使用4.51.3，避免4.52+导致GME不兼容</Item>
      </Constraints>
      <AcceptanceCriteria>
        <Criterion>AC1: 本地embedding服务可正常启动并响应请求（通过EMBEDDING_PROVIDER=local_gpu配置）</Criterion>
        <Criterion>AC2: 支持文本embedding（Qwen3-Embedding-4B）和reranking（Qwen3-Reranker-4B）</Criterion>
        <Criterion>AC3: （可选）支持多模态embedding（GME-Qwen2-VL-2B用于图片）</Criterion>
        <Criterion>AC4: GPU资源合理分配：GPU0=embedding, GPU1=reranker, GPU2=multimodal(可选)</Criterion>
        <Criterion>AC5: 实现动态批处理，批处理吞吐量 >= 100 texts/sec</Criterion>
        <Criterion>AC6: 所有代码符合项目规范，无硬编码，配置化管理</Criterion>
        <Criterion>AC7: 与现有backend无缝集成，通过ModelFactory创建provider</Criterion>
        <Criterion>AC8: 支持FP16精度，Pascal架构兼容（禁用Flash Attention）</Criterion>
        <Criterion>AC9: 实现Fail-Fast错误处理，无fallback机制</Criterion>
        <Criterion>AC10: 返回numpy.ndarray格式的embeddings（与现有provider一致）</Criterion>
        <Criterion>AC11: 支持async/await异步接口（与现有架构一致）</Criterion>
      </AcceptanceCriteria>
      <TestStrategy>
        - 功能测试：通过backend API测试embedding和reranking功能
        - 性能测试：测量批处理吞吐量和延迟
        - 显存测试：监控GPU显存使用，确保不OOM
        - 集成测试：端到端RAG查询测试
      </TestStrategy>
      <Rollback>
        - 设置EMBEDDING_PROVIDER=openai回退到在线API
        - 删除backend/providers/local_embedding.py
        - 从ModelFactory移除local provider注册
      </Rollback>
      <Owner>@claude</Owner>
    </Meta>
  </Section>

  <Section id="context">
    <Heading>1) CONTEXT</Heading>
    <List type="bullet">
      <Item>
        <Label>Current behavior:</Label>
        <Text>
          - 使用在线embedding API（OpenAI/Jina）
          - 通过backend/providers/openai.py和jina.py实现
          - 配置通过环境变量：EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME, EMBEDDING_API_KEY
          - 每次请求产生API成本
        </Text>
      </Item>
      <Item>
        <Label>Target behavior:</Label>
        <Text>
          - 本地部署Qwen3-Embedding和Qwen3-Reranker模型
          - 使用3张1080 Ti GPU，合理分配资源
          - 零API成本，数据隐私保护
          - 支持动态批处理，高吞吐量
          - 通过EMBEDDING_PROVIDER=local配置启用
        </Text>
      </Item>
      <Item>
        <Label>Interfaces touched:</Label>
        <Text>
          Backend (NEW):
          - backend/providers/local_embedding.py: LocalEmbeddingProvider, LocalRerankerProvider
          - backend/services/model_factory.py: 注册local provider
          - backend/config.py: 添加local provider配置支持
          
          Backend (MODIFIED):
          - backend/services/model_factory.py: create_embedding_provider()添加local分支
          
          Configuration (NEW):
          - env.backend.example: 添加local embedding配置示例
          - configs/local_embedding.yaml: 本地embedding配置示例
        </Text>
      </Item>
      <Item>
        <Label>Risk notes:</Label>
        <Text>
          - 显存不足风险：8B模型需16GB FP16，单卡11GB不够，需模型并行或降级到4B
          - Pascal架构限制：无Flash Attention，推理速度可能不如Ampere/Ada架构
          - 模型并行复杂度：sentence-transformers不原生支持tensor parallelism
          - 批处理实现复杂度：需自行实现动态batching逻辑
        </Text>
      </Item>
    </List>
  </Section>

  <Section id="technical_design">
    <Heading>2) 技术方案设计</Heading>
    
    <Subsection id="2.1">
      <Title>2.1 核心方案与GPU映射（已确定）</Title>
      <Text>
        **最终方案（单机多卡，单模单卡）**：
        - GPU 0: Qwen3-Embedding-4B（FP16，2560维，适配11GB显存）
        - GPU 1: Qwen3-Reranker-4B（FP16，交叉编码重排，适配11GB显存）
        - GPU 2: GME-Qwen2-VL-2B（FP16，1536维，可选）

        **核心优势**：
        - 所有模型单卡部署，架构简单，无跨卡通信开销
        - 无需实现复杂的模型并行（tensor parallelism）
        - 支持多模态（图片embedding），与Milvus混合向量搜索完美配合
        - 显存充足（每个模型都有3GB+余量），稳定性高
        - 符合sentence-transformers和transformers的标准使用模式

        **技术决策依据（摘要）**：
        - ST/Transformers 推理路径稳定、生态完善；本项目无需实现张量并行。
        - Qwen3-Embedding-4B 支持最高 2560 维向量；GME-Qwen2-VL-2B 输出 1536 维图片/多模态向量。
        - Pascal 架构不支持 BF16/FA2，采用 FP16 + SDPA/Eager；按 GPU 分配模型，避免跨卡通信与资源争用。
      </Text>
    </Subsection>
    
    <Subsection id="2.2">
      <Title>2.2 模型与维度</Title>
      <Text>
        - **Embedding**: Qwen/Qwen3-Embedding-4B（Hugging Face）
          - 参数量：4B；显存：≈8GB（FP16）；输出维度：最高 2560（建议 2560）
        
        - **Reranker**: Qwen/Qwen3-Reranker-4B（Hugging Face）
          - 参数量：4B；显存：≈8GB（FP16）；输入：query + document pairs；输出：relevance scores
        
        - **Multimodal（可选）**: Alibaba-NLP/gme-Qwen2-VL-2B-Instruct
          - 参数量：≈2B；显存：≈4GB（FP16）；输出维度：1536；支持：文本/图片/联合 embedding
      </Text>
    </Subsection>
    
    <Subsection id="2.3">
      <Title>2.3 架构设计</Title>
      <Text>
        **核心组件**：

        1. **LocalEmbeddingProvider** (backend/providers/local_embedding.py)
           - 继承BaseEmbeddingProvider
           - 接口要求：
             * async embed(texts: List[str], **kwargs) -> np.ndarray
             * @property embedding_dim() -> int
           - 初始化：
             * 使用SentenceTransformer加载Qwen3-Embedding-4B
             * 设置model_kwargs={"torch_dtype": "float16", "attn_implementation": "sdpa"}（或"eager" 以最大兼容）
             * 绑定到指定GPU（通过device参数）
           - 批处理：集成BatchProcessor实现动态批处理
           - 错误处理：Fail-Fast，不添加fallback

        2. **LocalRerankerProvider** (backend/providers/local_embedding.py)
           - 继承BaseRerankerProvider
           - 接口要求：
             * async rerank(query: str, documents: List[str], **kwargs) -> List[float]
           - 初始化：
             * 使用AutoModelForSequenceClassification加载Qwen3-Reranker-4B
             * 使用官方yes/no模板格式化输入
             * 设置padding_side="left"（Qwen3-Reranker要求）
             * FP16精度，绑定到指定GPU
           - 返回格式：List[float]，每个文档一个relevance score

        3. **BatchProcessor** (backend/providers/local_embedding.py)
           - 动态批处理队列（参考TEI设计）
           - 核心参数：
             * max_batch_tokens: 控制批次总token数（默认16384）
             * max_batch_size: 最大请求数（默认32）
             * max_wait_time: 最大等待时间（默认100ms）
           - 实现：
             * 使用asyncio.Queue收集请求
             * 后台任务定期处理batch（满足任一条件即触发）
             * 使用asyncio.Future返回结果给各请求

        4. **MultimodalEmbeddingProvider** (backend/providers/local_embedding.py, 可选)
           - 继承BaseEmbeddingProvider
           - 使用SentenceTransformer加载GME-Qwen2-VL-2B
           - 支持encode({"image": <path_or_bytes>, "prompt": ...})
           - 输出1536维向量

        5. **ModelFactory集成** (backend/services/model_factory.py)
           - create_embedding_provider()添加local provider检测逻辑
           - create_reranker()添加local provider支持
           - 配置模式：通过ModelConfig.extra_params传递 device/dtype/attn_implementation 等参数

        **数据流**：
        ```
        API Request → RAGService → ModelFactory → LocalEmbeddingProvider
                                                  ↓
                                            BatchProcessor.add_request()
                                                  ↓
                                            [Queue: 收集请求]
                                                  ↓
                                            BatchProcessor._process_batch()
                                                  ↓
                                            SentenceTransformer.encode(batch)
                                                  ↓
                                            [分发结果到各Future]
                                                  ↓
                                            Return embeddings to caller
        ```

        **关键设计决策（rationale）**：
        - 优先采用 Sentence-Transformers/Transformers 官方推理路径，降低自研复杂度与维护成本。
        - Pascal 代（GTX 1080 Ti）无 BF16/FlashAttention2 原生支持，统一 FP16 + SDPA/Eager，保证兼容性与稳定性。
        - Provider 内部实现 token-based 动态批处理（参数化阈值），对调用方透明。
        - 模型与 GPU 绑定的进程内加载，避免不必要的跨卡内存拷贝与竞争。
      </Text>
    </Subsection>
    
    <Subsection id="2.4">
      <Title>2.4 配置管理</Title>
      <Text>
        **环境变量**（.env.backend）：
        ```bash
        # ============================================================================
        # Local Embedding Configuration
        # ============================================================================
        EMBEDDING_PROVIDER=local_gpu  # 新增provider类型，区分local API和local GPU
        EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-4B
        EMBEDDING_MODEL_PATH=  # 可选，留空则从HF下载到缓存
        EMBEDDING_EMBEDDING_DIM=2560  # Qwen3-Embedding-4B最大维度

        # GPU和性能配置（通过extra_params传递）
        EMBEDDING_DEVICE=cuda:0
        EMBEDDING_DTYPE=float16  # Pascal支持FP16
        EMBEDDING_ATTN_IMPLEMENTATION=sdpa  # Pascal上推荐SDPA；必要时可降级eager
        EMBEDDING_MAX_BATCH_TOKENS=16384  # 参考TEI默认值
        EMBEDDING_MAX_BATCH_SIZE=32
        EMBEDDING_MAX_QUEUE_TIME=0.1  # 100ms

        # ============================================================================
        # Local Reranker Configuration
        # ============================================================================
        RERANKER_ENABLED=true
        RERANKER_PROVIDER=local_gpu  # 新增provider类型
        RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-4B
        RERANKER_MODEL_PATH=  # 可选

        # GPU和性能配置
        RERANKER_DEVICE=cuda:1
        RERANKER_DTYPE=float16
        RERANKER_PADDING_SIDE=left  # Qwen3-Reranker要求
        RERANKER_MAX_LENGTH=8192  # Qwen3-Reranker支持8k上下文
        RERANKER_BATCH_SIZE=16

        # ============================================================================
        # Optional: Multimodal Embedding (Phase P6)
        # ============================================================================
        MULTIMODAL_EMBEDDING_ENABLED=false
        MULTIMODAL_EMBEDDING_MODEL_NAME=Alibaba-NLP/gme-Qwen2-VL-2B-Instruct
        MULTIMODAL_EMBEDDING_DEVICE=cuda:2
        MULTIMODAL_EMBEDDING_DIM=1536
        ```

        **ModelConfig扩展**：
        需要在backend/config.py的ModelConfig类添加以下字段：
        - device: Optional[str] = None  # GPU设备（cuda:0/cuda:1/cuda:2）
        - model_path: Optional[str] = None  # 本地模型路径
        - dtype: str = "float16"  # 数据类型
        - attn_implementation: str = "sdpa"  # 注意力实现（或 "eager"）

        这些字段通过extra_params传递，或直接添加到ModelConfig dataclass。

        **ProviderType扩展**：
        添加新的provider类型：
        - LOCAL_GPU = "local_gpu"  # 本地GPU推理（区分于LOCAL=Ollama等API）
      </Text>
    </Subsection>
    
    <Subsection id="2.5">
      <Title>2.5 性能优化策略</Title>
      <Text>
        **1. 动态批处理（参考TEI设计）**：
           - **Token-based batching**：使用max_batch_tokens控制批次大小，而非仅max_batch_size
           - **双阈值触发**：满足以下任一条件即处理batch：
             * 累计tokens >= max_batch_tokens
             * 请求数 >= max_batch_size
             * 等待时间 >= max_wait_time
           - **实现细节**：
             * 使用asyncio.Queue收集请求
             * 后台任务（asyncio.create_task）持续监控队列
             * 每个请求携带asyncio.Future，用于返回结果
             * 批量推理后，按索引分发结果到各Future
           - **参数调优**：
             * max_batch_tokens=16384（TEI默认值，适合大多数场景）
             * max_batch_size=32（防止单个请求过大导致OOM）
             * max_wait_time=100ms（平衡吞吐量和延迟）

        **2. 模型优化（Pascal架构兼容）**：
           - **FP16精度**：
             * 使用model_kwargs={"torch_dtype": "float16"}或model.half()
             * Pascal原生支持FP16，性能提升明显
             * 不使用BF16（Pascal不支持）
           - **禁用Flash Attention**：
             * 设置attn_implementation="eager"或"sdpa"
             * Flash Attention需要Ampere+架构
             * SDPA（Scaled Dot-Product Attention）是PyTorch 2.0+的优化实现
           - **禁用梯度计算**：
             * 使用@torch.no_grad()装饰器或with torch.no_grad()上下文
             * 推理时不需要梯度，节省显存和计算
           - **模型编译（可选）**：
             * torch.compile()在Pascal上支持有限，谨慎使用
             * 如果启用，使用mode="reduce-overhead"

        **3. GPU内存管理**：
           - **预分配显存**：
             * 模型加载后立即进行一次warmup推理
             * 避免首次推理时的显存分配延迟
           - **避免显存碎片化**：
             * 使用固定的batch size（通过padding）
             * 定期调用torch.cuda.empty_cache()（但不要过于频繁）
           - **显存监控**：
             * 启动时记录模型加载后的显存占用
             * 推理时监控峰值显存，确保不超过11GB

        **4. 异步处理**：
           - **所有接口使用async/await**：
             * embed()和rerank()都是async方法
             * 批处理逻辑使用asyncio.Queue和asyncio.Future
           - **避免阻塞事件循环**：
             * 模型推理使用asyncio.to_thread()或run_in_executor()
             * 不在async函数中直接调用同步的模型推理
           - **并发控制**：
             * 使用asyncio.Semaphore限制并发请求数
             * 防止过多请求导致显存OOM

        **5. Sentence-Transformers特定优化**：
           - **推荐配置**（基于官方文档）：
             * 文本 < 500字符：考虑ONNX O4优化（但需测试Pascal兼容性）
             * 文本 >= 500字符：使用PyTorch FP16（本方案采用）
           - **Padding策略**：
             * Qwen3-Embedding使用左填充（left padding）
             * Qwen3-Reranker使用左填充（官方要求）
           - **Tokenizer优化**：
             * 设置padding=True, truncation=True, max_length=8192
             * 使用fast tokenizer（transformers默认）

        **6. 性能基准目标**：
           - 吞吐量：>= 100 texts/sec（embedding，batch_size=32）
           - 延迟：p95 < 200ms（embedding，单次请求）
           - Reranker延迟：< 500ms（10 documents）
           - GPU利用率：> 70%（批处理生效时）
           - 显存占用：< 11GB per GPU
      </Text>
    </Subsection>

    <Subsection id="2.6">
      <Title>2.6 Pascal架构（GTX 1080 Ti）适配指南</Title>
      <Text>
        **硬件规格**：
        - 架构：Pascal (SM 6.1)
        - CUDA Cores：3584
        - 显存：11GB GDDR5X
        - 显存带宽：484 GB/s
        - FP16性能：~11 TFLOPS（与FP32相同，无专用Tensor Cores）

        **关键限制与适配**：

        **1. 不支持BF16（Brain Float 16）**：
        - BF16需要Ampere架构（RTX 30系列）及以上
        - 解决方案：强制使用FP16（torch.float16）
        - 配置：model_kwargs={"torch_dtype": torch.float16}
        - 验证：启动时检查model.dtype，确保为torch.float16

        **2. 不支持Flash Attention / Flash Attention 2**：
        - Flash Attention需要Ampere+架构的Tensor Cores
        - 解决方案：使用eager attention或SDPA
        - 配置：
          * attn_implementation="eager"（最兼容，但较慢）
          * attn_implementation="sdpa"（PyTorch 2.0+优化，推荐）
        - 禁用方法：
          ```python
          model = AutoModel.from_pretrained(
              model_name,
              torch_dtype=torch.float16,
              attn_implementation="sdpa",  # 或"eager"
              trust_remote_code=True
          )
          ```

        **3. Tensor Cores限制**：
        - Pascal没有专用Tensor Cores（Volta引入）
        - FP16计算通过CUDA Cores执行，性能提升有限
        - 主要收益来自显存带宽节省（FP16占用减半）

        **4. CUDA版本要求**：
        - 推荐：CUDA 11.8（最后一个完整支持Pascal的版本）
        - 兼容：CUDA 12.x也支持，但优化较少
        - 验证：torch.cuda.get_device_capability() 应返回 (6, 1)

        **5. PyTorch版本要求**：
        - 推荐：PyTorch 2.0+（支持SDPA）
        - 最低：PyTorch 1.13+（支持FP16）
        - 验证：torch.backends.cuda.sdp_kernel() 检查SDPA可用性

        **6. Transformers版本要求**：
        - 推荐：transformers==4.51.3（GME兼容性）
        - 避免：transformers>=4.52（GME不兼容）
        - 原因：GME-Qwen2-VL-2B依赖特定版本的Qwen2VL实现

        **7. 性能优化建议**：
        - 使用SDPA而非eager attention（2-3x加速）
        - 启用torch.backends.cudnn.benchmark=True
        - 使用固定batch size减少内核启动开销
        - 避免频繁的CPU-GPU数据传输

        **8. 显存优化**：
        - FP16模型占用约为FP32的50%
        - Qwen3-Embedding-4B: ~8GB FP16（11GB显存足够）
        - Qwen3-Reranker-4B: ~8GB FP16（11GB显存足够）
        - GME-Qwen2-VL-2B: ~4GB FP16（11GB显存足够）
        - 预留3GB显存用于激活值和batch处理

        **9. 启动时验证清单**：
        ```python
        # 验证GPU架构
        assert torch.cuda.get_device_capability(device) == (6, 1), "需要Pascal架构"

        # 验证模型精度
        assert model.dtype == torch.float16, "必须使用FP16"

        # 验证注意力实现
        assert model.config.attn_implementation in ["eager", "sdpa"], "禁用Flash Attention"

        # 验证显存占用
        allocated = torch.cuda.memory_allocated(device) / 1024**3
        assert allocated < 8.5, f"模型显存占用过高: {allocated:.2f}GB"
        ```
      </Text>
    </Subsection>

    <Subsection id="2.7">
      <Title>2.7 Milvus 多向量与混合检索（可选，Phase P6）</Title>
      <Text>
        **目标**：
        支持 Milvus 2.4+ 的多向量集合（named vectors），以文本向量（2560d）与图片/多模态向量（1536d）联合召回；使用 RRF 或 WeightedRanker 进行融合，并在应用层用 Qwen3-Reranker-4B 做最终重排。

        **Collection 设计**：
        ```python
        # Collection Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="text_vec", dtype=DataType.FLOAT_VECTOR, dim=2560),   # Qwen3-Embedding
            FieldSchema(name="image_vec", dtype=DataType.FLOAT_VECTOR, dim=1536),  # GME/Qwen2-VL
            FieldSchema(name="image_path", dtype=DataType.VARCHAR, max_length=512),
        ]
        schema = CollectionSchema(fields, description="Multimodal RAG Collection")

        # 为两列向量分别创建索引
        collection.create_index("text_vec", {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}})
        collection.create_index("image_vec", {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}})
        ```

        **混合检索**（pymilvus MilvusClient/hybrid_search）：
        - 并发发起 `AnnSearchRequest("text_vec")` 与 `AnnSearchRequest("image_vec")`；
        - 选择融合策略：`RRF` 或 `WeightedRanker(weights=[α, 1-α])`；
        - 取 Top-K（如 50）后交由应用层 `/rerank` 最终重排。

        **实现要点**：
        - 在backend/services/rag_service.py添加multimodal_search()（或在现有流程中封装）；
        - 通过环境变量暴露融合策略与权重，默认 RRF；
        - 统一使用 Qwen3-Reranker-4B 进行最终重排，返回 Top-N（如 10）。

        **配置示例**：
        ```bash
        # Milvus Collection配置
        MILVUS_COLLECTION_NAME=arona_multimodal
        MILVUS_TEXT_EMBEDDING_FIELD=text_vec
        MILVUS_MULTIMODAL_EMBEDDING_FIELD=image_vec
        MILVUS_HYBRID_SEARCH_ENABLED=true
        MILVUS_HYBRID_FUSION=rrf   # 或 weighted
        MILVUS_HYBRID_WEIGHTS=0.7,0.3
        ```
      </Text>
    </Subsection>
  </Section>

  <Section id="high_level_plan">
    <Heading>3) HIGH-LEVEL PLAN</Heading>
    <Phases>
      <Phase>
        <Id>P1</Id>
        <Name>环境准备与依赖安装</Name>
        <Summary>安装PyTorch、transformers、sentence-transformers，验证GPU可用性</Summary>
      </Phase>
      <Phase>
        <Id>P2</Id>
        <Name>模型下载与验证</Name>
        <Summary>从HuggingFace下载Qwen3-Embedding-4B和Qwen3-Reranker-4B，验证加载和推理</Summary>
      </Phase>
      <Phase>
        <Id>P3</Id>
        <Name>核心Provider实现</Name>
        <Summary>实现LocalEmbeddingProvider和LocalRerankerProvider，集成到ModelFactory</Summary>
      </Phase>
      <Phase>
        <Id>P4</Id>
        <Name>动态批处理实现</Name>
        <Summary>实现BatchProcessor，优化吞吐量</Summary>
      </Phase>
      <Phase>
        <Id>P5</Id>
        <Name>集成测试与性能验证</Name>
        <Summary>端到端测试，性能基准测试，显存监控</Summary>
      </Phase>
      <Phase>
        <Id>P6</Id>
        <Name>（可选）多模态支持</Name>
        <Summary>集成GME-Qwen2-VL-2B，支持图片embedding</Summary>
      </Phase>
    </Phases>
  </Section>

  <Section id="phases">
    <Heading>4) PHASES</Heading>

    <!-- ========== Phase P1 ========== -->
    <PhaseHeading>Phase P1 — 环境准备与依赖安装</PhaseHeading>

    <Subsection id="4.1.1">
      <Title>4.1.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P1</PhaseId>
        <Intent>安装必要的Python包，验证GPU环境，确保Pascal架构兼容性，为Plan B实施做好准备</Intent>
        <Edits>
          <Edit>
            <Path>requirements-backend.txt</Path>
            <Operation>modify</Operation>
            <Rationale>添加本地embedding所需依赖，固定transformers版本以确保GME兼容性</Rationale>
            <Method>
              添加以下依赖：
              - torch==2.0.1 (CUDA 11.8版本，Pascal架构最佳支持)
              - transformers==4.51.3 (GME-Qwen2-VL-2B兼容性要求，避免4.52+)
              - sentence-transformers>=2.3.0
              - accelerate>=0.25.0 (用于模型加载优化)
              - safetensors>=0.4.0 (快速模型加载)
              - pillow>=10.0.0 (多模态图像处理)
            </Method>
          </Edit>
          <Edit>
            <Path>scripts/verify_pascal.py</Path>
            <Operation>add</Operation>
            <Rationale>创建Pascal架构兼容性验证脚本，确保FP16、SDPA等特性正常工作</Rationale>
            <Method>
              实现以下验证：
              1. 检查GPU架构为Pascal (6, 1)
              2. 验证FP16计算正常
              3. 检查SDPA可用性
              4. 确认BF16不可用（符合预期）
              5. 测试显存分配和释放
            </Method>
          </Edit>
          <Edit>
            <Path>.env.backend.example</Path>
            <Operation>modify</Operation>
            <Rationale>添加本地embedding配置示例</Rationale>
            <Method>
              添加以下配置段：
              # ============================================================================
              # Local Embedding Configuration (Plan B)
              # ============================================================================
              EMBEDDING_PROVIDER=local_gpu
              EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-4B
              EMBEDDING_EMBEDDING_DIM=2560
              EMBEDDING_DEVICE=cuda:0
              EMBEDDING_DTYPE=float16
              EMBEDDING_ATTN_IMPLEMENTATION=sdpa

              # ============================================================================
              # Local Reranker Configuration (Plan B)
              # ============================================================================
              RERANKER_ENABLED=true
              RERANKER_PROVIDER=local_gpu
              RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-4B
              RERANKER_DEVICE=cuda:1
              RERANKER_DTYPE=float16
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>
            # 安装PyTorch (CUDA 11.8版本)
            pip install torch==2.0.1 torchvision==0.15.2 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu118
          </Command>
          <Command>
            # 安装transformers和sentence-transformers
            pip install transformers==4.51.3 sentence-transformers>=2.3.0 accelerate safetensors pillow
          </Command>
          <Command>
            # 验证GPU环境
            nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv
          </Command>
          <Command>
            # 验证PyTorch CUDA
            python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.version.cuda}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}'); [print(f'GPU {i}: {torch.cuda.get_device_name(i)}, Compute Cap: {torch.cuda.get_device_capability(i)}') for i in range(torch.cuda.device_count())]"
          </Command>
          <Command>
            # 运行Pascal兼容性验证脚本
            python scripts/verify_pascal.py
          </Command>
          <Command>
            # 配置HuggingFace缓存
            export HF_HOME=/path/to/huggingface_cache
            mkdir -p $HF_HOME
          </Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>验证GPU架构</Name>
            <Expectation>3张GTX 1080 Ti，Compute Capability (6, 1)，显存11GB</Expectation>
          </Test>
          <Test>
            <Name>验证PyTorch CUDA可用</Name>
            <Expectation>torch.cuda.is_available() == True, device_count == 3, CUDA version 11.8</Expectation>
          </Test>
          <Test>
            <Name>验证transformers版本</Name>
            <Expectation>transformers.__version__ == "4.51.3"</Expectation>
          </Test>
          <Test>
            <Name>验证FP16支持</Name>
            <Expectation>FP16矩阵乘法正常，无错误</Expectation>
          </Test>
          <Test>
            <Name>验证SDPA可用性</Name>
            <Expectation>torch.nn.functional.scaled_dot_product_attention存在</Expectation>
          </Test>
          <Test>
            <Name>验证BF16不支持</Name>
            <Expectation>BF16操作失败或性能差（符合Pascal预期）</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>所有依赖安装成功，版本符合要求</Criterion>
          <Criterion>PyTorch可识别3张GTX 1080 Ti，Compute Capability (6, 1)</Criterion>
          <Criterion>transformers==4.51.3和sentence-transformers>=2.3.0可正常导入</Criterion>
          <Criterion>Pascal兼容性验证脚本全部通过</Criterion>
          <Criterion>HF_HOME配置正确，磁盘空间>=50GB</Criterion>
          <Criterion>.env.backend.example包含本地embedding配置示例</Criterion>
        </ExitCriteria>
        <Risks>
          <Risk>
            <Description>CUDA版本不兼容Pascal架构</Description>
            <Mitigation>使用CUDA 11.8（最后一个完整支持Pascal的版本），避免CUDA 12.x的潜在问题</Mitigation>
          </Risk>
          <Risk>
            <Description>transformers版本过高导致GME不兼容</Description>
            <Mitigation>固定transformers==4.51.3，在requirements中明确标注原因</Mitigation>
          </Risk>
          <Risk>
            <Description>FP16性能不如预期</Description>
            <Mitigation>Pascal的FP16性能与FP32相同（无Tensor Cores），主要收益来自显存节省，需设置合理预期</Mitigation>
          </Risk>
        </Risks>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.1.2">
      <Title>4.1.2 Execution</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.1.3">
      <Title>4.1.3 Diffs</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.1.4">
      <Title>4.1.4 Results</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <!-- ========== Phase P2 ========== -->
    <PhaseHeading>Phase P2 — 模型下载与验证</PhaseHeading>

    <Subsection id="4.2.1">
      <Title>4.2.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P2</PhaseId>
        <Intent>从HuggingFace下载Plan B所需的3个模型，验证FP16加载和推理，测量显存占用</Intent>
        <Edits>
          <Edit>
            <Path>scripts/download_local_models.py</Path>
            <Operation>add</Operation>
            <Rationale>创建模型下载和验证脚本，支持Plan B的3个模型，自动检测Pascal兼容性</Rationale>
            <Method>
              实现以下功能：
              1. 使用huggingface_hub.snapshot_download()下载模型到本地缓存
              2. 支持--model参数指定单个模型，或--all下载所有Plan B模型
              3. 验证模型加载（FP16精度，eager/sdpa attention）
              4. 测试简单推理（embedding: 单句，reranker: query+1 doc）
              5. 测量显存占用（torch.cuda.memory_allocated()）
              6. 生成验证报告（JSON格式）

              支持的模型：
              - Qwen/Qwen3-Embedding-4B
              - Qwen/Qwen3-Reranker-4B
              - Alibaba-NLP/gme-Qwen2-VL-2B-Instruct (可选)
            </Method>
          </Edit>
          <Edit>
            <Path>scripts/verify_model_loading.py</Path>
            <Operation>add</Operation>
            <Rationale>创建独立的模型加载验证脚本，测试不同配置（FP16 vs FP32, eager vs sdpa）</Rationale>
            <Method>
              实现以下测试：
              1. 加载Qwen3-Embedding-4B到cuda:0，测试FP16推理
              2. 加载Qwen3-Reranker-4B到cuda:1，测试FP16推理
              3. 验证attn_implementation配置生效
              4. 测量warmup前后的显存占用
              5. 测试batch推理（batch_size=1,8,16,32）
              6. 生成性能基准报告
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>
            # 下载Qwen3-Embedding-4B
            python scripts/download_local_models.py --model Qwen/Qwen3-Embedding-4B --device cuda:0
          </Command>
          <Command>
            # 下载Qwen3-Reranker-4B
            python scripts/download_local_models.py --model Qwen/Qwen3-Reranker-4B --device cuda:1
          </Command>
          <Command>
            # （可选）下载GME-Qwen2-VL-2B
            python scripts/download_local_models.py --model Alibaba-NLP/gme-Qwen2-VL-2B-Instruct --device cuda:2
          </Command>
          <Command>
            # 验证所有模型加载
            python scripts/verify_model_loading.py --all
          </Command>
          <Command>
            # 测试FP16 vs FP32性能对比
            python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B --compare-dtypes
          </Command>
          <Command>
            # 测试eager vs sdpa attention性能对比
            python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B --compare-attn
          </Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>模型下载成功</Name>
            <Expectation>模型文件存在于$HF_HOME/hub/，包含config.json, model.safetensors等</Expectation>
          </Test>
          <Test>
            <Name>Qwen3-Embedding-4B加载成功</Name>
            <Expectation>
              - 使用SentenceTransformer加载
              - model.dtype == torch.float16
              - 显存占用 ~8GB
              - 可以encode(["test"])并返回2560维向量
            </Expectation>
          </Test>
          <Test>
            <Name>Qwen3-Reranker-4B加载成功</Name>
            <Expectation>
              - 使用AutoModelForSequenceClassification加载
              - model.dtype == torch.float16
              - 显存占用 ~8GB
              - 可以对query+document进行rerank并返回score
            </Expectation>
          </Test>
          <Test>
            <Name>GME-Qwen2-VL-2B加载成功（可选）</Name>
            <Expectation>
              - 使用SentenceTransformer加载
              - model.dtype == torch.float16
              - 显存占用 ~4GB
              - 可以encode({"image": ..., "prompt": ...})并返回1536维向量
            </Expectation>
          </Test>
          <Test>
            <Name>attn_implementation配置生效</Name>
            <Expectation>
              - model.config.attn_implementation in ["eager", "sdpa"]
              - 不使用flash_attention_2
            </Expectation>
          </Test>
          <Test>
            <Name>显存占用符合预期</Name>
            <Expectation>
              - Qwen3-Embedding-4B: 7.5-8.5GB (FP16)
              - Qwen3-Reranker-4B: 7.5-8.5GB (FP16)
              - GME-Qwen2-VL-2B: 3.5-4.5GB (FP16)
              - 所有模型都在11GB显存限制内
            </Expectation>
          </Test>
          <Test>
            <Name>批处理推理正常</Name>
            <Expectation>
              - batch_size=32时，embedding推理成功，显存不OOM
              - batch_size=16时，reranker推理成功，显存不OOM
            </Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>Qwen3-Embedding-4B和Qwen3-Reranker-4B下载完成</Criterion>
          <Criterion>两个模型都可以FP16加载到各自GPU（cuda:0, cuda:1）</Criterion>
          <Criterion>简单推理测试通过（embedding: 单句，reranker: query+1 doc）</Criterion>
          <Criterion>显存占用在11GB以内（每个GPU）</Criterion>
          <Criterion>attn_implementation配置为eager或sdpa（非flash_attention_2）</Criterion>
          <Criterion>批处理推理测试通过（batch_size=32 for embedding, 16 for reranker）</Criterion>
          <Criterion>生成验证报告（JSON格式），包含显存占用、推理延迟等指标</Criterion>
        </ExitCriteria>
        <Risks>
          <Risk>
            <Description>模型下载失败（网络问题或HuggingFace访问受限）</Description>
            <Mitigation>配置HF_ENDPOINT镜像站，或提前手动下载模型文件</Mitigation>
          </Risk>
          <Risk>
            <Description>显存占用超过11GB</Description>
            <Mitigation>确保使用FP16而非FP32，检查是否有其他进程占用显存</Mitigation>
          </Risk>
          <Risk>
            <Description>transformers版本不兼容导致加载失败</Description>
            <Mitigation>确认transformers==4.51.3，查看模型官方文档的版本要求</Mitigation>
          </Risk>
        </Risks>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.2.2">
      <Title>4.2.2 Execution</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.2.3">
      <Title>4.2.3 Diffs</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.2.4">
      <Title>4.2.4 Results</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <!-- ========== Phase P3 ========== -->
    <PhaseHeading>Phase P3 — 核心Provider实现</PhaseHeading>

    <Subsection id="4.3.1">
      <Title>4.3.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P3</PhaseId>
        <Intent>实现LocalEmbeddingProvider和LocalRerankerProvider，集成到现有架构</Intent>
        <Edits>
          <Edit>
            <Path>backend/providers/local_embedding.py</Path>
            <Operation>add</Operation>
            <Rationale>实现本地embedding provider</Rationale>
            <Method>
              1. LocalEmbeddingProvider继承BaseEmbeddingProvider
              2. __init__: 加载模型到指定GPU，设置FP16
              3. async embed(texts): 调用模型推理，返回np.ndarray
              4. LocalRerankerProvider继承BaseRerankerProvider
              5. async rerank(query, documents): 返回relevance scores
            </Method>
          </Edit>
          <Edit>
            <Path>backend/services/model_factory.py</Path>
            <Operation>modify</Operation>
            <Rationale>注册local provider</Rationale>
            <Method>
              在create_embedding_provider()添加：
              if config.provider == ProviderType.LOCAL:
                  from backend.providers.local_embedding import LocalEmbeddingProvider
                  return LocalEmbeddingProvider(config)

              在create_reranker()添加类似逻辑
            </Method>
          </Edit>
          <Edit>
            <Path>backend/config.py</Path>
            <Operation>modify</Operation>
            <Rationale>添加LOCAL provider类型和配置字段</Rationale>
            <Method>
              1. ProviderType枚举添加LOCAL
              2. ModelConfig添加device字段（cuda:0/cuda:1/cuda:2）
              3. ModelConfig添加model_path字段（可选，本地路径）
              4. ModelConfig.from_env()支持读取EMBEDDING_DEVICE等
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>python -c "from backend.providers.local_embedding import LocalEmbeddingProvider; print('Import OK')"</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>Provider可实例化</Name>
            <Expectation>LocalEmbeddingProvider(config)成功</Expectation>
          </Test>
          <Test>
            <Name>Embedding推理成功</Name>
            <Expectation>embed(["test"])返回正确shape的ndarray</Expectation>
          </Test>
          <Test>
            <Name>Reranker推理成功</Name>
            <Expectation>rerank("query", ["doc1", "doc2"])返回scores</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>LocalEmbeddingProvider和LocalRerankerProvider实现完成</Criterion>
          <Criterion>ModelFactory可创建local provider</Criterion>
          <Criterion>基本推理功能正常</Criterion>
        </ExitCriteria>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.3.2">
      <Title>4.3.2 Execution</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.3.3">
      <Title>4.3.3 Diffs</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.3.4">
      <Title>4.3.4 Results</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <!-- ========== Phase P4 ========== -->
    <PhaseHeading>Phase P4 — 动态批处理实现</PhaseHeading>

    <Subsection id="4.4.1">
      <Title>4.4.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P4</PhaseId>
        <Intent>实现动态批处理机制，提高吞吐量，降低GPU空闲时间</Intent>
        <Edits>
          <Edit>
            <Path>backend/providers/local_embedding.py</Path>
            <Operation>modify</Operation>
            <Rationale>添加BatchProcessor类</Rationale>
            <Method>
              1. BatchProcessor类：
                 - asyncio.Queue收集请求
                 - 后台任务定期处理batch
                 - 支持max_batch_size和max_wait_time
              2. 修改LocalEmbeddingProvider.embed()使用BatchProcessor
              3. 确保线程安全和异步兼容
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>python -m pytest tests/test_batch_processor.py (如果编写测试)</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>批处理正确性</Name>
            <Expectation>批量推理结果与单条推理一致</Expectation>
          </Test>
          <Test>
            <Name>吞吐量提升</Name>
            <Expectation>批处理吞吐量 >= 100 texts/sec</Expectation>
          </Test>
          <Test>
            <Name>延迟可控</Name>
            <Expectation>p95延迟 < 200ms</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>BatchProcessor实现完成</Criterion>
          <Criterion>吞吐量达标</Criterion>
          <Criterion>延迟可控</Criterion>
        </ExitCriteria>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.4.2">
      <Title>4.4.2 Execution</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.4.3">
      <Title>4.4.3 Diffs</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.4.4">
      <Title>4.4.4 Results</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <!-- ========== Phase P5 ========== -->
    <PhaseHeading>Phase P5 — 集成测试与性能验证</PhaseHeading>

    <Subsection id="4.5.1">
      <Title>4.5.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P5</PhaseId>
        <Intent>端到端测试，性能基准测试，确保所有AC满足</Intent>
        <Edits>
          <Edit>
            <Path>scripts/benchmark_local_embedding.py</Path>
            <Operation>add</Operation>
            <Rationale>创建性能基准测试脚本</Rationale>
            <Method>
              测试：
              1. 吞吐量测试（100/500/1000 texts）
              2. 延迟测试（p50/p95/p99）
              3. 显存监控
              4. 端到端RAG查询测试
            </Method>
          </Edit>
          <Edit>
            <Path>env.backend.example</Path>
            <Operation>modify</Operation>
            <Rationale>添加local embedding配置示例</Rationale>
            <Method>添加完整的local embedding配置注释和示例</Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>python scripts/benchmark_local_embedding.py --mode throughput</Command>
          <Command>python scripts/benchmark_local_embedding.py --mode latency</Command>
          <Command>nvidia-smi --query-gpu=memory.used --format=csv -l 1</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>吞吐量达标</Name>
            <Expectation>>= 100 texts/sec</Expectation>
          </Test>
          <Test>
            <Name>延迟可控</Name>
            <Expectation>p95 < 200ms</Expectation>
          </Test>
          <Test>
            <Name>显存不超限</Name>
            <Expectation>每张卡 < 11GB</Expectation>
          </Test>
          <Test>
            <Name>端到端RAG查询成功</Name>
            <Expectation>返回正确结果</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>所有性能指标达标</Criterion>
          <Criterion>端到端测试通过</Criterion>
          <Criterion>配置文档完整</Criterion>
        </ExitCriteria>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.5.2">
      <Title>4.5.2 Execution</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.5.3">
      <Title>4.5.3 Diffs</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <Subsection id="4.5.4">
      <Title>4.5.4 Results</Title>
      <Text>待执行后填写</Text>
    </Subsection>

    <!-- ========== Phase P6 (Optional) ========== -->
    <PhaseHeading>Phase P6 — （可选）多模态与 Milvus 混合检索</PhaseHeading>

    <Subsection id="4.6.1">
      <Title>4.6.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P6</PhaseId>
        <Intent>集成GME-Qwen2-VL-2B，支持图片embedding</Intent>
        <Edits>
          <Edit>
            <Path>backend/providers/local_embedding.py</Path>
            <Operation>modify</Operation>
            <Rationale>添加MultimodalEmbeddingProvider</Rationale>
            <Method>
              1. 加载GME-Qwen2-VL-2B到GPU 2
              2. 实现embed_multimodal(texts, images)
              3. 支持文本+图片联合embedding
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>python scripts/download_local_models.py --model OpenGVLab/GME-Qwen2-VL-2B</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>多模态embedding成功</Name>
            <Expectation>embed_multimodal(["text"], [image])返回正确结果</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>多模态embedding功能正常（如果实现）</Criterion>
        </ExitCriteria>
      </PhasePlan>
    </Subsection>

    <Subsection id="4.6.2">
      <Title>4.6.2 Execution</Title>
      <Text>待执行后填写（可选Phase）</Text>
    </Subsection>
  </Section>

  <Section id="dependencies">
    <Heading>5) 依赖清单</Heading>
    <Text>
      **Python包**：
      - torch >= 2.0.0（CUDA 11.8，建议 2.3/2.4）
      - transformers == 4.51.3（GME 兼容性更佳；避免 4.52+）
      - sentence-transformers >= 2.7.0（支持图像输入 encode 字典）
      - accelerate >= 0.25.0
      - numpy >= 1.24.0
      - huggingface_hub (已有)

      **模型**：
      - Qwen/Qwen3-Embedding-4B（~8GB, 2560维）
      - Qwen/Qwen3-Reranker-4B（~8GB）
      - Alibaba-NLP/gme-Qwen2-VL-2B-Instruct（~4GB, 1536维，可选）

      **硬件**：
      - 3× NVIDIA 1080 Ti (Pascal, CUDA Compute Capability 6.1)
      - CUDA 11.8+
      - 至少30GB系统内存
    </Text>
  </Section>

  <Section id="risks">
    <Heading>6) 潜在风险与缓解措施</Heading>
    <List type="bullet">
      <Item>
        <Label>风险1: 显存不足导致OOM</Label>
        <Text>
          缓解：使用4B模型而非8B，单卡部署，监控显存使用
        </Text>
      </Item>
      <Item>
        <Label>风险2: Pascal架构性能不足</Label>
        <Text>
          缓解：使用FP16优化，实现动态批处理提高吞吐量，接受相对较低的单次推理速度
        </Text>
      </Item>
      <Item>
        <Label>风险3: 模型并行实现复杂</Label>
        <Text>
          缓解：采用方案B，避免模型并行，使用单卡部署
        </Text>
      </Item>
      <Item>
        <Label>风险4: 批处理实现bug导致结果错误</Label>
        <Text>
          缓解：充分测试，对比单条推理和批量推理结果一致性
        </Text>
      </Item>
      <Item>
        <Label>风险5: 模型下载失败（网络问题）</Label>
        <Text>
          缓解：提供离线下载脚本，支持从本地路径加载模型
        </Text>
      </Item>
      <Item>
        <Label>风险6: Transformers/GME 版本不兼容</Label>
        <Text>
          缓解：锁定 transformers==4.51.3；如需升级，先在独立环境验证 GME 推理路径。
        </Text>
      </Item>
    </List>
  </Section>

  <Section id="checklist">
    <Heading>7) QUICK CHECKLIST</Heading>
    <Checklist>
      <Item status="pending">[ ] P1: 环境准备完成，GPU可用</Item>
      <Item status="pending">[ ] P2: 模型下载完成，验证通过</Item>
      <Item status="pending">[ ] P3: Provider实现完成，集成到ModelFactory</Item>
      <Item status="pending">[ ] P4: 动态批处理实现，吞吐量达标</Item>
      <Item status="pending">[ ] P5: 集成测试通过，性能验证通过</Item>
      <Item status="pending">[ ] 配置文档更新（env.backend.example）</Item>
      <Item status="pending">[ ] 代码符合项目规范（无硬编码，职责清晰）</Item>
      <Item status="pending">[ ] 所有AC满足</Item>
    </Checklist>
  </Section>

  <Section id="integration_guide">
    <Heading>8) 集成指南</Heading>

    <Subsection id="8.1">
      <Title>8.1 配置步骤</Title>
      <Text>
        1. **安装依赖**：
           ```bash
           pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
           pip install transformers sentence-transformers accelerate
           ```

        2. **下载模型**：
           ```bash
           python scripts/download_local_models.py --model Qwen/Qwen3-Embedding-4B
           python scripts/download_local_models.py --model Qwen/Qwen3-Reranker-4B
           ```

        3. **配置环境变量**（.env.backend）：
           ```bash
           # 切换到本地embedding
           EMBEDDING_PROVIDER=local
           EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-4B
           EMBEDDING_DEVICE=cuda:0
           EMBEDDING_EMBEDDING_DIM=1024
           EMBEDDING_BATCH_SIZE=32
           EMBEDDING_MAX_QUEUE_TIME=0.1

           # 本地reranker
           RERANKER_ENABLED=true
           RERANKER_PROVIDER=local
           RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-4B
           RERANKER_DEVICE=cuda:1
           ```

        4. **启动服务**：
           ```bash
           bash scripts/start_backend.sh
           ```

        5. **验证**：
           ```bash
           curl http://localhost:8000/health
           # 应返回包含local embedding配置的响应
           ```
      </Text>
    </Subsection>

    <Subsection id="8.2">
      <Title>8.2 性能调优建议</Title>
      <Text>
        - **批大小调整**：根据GPU显存和延迟要求调整EMBEDDING_BATCH_SIZE（推荐16-64）
        - **队列等待时间**：EMBEDDING_MAX_QUEUE_TIME平衡吞吐量和延迟（推荐0.05-0.2秒）
        - **FP16精度**：确保使用FP16以节省显存和提升速度
        - **预热**：首次推理较慢，建议启动后预热（发送几次测试请求）
        - **显存监控**：使用nvidia-smi监控显存，避免OOM
      </Text>
    </Subsection>

    <Subsection id="8.3">
      <Title>8.3 故障排查</Title>
      <Text>
        **问题1: CUDA out of memory**
        - 解决：降低batch_size，或使用更小的模型（如Qwen3-Embedding-0.6B）

        **问题2: 推理速度慢**
        - 检查：是否使用FP16，batch_size是否过小
        - 解决：增大batch_size，启用torch.compile()（有限支持）

        **问题3: 模型加载失败**
        - 检查：HF_HOME环境变量，网络连接
        - 解决：使用离线下载，或指定EMBEDDING_MODEL_PATH本地路径

        **问题4: 结果不一致**
        - 检查：批处理实现是否正确
        - 解决：对比单条和批量推理结果，检查索引映射
      </Text>
    </Subsection>
  </Section>

  <Section id="verification_standards">
    <Heading>9) 验证标准</Heading>
    <List type="bullet">
      <Item>
        <Label>功能验证</Label>
        <Text>
          - [ ] 本地embedding服务可启动
          - [ ] API请求返回正确的embedding向量
          - [ ] Reranker返回正确的relevance scores
          - [ ] 端到端RAG查询成功
        </Text>
      </Item>
      <Item>
        <Label>性能验证</Label>
        <Text>
          - [ ] 吞吐量 >= 100 texts/sec (embedding)
          - [ ] p95延迟 < 200ms
          - [ ] Reranker延迟 < 500ms (10 docs)
          - [ ] GPU利用率 > 70%
        </Text>
      </Item>
      <Item>
        <Label>资源验证</Label>
        <Text>
          - [ ] GPU 0显存 < 11GB (embedding)
          - [ ] GPU 1显存 < 11GB (reranker)
          - [ ] 系统内存 < 30GB
          - [ ] 无内存泄漏（长时间运行）
        </Text>
      </Item>
      <Item>
        <Label>代码质量验证</Label>
        <Text>
          - [ ] 无硬编码值
          - [ ] 所有配置通过环境变量
          - [ ] 错误处理完善（Fail-Fast）
          - [ ] 代码符合项目规范
          - [ ] 无技术债务
        </Text>
      </Item>
    </List>
  </Section>

  <Section id="summary">
    <Heading>10) 总结</Heading>
    <Text>
      本任务计划详细规划了从在线embedding API迁移到本地部署的完整方案。通过6个Phase的逐步实施，将在3张NVIDIA 1080 Ti GPU上部署高性能的embedding和reranking服务。

      **核心优势**：
      - 零API成本，长期节省大量费用
      - 数据隐私保护，所有数据本地处理
      - 高性能，通过动态批处理优化吞吐量
      - 可扩展，支持多模态embedding（可选）

      **技术亮点**：
      - 基于现有backend架构，无缝集成
      - 遵循项目规范，零技术债务
      - Fail-Fast设计，问题快速暴露
      - 完整的配置管理和性能监控

      **下一步行动**：
      1. 按Phase顺序执行并在每个Phase结束后回填Execution/Results
      2. 逐项核对“验证标准/AC”与“补充信息”要求是否全部满足
      3. 如需启用多模态与 Milvus 混合检索，执行可选 Phase 并完成回归验证
    </Text>
  </Section>

  <Section id="phases_refined">
    <Heading>11) Phase 细化（输入/输出/依赖/验收）</Heading>

    <!-- ========== Phase P1 ========== -->
    <PhaseHeading>Phase P1 — 环境与版本锁定</PhaseHeading>
    <Subsection id="11.1.1"><Title>11.1.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P1</PhaseId>
        <Intent>锁定依赖与CUDA环境，确保Pascal兼容与可重复</Intent>
        <Inputs>
          - 文件：requirements-backend.txt, pyproject.toml（仅必要时）
          - 环境：CUDA 11.8, 驱动, Python 3.10+
        </Inputs>
        <Outputs>
          - 已安装：torch(2.3/2.4)、transformers==4.51.3、sentence-transformers>=2.7、pymilvus>=2.5（可选）
          - 运行日志：`nvidia-smi`、`torch.cuda.get_device_capability()` 校验(6,1)
        </Outputs>
        <Dependencies>
          - 无
        </Dependencies>
        <Acceptance>
          - 能导入 torch/transformers/sentence_transformers
          - `torch.backends.cuda.can_use_cudnn_attention()` 正常；`attn_implementation` 可设为 sdpa/eager
          - 1080Ti 确认（CC=6.1），不启用FA2/BF16
        </Acceptance>
      </PhasePlan>
    </Subsection>

    <!-- ========== Phase P2 ========== -->
    <PhaseHeading>Phase P2 — 模型下载与预热</PhaseHeading>
    <Subsection id="11.2.1"><Title>11.2.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P2</PhaseId>
        <Intent>落地三模型（可选第3）并完成显存/推理健康检查</Intent>
        <Inputs>
          - 模型：Qwen/Qwen3-Embedding-4B, Qwen/Qwen3-Reranker-4B, Alibaba-NLP/gme-Qwen2-VL-2B-Instruct（可选）
        </Inputs>
        <Outputs>
          - 各模型可在指定 GPU（cuda:0/1/2）以 FP16 加载
          - 预热推理成功（embedding 返回 2560 维；GME 返回 1536 维；reranker 返回分数）
        </Outputs>
        <Dependencies>
          - P1
        </Dependencies>
        <Acceptance>
          - 模型加载耗显存符合预期：~8GB/~8GB/~4GB
          - 预热延迟记录并存档（供P5对比）
        </Acceptance>
      </PhasePlan>
    </Subsection>

    <!-- ========== Phase P3 ========== -->
    <PhaseHeading>Phase P3 — Provider 实现（本地GPU）</PhaseHeading>
    <Subsection id="11.3.1"><Title>11.3.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P3</PhaseId>
        <Intent>新增 LocalEmbeddingProvider / LocalRerankerProvider（与现有接口兼容）</Intent>
        <Inputs>
          - backend/providers/base.py（接口）
          - backend/services/model_factory.py（工厂）
        </Inputs>
        <Outputs>
          - backend/providers/local_embedding.py（新增文件，含 LocalEmbeddingProvider/LocalRerankerProvider/BatchProcessor）
          - 支持 FP16、attn_implementation=sdpa|eager，参数化 batch 阈值
        </Outputs>
        <Dependencies>
          - P2
        </Dependencies>
        <Acceptance>
          - `ModelFactory.create_embedding_func()` 返回的 EmbeddingFunc 能正常工作
          - `ModelFactory.create_reranker()` 返回的异步函数能产出 per-doc 分数
          - 单条/批量结果一致性校验通过
        </Acceptance>
      </PhasePlan>
    </Subsection>

    <!-- ========== Phase P4 ========== -->
    <PhaseHeading>Phase P4 — 配置与工厂集成</PhaseHeading>
    <Subsection id="11.4.1"><Title>11.4.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P4</PhaseId>
        <Intent>扩展 ProviderType/ModelConfig 与 .env，打通端到端调用</Intent>
        <Inputs>
          - backend/config.py（新增 ProviderType.LOCAL_GPU；ModelConfig.extra_params 字段）
          - env.backend.example（示例）
        </Inputs>
        <Outputs>
          - 新 env 键：EMBEDDING_/RERANKER_ 的 device/dtype/attn_implementation/…
          - create_embedding_provider()/create_reranker() 识别 local_gpu 分支
        </Outputs>
        <Dependencies>
          - P3
        </Dependencies>
        <Acceptance>
          - /api/health 返回 provider=local_gpu
          - 通过 RAGService 完成一次 aquery() 并返回结果
        </Acceptance>
      </PhasePlan>
    </Subsection>

    <!-- ========== Phase P5 ========== -->
    <PhaseHeading>Phase P5 — 动态批处理与性能验证</PhaseHeading>
    <Subsection id="11.5.1"><Title>11.5.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P5</PhaseId>
        <Intent>按 TEI 思路实现/调参动态批处理，实现吞吐与p95目标</Intent>
        <Inputs>
          - provider 内部参数：max_batch_tokens/max_batch_size/max_wait_ms
        </Inputs>
        <Outputs>
          - p95 延迟、吞吐曲线；GPU 利用率与峰值显存报告
        </Outputs>
        <Dependencies>
          - P4
        </Dependencies>
        <Acceptance>
          - 吞吐 >= 100 texts/sec；p95 < 200ms（embedding）
          - reranker（10 docs）< 500ms；显存 < 11GB/卡
        </Acceptance>
      </PhasePlan>
    </Subsection>

    <!-- ========== Phase P6 (Optional) ========== -->
    <PhaseHeading>Phase P6 — 多模态与 Milvus 混合检索（可选）</PhaseHeading>
    <Subsection id="11.6.1"><Title>11.6.1 Plan</Title>
      <PhasePlan>
        <PhaseId>P6</PhaseId>
        <Intent>启用 GME 图片/多模态向量 + Milvus 多向量混合检索 + 应用层重排</Intent>
        <Inputs>
          - pymilvus；Milvus 集群（>=2.4，推荐2.6）
        </Inputs>
        <Outputs>
          - named vectors 集合与索引；hybrid_search + RRF/WeightedRanker
        </Outputs>
        <Dependencies>
          - P2（GME 可选）、P4
        </Dependencies>
        <Acceptance>
          - 纯文本/图片/混合 三种检索可用
          - 与纯文本相比，Recall@k 或 MRR@k 有提升（以真实集评估）
        </Acceptance>
      </PhasePlan>
    </Subsection>
  </Section>

  <Section id="references">
    <Heading>12) 参考与最佳实践</Heading>
    <Text>
      - Transformers `attn_implementation=sdpa` 与 FP16 加载示例（官方文档）
        - https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/gpt_neox.md
      - PyTorch CUDA Graphs/SDP/环境变量（官方文档）
        - https://pytorch.org/docs/stable/
      - FastAPI 错误处理与校验（官方文档）
        - https://fastapi.tiangolo.com/tutorial/handling-errors/
      - Sentence-Transformers CrossEncoder/FP16 推理与批处理思路
        - https://github.com/ukplab/sentence-transformers
      - Hugging Face 模型卡：
        - Qwen/Qwen3-Embedding-4B（支持最高 2560 维）
        - Qwen/Qwen3-Reranker-4B（交叉编码器重排）
        - Alibaba-NLP/gme-Qwen2-VL-2B-Instruct（1536 维，多模态）
      - Milvus 多向量/混合检索/融合（RRF、WeightedRanker）
        - https://milvus.io/docs/multi-vector-search.md
        - https://milvus.io/docs/rrf-ranker.md
        - https://milvus.io/docs/weighted-ranker.md
      - 动态批处理参考：HuggingFace Text Embeddings Inference（token-based batching 设计）
        - https://github.com/huggingface/text-embeddings-inference
      - 架构限制说明：BF16（Ampere 起引入），Pascal 无原生支持；FlashAttention2 对算力架构要求较高
        - https://docs.nvidia.com/cuda/archive/11.0/pdf/NVIDIA-CUDA-Programmer-Guide.pdf
        - https://tridao.me/publications/flash2/flash2.pdf
    </Text>
  </Section>
</Task>
