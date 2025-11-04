# RAG-Anything UI Quick Reference

## Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│  RAG-Anything                              [⚙️ Settings]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     ┌──────────────┐  ┌──────────────────────┐             │
│     │ 💬 Chat Mode │  │ 📄 Document Viewer   │             │
│     └──────────────┘  └──────────────────────┘             │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                                                       │ │
│  │              Chat Dialog (Centered)                  │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │                                                 │ │ │
│  │  │         Conversation Messages                   │ │ │
│  │  │                                                 │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────┬──────────────────────────┬──────────┐   │ │
│  │  │ Mode ▼ │ Type your question...    │ [➤ Send] │   │ │
│  │  └────────┴──────────────────────────┴──────────┘   │ │
│  │                                                       │ │
│  │  [🗑️ Clear Conversation]                             │ │
│  │                                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Icon Reference

| Icon | Name | Usage |
|------|------|-------|
| 💬 | Chat | Chat Mode tab |
| 📄 | Document | Document Viewer tab |
| ⬆️ | Upload | Upload documents |
| 🕸️ | Graph | Knowledge Graph |
| 📚 | Library | Document Library |
| ⚙️ | Settings | Settings modal |
| ➤ | Send | Send message |
| 🔄 | Refresh | Refresh data |
| 🗑️ | Clear | Clear conversation |
| ✕ | Close | Close modal |
| ☰ | Menu | Secondary menu |

## Navigation Guide

### Primary Navigation

**Chat Mode** (Default)
- Click to access the main chat interface
- Centered dialog with conversation history
- Mode selector integrated into input row
- Quick access to RAG queries

**Document Viewer**
- Click to access document management features
- Shows secondary menu with 3 options
- Manage uploads, view graph, browse library

### Secondary Navigation (Document Viewer Only)

**Upload**
- Upload new documents for processing
- Supported formats: PDF, DOCX, PPTX, XLSX, TXT, MD, HTML
- Real-time processing status

**Knowledge Graph**
- View graph statistics
- Explore knowledge graph data
- Future: Interactive visualization

**Library**
- List all processed documents
- View document metadata
- Check processing status

### Settings Modal

**Access**: Click ⚙️ Settings button in top-right corner

**Features**:
- Backend health status
- Current configuration viewer
- Hot-reload configuration files
- Close with ✕ button or click outside modal

## Common Tasks

### 1. Ask a Question

1. Ensure you're in **Chat Mode** (default view)
2. Select query mode from dropdown (Hybrid recommended)
3. Type your question in the input box
4. Click **Send** button or press Enter
5. View response in chat history

### 2. Upload a Document

1. Click **Document Viewer** tab
2. Click **Upload** in secondary menu
3. Click "Select Document" and choose file
4. Click **Upload & Process** button
5. Wait for processing to complete
6. Check status message

### 3. View Knowledge Graph

1. Click **Document Viewer** tab
2. Click **Knowledge Graph** in secondary menu
3. Click **Refresh Stats** to see graph statistics
4. Click **Load Graph Data** to view graph structure
5. Explore nodes and relationships (JSON format)

### 4. Browse Document Library

1. Click **Document Viewer** tab
2. Click **Library** in secondary menu
3. View list of processed documents
4. Click **Refresh List** to update
5. Check document status and chunk counts

### 5. Check Backend Status

1. Click **Settings** button (⚙️) in top-right
2. View "Backend Status" section
3. Click **Refresh** to update status
4. Check version and health information
5. Close modal when done

### 6. Reload Configuration

1. Click **Settings** button (⚙️)
2. Scroll to "Hot-Reload Configuration"
3. Enter config file names (default: `.env.backend`)
4. Click **Reload Configuration**
5. Check reload status message
6. **Note**: Some changes require server restart

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message (when input focused) |
| Esc | Close modal (future enhancement) |
| Ctrl+K | Focus chat input (future enhancement) |

## Query Modes Explained

**Hybrid** (Recommended)
- Combines multiple retrieval strategies
- Best for general-purpose queries
- Balances accuracy and coverage

**Local**
- Focuses on specific document sections
- Best for detailed, specific questions
- Higher precision, narrower scope

**Global**
- Searches across entire knowledge base
- Best for broad, conceptual questions
- Wider coverage, may be less precise

**Naive**
- Simple keyword-based search
- Fastest but least sophisticated
- Use for quick lookups

## Tips & Best Practices

### Chat Interface
- ✅ Use Hybrid mode for most queries
- ✅ Ask specific, well-formed questions
- ✅ Clear conversation when switching topics
- ✅ Review mode selection before sending

### Document Upload
- ✅ Upload one document at a time for better tracking
- ✅ Wait for processing to complete before querying
- ✅ Check supported formats before uploading
- ✅ Use descriptive file names

### Knowledge Graph
- ✅ Refresh stats after uploading new documents
- ✅ Use graph data to understand document relationships
- ✅ Check entity and relation counts
- ✅ Future: Interactive exploration coming soon

### Settings
- ✅ Check backend status if queries fail
- ✅ Reload config after editing .env files
- ✅ Restart server for major config changes
- ✅ Keep modal open while making multiple changes

## Troubleshooting

### Chat not responding
1. Check backend status in Settings
2. Verify documents are uploaded and processed
3. Try different query mode
4. Check browser console for errors

### Upload failing
1. Verify file format is supported
2. Check file size (large files take longer)
3. Ensure backend is running
4. Check upload status message for details

### Settings modal not opening
1. Refresh browser page
2. Clear browser cache
3. Check for JavaScript errors
4. Try different browser

### Mode switching not working
1. Click directly on tab button
2. Wait for view to load
3. Refresh page if stuck
4. Check browser console

## Visual Design Elements

### Colors

- **Primary Green**: `#10a37f` - Active states, primary actions
- **Secondary Purple**: `#7c3aed` - Accents, secondary features
- **Text Primary**: `#2e2e2e` - Main text
- **Text Secondary**: `#6e6e6e` - Labels, hints
- **Border**: `#e5e5e5` - Dividers, borders
- **Background**: `#ffffff` - Main background
- **Secondary BG**: `#f7f7f8` - Cards, panels

### Typography

- **Font Family**: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto
- **Header**: 1.5rem, weight 600
- **Body**: 1rem, weight 400
- **Labels**: 0.875rem, weight 500

### Spacing

- **Small**: 0.5rem (8px)
- **Medium**: 1rem (16px)
- **Large**: 2rem (32px)
- **Border Radius**: 8-12px (rounded corners)

## Accessibility

- All icons include text labels
- High contrast color scheme
- Keyboard navigation support
- Clear focus indicators
- Semantic HTML structure

## Browser Support

- ✅ Chrome 120+
- ✅ Firefox 120+
- ✅ Safari 17+
- ✅ Edge 120+
- ⚠️ Older browsers may have limited CSS support

## Getting Help

- Check this quick reference first
- Review FRONTEND_REDESIGN_V2.md for detailed documentation
- Check browser console for error messages
- Verify backend is running and accessible
- Report issues with screenshots and error logs

