import asyncio
import sys
import types
import numpy as np
import pytest

# Provide lightweight stubs for optional heavy deps to import the module under test
if "sentence_transformers" not in sys.modules:
    st_mod = types.ModuleType("sentence_transformers")

    # simple placeholder; our tests inject a mock model instance directly
    class _ST:  # pragma: no cover - placeholder
        pass

    st_mod.SentenceTransformer = _ST
    sys.modules["sentence_transformers"] = st_mod

if "transformers" not in sys.modules:
    tr_mod = types.ModuleType("transformers")

    class _TOK:  # pragma: no cover - placeholder
        pass

    class _CLS:  # pragma: no cover - placeholder
        pass

    class _CAUSAL:  # pragma: no cover - placeholder
        pass

    class _MODEL:  # pragma: no cover - placeholder
        pass

    class _PROC:  # pragma: no cover - placeholder
        pass

    tr_mod.AutoTokenizer = _TOK
    tr_mod.AutoModelForSequenceClassification = _CLS
    tr_mod.AutoModelForCausalLM = _CAUSAL
    tr_mod.AutoModel = _MODEL
    tr_mod.AutoProcessor = _PROC
    sys.modules["transformers"] = tr_mod

if "torch" not in sys.modules:
    torch_mod = types.ModuleType("torch")
    # dtypes
    torch_mod.float16 = "float16"
    torch_mod.float32 = "float32"

    class _NoGrad:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def no_grad():  # pragma: no cover - context manager stub
        return _NoGrad()

    torch_mod.no_grad = no_grad

    class _Cuda:
        @staticmethod
        def is_available():
            return False

        @staticmethod
        def memory_allocated(device):
            return 0

    torch_mod.cuda = _Cuda()

    sys.modules["torch"] = torch_mod

# PIL is optional; stub it so importing backend.providers.local_embedding works in minimal envs
if "PIL" not in sys.modules:
    pil_mod = types.ModuleType("PIL")
    pil_image_mod = types.ModuleType("PIL.Image")

    class _Image:  # pragma: no cover - placeholder
        pass

    pil_image_mod.Image = _Image
    pil_mod.Image = pil_image_mod

    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = pil_image_mod

from backend.providers.local_embedding import BatchProcessor


class MockSentenceTransformer:
    """A lightweight mock of SentenceTransformer for unit tests."""

    def __init__(self, embedding_dim: int = 8):
        self.embedding_dim = embedding_dim
        self.encode_call_sizes = []  # record number of texts per encode call
        self.tokenize_call_sizes = []

    # Mimic sentence-transformers' encode signature
    def encode(
        self, texts, convert_to_tensor=True, show_progress_bar=False, batch_size=32
    ):
        size = len(texts)
        self.encode_call_sizes.append(size)
        # Deterministic embeddings for test: [[0..], [1..], ...]
        arr = np.arange(size * self.embedding_dim, dtype=np.float32).reshape(
            size, self.embedding_dim
        )

        class _MockTensor:
            def __init__(self, a):
                self._a = a

            def cpu(self):
                return self

            def numpy(self):
                return self._a

        return _MockTensor(arr)

    # Mimic sentence-transformers' tokenize API
    def tokenize(self, texts):
        # Use character count as token count for simplicity
        input_ids = [[0] * len(t) for t in texts]
        self.tokenize_call_sizes.append(len(texts))
        return {"input_ids": input_ids}


@pytest.mark.asyncio
async def test_batching_by_size():
    model = MockSentenceTransformer()
    processor = BatchProcessor(model=model, max_batch_size=2, max_wait_time=0.2)
    processor.start()

    # Submit three single-text requests concurrently
    r1 = asyncio.create_task(processor.embed(["a"]))
    r2 = asyncio.create_task(processor.embed(["b"]))
    r3 = asyncio.create_task(processor.embed(["c"]))

    e1, e2, e3 = await asyncio.gather(r1, r2, r3)

    # Two batches expected: first with 2 texts, then 1
    assert model.encode_call_sizes[0] == 2
    assert model.encode_call_sizes[1] == 1

    # Result shapes
    assert e1.shape == (1, model.embedding_dim)
    assert e2.shape == (1, model.embedding_dim)
    assert e3.shape == (1, model.embedding_dim)

    await processor.shutdown()


@pytest.mark.asyncio
async def test_max_batch_tokens_limits():
    model = MockSentenceTransformer()
    # Set a small token budget so that batches split by character length
    processor = BatchProcessor(
        model=model,
        max_batch_size=10,
        max_wait_time=0.2,
        max_batch_tokens=5,
    )
    processor.start()

    # token counts by char length: 4, 3, 2
    r1 = asyncio.create_task(processor.embed(["aaaa"]))  # 4 tokens
    r2 = asyncio.create_task(processor.embed(["bbb"]))  # 3 tokens
    r3 = asyncio.create_task(processor.embed(["cc"]))  # 2 tokens

    e1, e2, e3 = await asyncio.gather(r1, r2, r3)

    # Expect two encode calls: ["aaaa"] then ["bbb","cc"] because 4 + 3 > 5
    assert model.encode_call_sizes[0] == 1
    assert model.encode_call_sizes[1] == 2

    # Shapes match per request sizes
    assert e1.shape == (1, model.embedding_dim)
    assert e2.shape == (1, model.embedding_dim)
    assert e3.shape == (1, model.embedding_dim)

    await processor.shutdown()


@pytest.mark.asyncio
async def test_multi_text_request_roundtrips():
    model = MockSentenceTransformer(embedding_dim=6)
    processor = BatchProcessor(model=model, max_batch_size=8, max_wait_time=0.1)
    processor.start()

    res = await processor.embed(["a", "bb", "ccc"])  # 3 texts in one request
    assert isinstance(res, np.ndarray)
    assert res.shape == (3, 6)

    await processor.shutdown()


@pytest.mark.asyncio
async def test_shutdown_is_graceful():
    model = MockSentenceTransformer()
    processor = BatchProcessor(model=model, max_batch_size=2, max_wait_time=0.05)
    processor.start()

    # Fire some requests
    tasks = [asyncio.create_task(processor.embed([str(i)])) for i in range(4)]
    _ = await asyncio.gather(*tasks)

    # Should shutdown cleanly
    await processor.shutdown()
    # Background task cleared
    assert processor._processor_task is None
