#!/bin/bash
# Warmup script to preload the embedding model into GPU memory

echo "Warming up qwen3-embedding:8b model..."
echo "This ensures the model is loaded into GPU memory before the test."
echo ""

# Send a simple embedding request to trigger model loading
curl -s http://gpu01:11434/api/embeddings -d '{
  "model": "qwen3-embedding:8b",
  "prompt": "warmup"
}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'embedding' in data and len(data['embedding']) > 0:
    print(f'✅ Model loaded successfully! Embedding dimension: {len(data[\"embedding\"])}')
    sys.exit(0)
else:
    print('❌ Model failed to load or returned empty embedding')
    print(f'Response: {data}')
    sys.exit(1)
"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 Warmup complete! You can now run the test."
else
    echo ""
    echo "⚠️  Warmup failed. Check Ollama service status."
fi

exit $exit_code

