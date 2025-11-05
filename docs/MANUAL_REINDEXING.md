# Manual Re-indexing Feature

## Overview

This document describes the manual re-indexing feature that allows users to force re-processing of documents in the RAG knowledge graph.

## Problem Statement

Previously, the RAG system had the following limitations:

1. **No Manual Re-indexing**: Once a document was indexed, there was no way to re-index it without manually deleting it from the database
2. **Ambiguous "Refresh Index"**: The existing "Refresh Index" button only scanned for new files, but did NOT re-process already indexed documents
3. **No Status Distinction**: Users couldn't easily distinguish between "uploaded but not indexed" vs "fully indexed" documents

## Solution

### Backend Changes

#### 1. New API Endpoint: `POST /api/documents/reindex`

**Purpose**: Manually trigger re-indexing for specific files or all files

**Request Body** (`ReindexRequest`):
```json
{
  "file_paths": ["doc1.pdf", "doc2.pdf"],  // Optional: specific files to re-index. If null, re-index all
  "force": true  // If true, re-index even indexed files. If false, only re-index failed files
}
```

**Response** (`ReindexResponse`):
```json
{
  "files_marked_for_reindex": 5,
  "files_skipped": 2,
  "message": "Re-index request for all files: 5 marked for re-indexing, 2 skipped. Background processing started."
}
```

**Behavior**:
- Changes status of selected files from `indexed` or `failed` to `pending`
- Triggers background processing via `BackgroundIndexer.process_pending_files()`
- Skips files that are already `pending` or `processing`
- In non-force mode, only re-indexes `failed` files
- In force mode, re-indexes all files regardless of current status

#### 2. New Pydantic Models

**File**: `backend/models/index_status.py`

```python
class ReindexRequest(BaseModel):
    """Request model for manual re-indexing operation."""
    file_paths: Optional[list[str]] = None  # None = all files
    force: bool = False  # True = re-index all, False = only failed

class ReindexResponse(BaseModel):
    """Response model for manual re-indexing operation."""
    files_marked_for_reindex: int
    files_skipped: int
    message: str
```

### Frontend Changes

#### 1. New API Client Function

**File**: `frontend/src/api/config.ts`

```typescript
export const reindexDocuments = async (request: ReindexRequest): Promise<ReindexResponse> => {
  const response = await apiClient.post<ReindexResponse>('/api/documents/reindex', request);
  return response.data;
};
```

#### 2. New React Hook: `useReindexDocuments`

**File**: `frontend/src/hooks/useIndexingConfig.ts`

```typescript
export function useReindexDocuments() {
  // Returns: { reindex, isReindexing, error }
}
```

**Usage**:
```typescript
const { reindex, isReindexing } = useReindexDocuments();

// Re-index all failed files
reindex({ force: false });

// Force re-index all files
reindex({ force: true });

// Re-index specific files
reindex({ file_paths: ['doc1.pdf', 'doc2.pdf'], force: true });
```

#### 3. UI Components

##### DocumentCard Component

**File**: `frontend/src/components/documents/DocumentCard.tsx`

**Changes**:
- Added re-index button (🔄 icon) next to delete button
- Button only shows for `indexed` or `failed` files
- Clicking re-indexes that specific document
- Shows spinning animation while re-indexing

##### LibraryView Component

**File**: `frontend/src/views/LibraryView.tsx`

**Changes**:
- Added "Re-index" dropdown menu button in header
- Two options:
  1. **Re-index Failed Files**: Only re-processes files with `failed` status
  2. **Force Re-index All Files**: Re-processes ALL files regardless of status (shown in orange to indicate caution)

## Use Cases

### 1. Re-index Failed Documents

**Scenario**: Some documents failed to index due to temporary issues (e.g., API rate limits, network errors)

**Solution**:
1. Click "Re-index" dropdown in Library view
2. Select "Re-index Failed Files"
3. System marks all `failed` files as `pending` and re-processes them

### 2. Force Re-index After System Upgrade

**Scenario**: You upgraded the RAG system (e.g., new embedding model, improved parsing) and want to rebuild the knowledge graph

