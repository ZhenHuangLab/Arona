# Frontend Redesign - Quick Start Guide

## What's New?

The RAG-Anything frontend has been completely redesigned with:

✅ **Minimalist Design** - Clean, ChatGPT-style interface  
✅ **No Emojis** - Professional, timeless appearance  
✅ **No Gradients** - Simple color palette with clean lines  
✅ **Tab Navigation** - Chat, Upload, Graph, Library tabs  
✅ **Settings Panel** - Configuration management with hot-reload  
✅ **Knowledge Graph Viz** - View your knowledge graph data  
✅ **Document Library** - See all processed documents  

## Quick Start

### 1. Start the Backend

```bash
# From project root
cd backend
python main.py

# Or use the script
bash scripts/start_backend.sh
```

The backend will start on `http://localhost:8000`

### 2. Start the Frontend

```bash
# From project root
cd frontend
python app.py

# Or use the script
bash scripts/start_frontend.sh
```

The frontend will start on `http://localhost:7860`

### 3. Open in Browser

Navigate to: `http://localhost:7860`

You'll see the new minimalist interface with the **Chat** tab open by default.

## Interface Overview

### Chat Tab (Default)

The main conversation interface:
- **Query Mode Selector**: Choose Hybrid, Local, Global, or Naive
- **Chat Area**: Clean, centered conversation display
- **Input Box**: Single-line input with "Send" button
- **Clear Button**: Reset the conversation

**Usage**:
1. Select your preferred query mode (Hybrid recommended)
2. Type your question in the input box
3. Press Enter or click "Send"
4. View the response in the chat area

### Document Upload Tab

Upload and process documents:
- **File Selector**: Choose PDF, DOCX, PPTX, XLSX, TXT, MD, or HTML
- **Upload & Process**: Single-click upload and processing
- **Status Display**: Real-time processing status

**Usage**:
1. Click "Select Document" and choose a file
2. Click "Upload & Process"
3. Wait for processing to complete
4. Check status in the output area

### Knowledge Graph Tab

Visualize your knowledge graph:
- **Graph Statistics**: Entity and relation counts
- **Graph Data**: View nodes and edges (JSON format)
- **Refresh/Load Buttons**: Update graph data

**Usage**:
1. Click "Refresh Stats" to see graph statistics
2. Click "Load Graph Data" to view graph structure
3. Explore nodes and edges in JSON format

**Note**: Full interactive visualization (D3.js/Cytoscape.js) is planned for future release.

### Document Library Tab

View all processed documents:
- **Document List**: All RAG-indexed documents
- **Metadata**: Status, chunks, processing time
- **Auto-Refresh**: Updates when tab is opened

**Usage**:
1. Switch to the "Document Library" tab
2. View the list of processed documents
3. Click "Refresh List" to update

### Settings Panel

Manage configuration:
- **Backend Status**: Check backend health
- **Current Config**: View active configuration
- **Hot-Reload**: Reload config files without restart

**Usage**:
1. Click "Settings" button (top-right)
2. Expand the settings accordion
3. View backend status and configuration
4. Reload config files as needed

## Configuration Hot-Reload

### How It Works

The hot-reload feature allows you to update configuration without restarting the server:

1. **Edit Configuration**:
   ```bash
   nano .env.backend
   # Make your changes
   ```

2. **Reload in UI**:
   - Open Settings panel
   - Enter config file name (default: `.env.backend`)
   - Click "Reload Configuration"
   - Check reload status

3. **Limitations**:
   - Only reloads environment variables
   - Does NOT reinitialize model providers
   - For major changes, restart the backend

### What Can Be Hot-Reloaded?

✅ Environment variables in `.env.backend`  
❌ YAML configuration files (require restart)  
❌ Model provider changes (require restart)  
❌ Storage path changes (require restart)  

## New Backend Endpoints

### Graph Endpoints

```bash
# Get graph statistics
curl http://localhost:8000/api/graph/stats

# Get graph data (limit 50 nodes)
curl http://localhost:8000/api/graph/data?limit=50

# Get graph data with metadata
curl http://localhost:8000/api/graph/data?limit=100&include_metadata=true
```

### Configuration Endpoints

```bash
# Get current configuration
curl http://localhost:8000/api/config/current

# Reload configuration
curl -X POST http://localhost:8000/api/config/reload \
  -H "Content-Type: application/json" \
  -d '{"config_files": [".env.backend"]}'

# List available config files
curl http://localhost:8000/api/config/files
```

### Document Endpoints

```bash
# List processed documents
curl http://localhost:8000/api/documents/processed

# List uploaded documents
curl http://localhost:8000/api/documents/list
```

## Design Philosophy

### Minimalist Principles

1. **No Emojis**: Professional, accessible design
2. **Clean Colors**: White, gray, subtle green accents
3. **Simple Typography**: System fonts, readable sizes
4. **Generous Whitespace**: Breathing room for content
5. **Focused Layout**: Centered content, clear hierarchy

### Inspired By

- **ChatGPT**: Conversation-first interface
- **Apple Design**: Clean lines, subtle borders
- **Linear**: Minimalist task management
- **Notion**: Clean, functional design

## Troubleshooting

### Backend Not Connecting

**Problem**: "Cannot connect to backend"

**Solution**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `BACKEND_URL` environment variable
3. Check firewall settings

### Graph Data Empty

**Problem**: Graph shows 0 nodes/edges

**Solution**:
1. Process some documents first (Upload tab)
2. Wait for processing to complete
3. Refresh graph stats

### Config Reload Failed

**Problem**: "Failed to reload config"

**Solution**:
1. Check file exists: `ls -la .env.backend`
2. Verify file permissions
3. Check file syntax (no syntax errors)
4. For major changes, restart backend

### UI Not Updating

**Problem**: Changes not visible

**Solution**:
1. Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Clear browser cache
3. Check browser console for errors

## Next Steps

### Recommended Workflow

1. **Upload Documents** → Document Upload tab
2. **Wait for Processing** → Check status
3. **Ask Questions** → Chat tab
4. **Explore Graph** → Knowledge Graph tab
5. **Review Library** → Document Library tab

### Advanced Usage

- **Experiment with Query Modes**: Try different modes for different questions
- **Monitor Graph Growth**: Watch entities/relations increase as you add documents
- **Configuration Tuning**: Adjust settings in `.env.backend` and hot-reload

### Future Features

Coming soon:
- Interactive graph visualization (D3.js/Cytoscape.js)
- Document search and filtering
- Dark mode toggle
- Mobile-responsive design
- Real-time processing updates (WebSocket)

## Support

For issues or questions:
1. Check `docs/FRONTEND_REDESIGN.md` for detailed documentation
2. Review backend logs for errors
3. Check browser console for frontend errors
4. Verify all dependencies are installed

## Summary

The redesigned frontend provides a clean, professional interface for RAG-Anything:

- **Default View**: Chat interface (ChatGPT-style)
- **Navigation**: Tab-based (Chat, Upload, Graph, Library)
- **Settings**: Accordion panel with hot-reload
- **Design**: Minimalist, no emojis, clean colors
- **Backend**: Extended API with graph and config endpoints

Enjoy the new interface! 🎉 (Okay, one emoji in the docs is allowed 😄)

