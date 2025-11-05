# User Guide: Manual Re-indexing

## Quick Start

### What is Re-indexing?

Re-indexing rebuilds the knowledge graph for your documents. This is useful when:
- Documents failed to index due to temporary errors
- You upgraded the RAG system and want to use new features
- You updated a document and need to refresh it in the knowledge graph

### Difference: Refresh Index vs Re-index

| Feature | Refresh Index | Re-index |
|---------|---------------|----------|
| **Purpose** | Scan for NEW files | Reprocess EXISTING files |
| **What it does** | Looks for files in upload directory that aren't indexed yet | Rebuilds knowledge graph for already-uploaded files |
| **When to use** | After manually copying files to upload directory | After fixing errors or upgrading system |
| **Safe?** | ✅ Always safe | ⚠️ Force mode rebuilds everything |

## How to Re-index Documents

### Option 1: Re-index Failed Files (Recommended)

**When to use**: Some documents failed to index and you want to retry them

**Steps**:
1. Go to Library view
2. Click the "Re-index" dropdown button in the header
3. Select "Re-index Failed Files"
4. Wait for processing to complete

**What happens**:
- Only documents with "failed" status are re-processed
- Indexed documents are NOT affected
- Safe to use anytime

### Option 2: Force Re-index All Files (Use with Caution)

**When to use**: 
- You upgraded the embedding model
- You changed RAG configuration significantly
- You want to rebuild the entire knowledge graph

**Steps**:
1. Go to Library view
2. Click the "Re-index" dropdown button in the header
3. Select "Force Re-index All Files" (shown in orange)
4. Wait for processing to complete

**What happens**:
- ALL documents are re-processed, even already-indexed ones
- This can take a long time for large libraries
- May consume API credits for embedding generation

### Option 3: Re-index Individual Document

**When to use**: You updated a specific document and need to refresh it

**Steps**:
1. Go to Library view
2. Find the document card
3. Click the 🔄 (refresh) button on the card
4. Wait for processing to complete

**What happens**:
- Only that specific document is re-processed
- Quick and targeted

## Understanding Document Status

### Status Badges

Each document shows a status badge with a color:

| Status | Color | Icon | Meaning |
|--------|-------|------|---------|
| **Pending** | Gray | 🕐 | Waiting to be processed |
| **Processing** | Yellow | ⏳ | Currently being indexed |
| **Indexed** | Green | ✅ | Successfully indexed and ready for queries |
| **Failed** | Red | ❌ | Indexing failed (see error message) |

### When Re-index Button Appears

The 🔄 re-index button appears on document cards when:
- Status is "Indexed" (green) - allows re-indexing if needed
- Status is "Failed" (red) - allows retrying after fixing issues

The button does NOT appear when:
- Status is "Pending" or "Processing" - already being processed

## Common Scenarios

### Scenario 1: API Rate Limit Errors

**Problem**: Several documents show "Failed" status with "Rate limit exceeded" error

**Solution**:
1. Wait a few minutes for rate limits to reset
2. Click "Re-index" → "Re-index Failed Files"
3. Documents will be retried automatically

### Scenario 2: Upgraded Embedding Model

**Problem**: You switched from OpenAI to Azure OpenAI and want to use the new embeddings

**Solution**:
1. Update configuration in Settings
2. Click "Re-index" → "Force Re-index All Files"
3. All documents will be re-embedded with the new model

### Scenario 3: Fixed a Corrupted PDF

**Problem**: A PDF was corrupted, you fixed it, and need to update the knowledge graph

**Solution**:
1. Replace the file in the upload directory
2. Find the document card in Library view
3. Click the 🔄 button on that specific card
4. Document will be re-processed with the fixed file

### Scenario 4: Changed Chunking Strategy

**Problem**: You changed `CHUNK_SIZE` or `CHUNK_OVERLAP` in settings

**Solution**:
1. Update configuration in Settings
2. Click "Re-index" → "Force Re-index All Files"
3. All documents will be re-chunked with new settings

## Monitoring Re-indexing Progress

### Visual Indicators

1. **Button State**:
   - "Re-indexing..." with spinning icon = operation in progress
   - "Re-index" with static icon = ready to use

2. **Document Status**:
   - Watch status badges change: indexed → pending → processing → indexed
   - Yellow "Processing" badge means indexing is happening