**Solution**:
1. Click "Re-index" dropdown in Library view
2. Select "Force Re-index All Files"
3. System marks ALL files as `pending` and re-processes them

### 3. Re-index Specific Document

**Scenario**: A specific document needs to be updated in the knowledge graph (e.g., you fixed the source file)

**Solution**:
1. Find the document card in Library view
2. Click the 🔄 re-index button on the card
3. System marks that file as `pending` and re-processes it

## Status Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Status Flow                     │
└─────────────────────────────────────────────────────────────┘

Upload File
    ↓
[pending] ──────────────────────────────────────┐
    ↓                                           │
Background Indexer picks up                     │
    ↓                                           │
[processing]                                    │
    ↓                                           │
    ├─ Success → [indexed] ─────────────────────┤
    │                ↓                          │
    │           User clicks                     │
    │           "Re-index"                      │
    │                ↓                          │
    │           Back to [pending] ──────────────┘
    │
    └─ Failure → [failed] ──────────────────────┐
                     ↓                          │
                User clicks                     │
                "Re-index Failed"               │
                     ↓                          │
                Back to [pending] ──────────────┘
```

## Architecture

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Re-indexing Data Flow                      │
└──────────────────────────────────────────────────────────────┘

Frontend (LibraryView)
    │
    │ User clicks "Re-index"
    │
    ↓
useReindexDocuments Hook
    │
    │ POST /api/documents/reindex
    │ { force: true/false, file_paths: [...] }
    │
    ↓
Backend (documents.py)
    │
    │ 1. Validate request
    │ 2. Get all index statuses
    │ 3. Filter target files
    │ 4. Update status: indexed/failed → pending
    │ 5. Trigger background processing
    │
    ↓
BackgroundIndexer
    │
    │ 1. Pick up pending files
    │ 2. Process via RAG pipeline
    │ 3. Update status: pending → processing → indexed/failed
    │
    ↓
Knowledge Graph Updated
```

### Key Components

1. **IndexStatusService**: Manages status database (SQLite)
2. **BackgroundIndexer**: Processes pending files in background
3. **RAGService**: Handles document processing pipeline
4. **useReindexDocuments**: React hook for UI state management

## Testing

### Manual Testing Steps

1. **Test Re-index Failed Files**:
   ```bash
   # 1. Upload a document that will fail (e.g., corrupted PDF)
   # 2. Wait for it to fail
   # 3. Click "Re-index" → "Re-index Failed Files"
   # 4. Verify status changes: failed → pending → processing → indexed/failed
   ```

2. **Test Force Re-index All**:
   ```bash
   # 1. Have some indexed documents
   # 2. Click "Re-index" → "Force Re-index All Files"
   # 3. Verify all documents change: indexed → pending → processing → indexed
   ```

3. **Test Individual Re-index**:
   ```bash
   # 1. Find an indexed document card
   # 2. Click the 🔄 button on the card
   # 3. Verify status changes: indexed → pending → processing → indexed
   ```

### API Testing

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

## Configuration

No additional configuration required. The feature uses existing:
- `AUTO_INDEXING_ENABLED`: Must be `true` for background processing
- `INDEXING_SCAN_INTERVAL`: Controls how often background indexer runs
- `INDEXING_MAX_FILES_PER_BATCH`: Limits concurrent processing

## Limitations

1. **No Progress Tracking**: Currently no way to track re-indexing progress for individual files
2. **No Cancellation**: Once re-indexing starts, it cannot be cancelled
3. **No Selective Re-indexing**: Cannot re-index only specific parts of a document (e.g., only images)

## Future Enhancements

1. **Progress Tracking**: Add real-time progress updates for re-indexing operations
2. **Batch Operations**: Allow selecting multiple documents for re-indexing
3. **Scheduled Re-indexing**: Allow scheduling re-indexing at specific times
4. **Incremental Re-indexing**: Only re-process changed parts of documents
5. **Re-indexing History**: Track when documents were last re-indexed

## Related Documentation

- [Document Indexing Automation](../docs/ARCHITECTURE_REDESIGN.md)
- [Background Indexer Service](../backend/services/background_indexer.py)
- [Index Status Tracking](../backend/models/index_status.py)

