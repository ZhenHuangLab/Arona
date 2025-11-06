# Troubleshooting Guide

## ImportError: cannot import name 'LightRAG' from 'lightrag'

### Problem Description

When starting the backend, you may encounter the following error:

```
ImportError: cannot import name 'LightRAG' from 'lightrag' (/path/to/.venv/lib/python3.11/site-packages/lightrag/__init__.py)
```

### Root Cause

This issue occurs due to two main reasons:

1. **Package Name Conflict**: There are two different packages with similar names:
   - `lightrag` (version 0.1.0b6) - A different package (possibly from AdalFlow project)
   - `lightrag-hku` (version 1.4.9.1) - The package required by this project

   When both are installed, Python imports the wrong `lightrag` package.

2. **Missing `__init__.py`**: The `lightrag-hku` package installs to a `lightrag` directory but doesn't include a proper `__init__.py` file that exports the necessary classes.

### Solution

#### Step 1: Remove Conflicting Package

Uninstall the conflicting `lightrag` package:

```bash
uv pip uninstall lightrag
```

#### Step 2: Create Proper `__init__.py`

Create or update the `__init__.py` file in the lightrag package directory:

```bash
cat > .venv/lib/python3.11/site-packages/lightrag/__init__.py << 'EOF'
"""LightRAG - A lightweight RAG framework."""

from lightrag.lightrag import LightRAG
from lightrag.base import QueryParam
from lightrag.utils import EmbeddingFunc

__version__ = "1.4.9.1"

__all__ = ["LightRAG", "QueryParam", "EmbeddingFunc"]
EOF
```

**Note**: Adjust the Python version in the path if you're using a different version.

#### Step 3: Verify the Fix

Test that the imports work correctly:

```bash
python -c "from lightrag import LightRAG, QueryParam, EmbeddingFunc; print('✅ All imports successful')"
python -c "from raganything.raganything import RAGAnything; print('✅ RAGAnything imported successfully')"
python -c "from backend.main import app; print('✅ Backend app imported successfully')"
```

#### Step 4: Start the Backend

Now you should be able to start the backend without errors:

```bash
python -m backend.main --host 0.0.0.0 --port 8000
```

### Prevention

To prevent this issue in the future:

1. **Check installed packages** before installation:
   ```bash
   uv pip list | grep -i lightrag
   ```

2. **Only install `lightrag-hku`**, not `lightrag`:
   ```bash
   uv pip install lightrag-hku
   ```

3. **Use virtual environments** to isolate dependencies

### Related Issues

- Package name conflicts between `lightrag` and `lightrag-hku`
- Missing or incomplete `__init__.py` in installed packages
- Python module resolution order

### Additional Notes

This is a temporary workaround. The proper fix would be for the `lightrag-hku` package maintainers to:
1. Include a proper `__init__.py` file in their package
2. Choose a unique package name to avoid conflicts

If you encounter this issue after reinstalling dependencies, you may need to repeat Step 2 to recreate the `__init__.py` file.