3. **Toast Notifications**:
   - Success: "Re-index Complete: X files marked for re-indexing"
   - Error: "Re-index Failed: [error message]"

### Checking Results

After re-indexing completes:
1. Check document status badges - should be green "Indexed"
2. Try querying the documents to verify they're in the knowledge graph
3. Check error messages if any documents failed

## Troubleshooting

### Re-index Button Doesn't Appear

**Possible causes**:
- Document is still "Pending" or "Processing" - wait for it to complete
- Document was just uploaded - wait for initial indexing to finish

### Re-indexing Seems Stuck

**Possible causes**:
1. **Background indexing disabled**: Check Settings → Enable "Auto Indexing"
2. **Large queue**: Many documents ahead in queue - be patient
3. **API errors**: Check backend logs for errors

**Solution**:
1. Check Settings → ensure "Auto Indexing" is enabled
2. Wait a few minutes and refresh the page
3. Check backend logs: `docker logs rag-backend`

### All Documents Show "Failed"

**Possible causes**:
1. **API key invalid**: Check LLM provider API key in Settings
2. **Network issues**: Check internet connection
3. **Configuration error**: Check backend logs

**Solution**:
1. Verify API keys in Settings
2. Check backend logs for specific errors
3. Fix configuration issues
4. Click "Re-index" → "Re-index Failed Files"

### Re-indexing Takes Too Long

**Expected behavior**:
- Small documents (< 10 pages): 10-30 seconds
- Medium documents (10-100 pages): 1-5 minutes
- Large documents (> 100 pages): 5-15 minutes

**If slower than expected**:
1. Check `INDEXING_MAX_FILES_PER_BATCH` setting (default: 5)
2. Check API rate limits
3. Check system resources (CPU, memory)

## Best Practices

### ✅ Do

- **Re-index failed files regularly** to catch temporary errors
- **Test with one document first** before force re-indexing all
- **Monitor status badges** to track progress
- **Check error messages** to understand failures
- **Wait for completion** before querying re-indexed documents

### ❌ Don't

- **Don't force re-index unnecessarily** - wastes API credits and time
- **Don't re-index while uploading** - wait for initial indexing to complete
- **Don't spam the re-index button** - one click is enough
- **Don't ignore failed documents** - investigate and fix the root cause

## FAQ

### Q: Will re-indexing delete my documents?
**A**: No, re-indexing only rebuilds the knowledge graph. Original files are never deleted.

### Q: Can I query documents while re-indexing?
**A**: Yes, but results may be inconsistent until re-indexing completes.

### Q: How often should I re-index?
**A**: Only when needed (after errors, upgrades, or configuration changes). Not on a schedule.

### Q: Does re-indexing cost money?
**A**: Yes, if using paid LLM APIs (OpenAI, Azure). Re-indexing regenerates embeddings which consumes API credits.

### Q: Can I cancel re-indexing?
**A**: Not currently. Once started, re-indexing will complete for all marked files.

### Q: What happens if I close the browser during re-indexing?
**A**: Re-indexing continues in the background. You can close the browser safely.

## Advanced Usage

### API-based Re-indexing

For automation or scripting:

```bash
# Re-index all failed files
curl -X POST http://localhost:8000/api/documents/reindex \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Force re-index all files
curl -X POST http://localhost:8000/api/documents/reindex \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Re-index specific files
curl -X POST http://localhost:8000/api/documents/reindex \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["doc1.pdf", "doc2.pdf"], "force": true}'
```

### Configuration Options

Relevant settings in `backend/config.py`:

```python
# Enable/disable background indexing
AUTO_INDEXING_ENABLED = True

# How often to scan for pending files (seconds)
INDEXING_SCAN_INTERVAL = 30

# Max files to process concurrently
INDEXING_MAX_FILES_PER_BATCH = 5
```

## Getting Help

If you encounter issues:

1. **Check this guide** for common scenarios
2. **Check backend logs**: `docker logs rag-backend`
3. **Check frontend console**: Browser DevTools → Console
4. **Review documentation**: `docs/MANUAL_REINDEXING.md`
5. **Report issues**: Include error messages and steps to reproduce

## Related Documentation

- [Manual Re-indexing Technical Documentation](MANUAL_REINDEXING.md)
- [Document Indexing Automation](ARCHITECTURE_REDESIGN.md)
- [Configuration Guide](../README.md#configuration)

