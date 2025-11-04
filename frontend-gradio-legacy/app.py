"""
RAG-Anything Gradio Frontend - Redesigned

Minimalist web interface with modal settings, SVG icons, and centered chat interface.
Design: Clean, modern interface with 2-mode navigation and icon-based UI.
"""

import os
import sys
from pathlib import Path
import requests
from typing import List, Tuple, Optional, Dict, Any
import json

import gradio as gr

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_API = f"{BACKEND_URL}/api"


# ============================================================================
# SVG Icons - Line Style (Minimalist)
# ============================================================================

ICONS = {
    "chat": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>""",

    "document": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>""",

    "upload": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>""",

    "graph": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"></circle><circle cx="6" cy="6" r="3"></circle><circle cx="18" cy="6" r="3"></circle><path d="M6 9v6"></path><path d="M18 9v6"></path><path d="M9 6h6"></path></svg>""",

    "library": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>""",

    "settings": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M12 1v6m0 6v6m5.2-13.2l-4.2 4.2m-2 2l-4.2 4.2M23 12h-6m-6 0H5m13.2 5.2l-4.2-4.2m-2-2l-4.2-4.2"></path></svg>""",

    "send": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>""",

    "refresh": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>""",

    "clear": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>""",

    "close": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>""",

    "menu": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>""",
}

def icon_html(name: str, size: int = 20) -> str:
    """Generate HTML for an icon with optional text."""
    svg = ICONS.get(name, "")
    return f'<span style="display: inline-flex; align-items: center; gap: 0.5rem;">{svg}</span>'


# ============================================================================
# Custom CSS - Redesigned with Modal, Icons, Rounded Tabs
# ============================================================================
CUSTOM_CSS = """
/* Global Styles - Minimalist Design */
:root {
    --primary-bg: #ffffff;
    --secondary-bg: #f7f7f8;
    --border-color: #e5e5e5;
    --text-primary: #2e2e2e;
    --text-secondary: #6e6e6e;
    --accent-color: #10a37f;
    --accent-secondary: #7c3aed;
    --hover-bg: #f0f0f0;
    --modal-overlay: rgba(0, 0, 0, 0.5);
}

/* Remove gradients and emojis */
.gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--primary-bg);
}

/* Clean header with settings button */
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 2rem;
    border-bottom: 1px solid var(--border-color);
}

.header-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.02em;
}

.settings-btn-container {
    display: flex;
    align-items: center;
}

/* Modal Overlay */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--modal-overlay);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    backdrop-filter: blur(4px);
}

/* Modal Dialog */
.modal-dialog {
    background: var(--primary-bg);
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    padding: 2rem;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.modal-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
}

.modal-close {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
    color: var(--text-secondary);
    transition: color 0.2s;
}

.modal-close:hover {
    color: var(--text-primary);
}

/* Centered Tab Switcher with Rounded Rectangles */
.mode-switcher {
    display: flex;
    justify-content: center;
    padding: 2rem 1rem;
    gap: 1rem;
}

.mode-tab {
    padding: 0.75rem 2rem;
    border-radius: 12px;
    border: 2px solid var(--border-color);
    background: var(--primary-bg);
    color: var(--text-secondary);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.mode-tab:hover {
    border-color: var(--accent-color);
    background: var(--hover-bg);
}

.mode-tab.active {
    background: var(--accent-color);
    color: white;
    border-color: var(--accent-color);
}

.mode-tab.secondary {
    background: var(--accent-secondary);
    color: white;
    border-color: var(--accent-secondary);
}

/* Chat Dialog - Centered Large Box */
.chat-dialog {
    max-width: 900px;
    margin: 2rem auto;
    background: var(--primary-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Chat interface - centered, clean */
.chatbot-container {
    max-width: 100%;
    margin: 0 auto;
}

/* Input row with mode dropdown on left */
.input-row {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;
}

.input-row .mode-selector {
    flex: 0 0 140px;
}

.input-row .query-input {
    flex: 1;
}

.input-row .send-btn {
    flex: 0 0 auto;
}

/* Buttons - minimal */
.btn-primary {
    background: var(--accent-color);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.625rem 1.25rem;
    font-weight: 500;
    transition: opacity 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn-primary:hover {
    opacity: 0.9;
}

.btn-secondary {
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.625rem 1.25rem;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn-secondary:hover {
    background: var(--hover-bg);
    color: var(--text-primary);
}

.btn-icon {
    padding: 0.5rem;
    min-width: auto;
}

/* Secondary Menu Dropdown */
.secondary-menu {
    max-width: 900px;
    margin: 0 auto 2rem;
    text-align: center;
}

.menu-dropdown {
    display: inline-block;
    position: relative;
}

/* Clean cards */
.card {
    background: var(--primary-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}

/* Status indicator */
.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.5rem;
}

.status-healthy {
    background: #10a37f;
}

.status-error {
    background: #ef4444;
}

/* Icon styling */
.icon-label {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.icon-label svg {
    flex-shrink: 0;
}

/* Hide default Gradio tab styling */
.tabs {
    border: none !important;
}

.tab-nav {
    display: none !important;
}
"""


# ============================================================================
# Backend Communication Functions
# ============================================================================

def check_backend_health() -> Tuple[bool, str]:
    """Check if backend is healthy."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"Backend healthy (v{data.get('version', 'unknown')})"
        else:
            return False, f"Backend returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to backend at {BACKEND_URL}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def upload_and_process_document(file) -> str:
    """Upload and process a document."""
    if file is None:
        return "No file selected"

    try:
        # Upload file
        with open(file.name, "rb") as f:
            files = {"file": (Path(file.name).name, f)}
            response = requests.post(
                f"{BACKEND_API}/documents/upload-and-process",
                files=files,
                timeout=300,  # 5 minutes for processing
            )

        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                return f"Document processed successfully\n\nFile: {data['file_path']}"
            else:
                return f"Processing failed: {data.get('error', 'Unknown error')}"
        else:
            return f"Upload failed with status {response.status_code}"

    except Exception as e:
        return f"Error: {str(e)}"


def query_rag(
    query: str,
    mode: str,
    history: List[Tuple[str, str]]
) -> Tuple[List[Tuple[str, str]], str]:
    """Execute a RAG query."""
    if not query.strip():
        return history, ""

    try:
        # Prepare request
        payload = {
            "query": query,
            "mode": mode.lower(),
        }

        # Execute query
        response = requests.post(
            f"{BACKEND_API}/query/",
            json=payload,
            timeout=120,
        )

        if response.status_code == 200:
            data = response.json()
            answer = data["response"]

            # Update history
            history = history + [(query, answer)]

            return history, ""
        else:
            error_msg = f"Query failed with status {response.status_code}"
            history = history + [(query, error_msg)]
            return history, ""

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history = history + [(query, error_msg)]
        return history, ""


def clear_conversation():
    """Clear conversation history."""
    return [], ""


def get_processed_documents() -> str:
    """Get list of processed documents."""
    try:
        response = requests.get(f"{BACKEND_API}/documents/processed", timeout=10)
        if response.status_code == 200:
            data = response.json()
            docs = data.get("documents", [])
            if not docs:
                return "No documents have been processed yet."

            result = f"Total processed documents: {data.get('total', 0)}\n\n"
            for doc in docs:
                result += f"• {doc.get('file_path', 'Unknown')}\n"
                result += f"  Status: {doc.get('status', 'unknown')}\n"
                result += f"  Chunks: {doc.get('chunks', 0)}\n\n"
            return result
        else:
            return f"Failed to fetch documents: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_graph_stats() -> Dict[str, Any]:
    """Get knowledge graph statistics."""
    try:
        response = requests.get(f"{BACKEND_API}/graph/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch stats: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def reload_config(config_files: Optional[List[str]] = None) -> str:
    """Reload configuration files."""
    try:
        payload = {"config_files": config_files} if config_files else {}
        response = requests.post(
            f"{BACKEND_API}/config/reload",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return f"Status: {data['status']}\n{data['message']}\n\nReloaded: {', '.join(data['reloaded_files'])}"
        else:
            return f"Failed to reload config: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_current_config() -> str:
    """Get current configuration."""
    try:
        response = requests.get(f"{BACKEND_API}/config/current", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return json.dumps(data, indent=2)
        else:
            return f"Failed to fetch config: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# Create Gradio Interface - Redesigned with Modal and Icons
# ============================================================================

with gr.Blocks(
    title="RAG-Anything",
    css=CUSTOM_CSS,
    theme=gr.themes.Base(
        primary_hue="green",
        neutral_hue="gray",
        font=["Inter", "system-ui", "sans-serif"]
    )
) as app:

    # State for modal visibility
    settings_modal_visible = gr.State(False)
    current_mode = gr.State("chat")  # "chat" or "document"
    secondary_view = gr.State("upload")  # "upload", "graph", or "library"

    # Header with Settings Button
    with gr.Row(elem_classes="header-container"):
        gr.HTML('<h1 class="header-title">RAG-Anything</h1>')
        settings_btn = gr.Button(
            f'<span class="icon-label">{ICONS["settings"]} Settings</span>',
            elem_classes="btn-secondary btn-icon",
            size="sm"
        )

    # Mode Switcher - Centered Rounded Tabs
    with gr.Row(elem_classes="mode-switcher"):
        chat_mode_btn = gr.Button(
            f'<span class="icon-label">{ICONS["chat"]} Chat Mode</span>',
            elem_classes="mode-tab active",
            elem_id="chat-mode-btn"
        )
        document_mode_btn = gr.Button(
            f'<span class="icon-label">{ICONS["document"]} Document Viewer</span>',
            elem_classes="mode-tab",
            elem_id="document-mode-btn"
        )

    # ========================================================================
    # CHAT MODE VIEW
    # ========================================================================
    with gr.Column(visible=True, elem_id="chat-mode-view") as chat_view:

        # Chat Dialog - Centered Large Box
        with gr.Column(elem_classes="chat-dialog"):

            # Chatbot
            chatbot = gr.Chatbot(
                label="",
                height=500,
                show_label=False,
                bubble_full_width=False,
                elem_classes="chatbot-container"
            )

            # Input row with mode dropdown on left
            with gr.Row(elem_classes="input-row"):
                mode_dropdown = gr.Dropdown(
                    choices=["Hybrid", "Local", "Global", "Naive"],
                    value="Hybrid",
                    label="",
                    show_label=False,
                    container=False,
                    elem_classes="mode-selector",
                    scale=0
                )
                query_input = gr.Textbox(
                    label="",
                    placeholder="Ask a question about your documents...",
                    lines=1,
                    show_label=False,
                    container=False,
                    elem_classes="query-input",
                    scale=1
                )
                submit_btn = gr.Button(
                    f'{ICONS["send"]}',
                    variant="primary",
                    elem_classes="btn-primary btn-icon",
                    scale=0
                )

            # Clear button
            with gr.Row():
                clear_btn = gr.Button(
                    f'<span class="icon-label">{ICONS["clear"]} Clear Conversation</span>',
                    size="sm",
                    elem_classes="btn-secondary"
                )

        # Event handlers for chat
        submit_btn.click(
            fn=query_rag,
            inputs=[query_input, mode_dropdown, chatbot],
            outputs=[chatbot, query_input],
        )

        query_input.submit(
            fn=query_rag,
            inputs=[query_input, mode_dropdown, chatbot],
            outputs=[chatbot, query_input],
        )

        clear_btn.click(
            fn=clear_conversation,
            outputs=[chatbot, query_input],
        )

    # ========================================================================
    # DOCUMENT VIEWER MODE
    # ========================================================================
    with gr.Column(visible=False, elem_id="document-mode-view") as document_view:

        # Secondary Menu - Dropdown for Upload/Graph/Library
        with gr.Row(elem_classes="secondary-menu"):
            upload_tab_btn = gr.Button(
                f'<span class="icon-label">{ICONS["upload"]} Upload</span>',
                elem_classes="btn-secondary",
                size="sm"
            )
            graph_tab_btn = gr.Button(
                f'<span class="icon-label">{ICONS["graph"]} Knowledge Graph</span>',
                elem_classes="btn-secondary",
                size="sm"
            )
            library_tab_btn = gr.Button(
                f'<span class="icon-label">{ICONS["library"]} Library</span>',
                elem_classes="btn-secondary",
                size="sm"
            )

        # Upload View
        with gr.Column(visible=True, elem_id="upload-view") as upload_view:
            gr.Markdown("### Upload Documents")
            gr.Markdown("Supported formats: PDF, DOCX, PPTX, XLSX, TXT, MD, HTML")

            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="Select Document",
                        file_types=[
                            ".pdf", ".docx", ".pptx", ".xlsx",
                            ".txt", ".md", ".html"
                        ]
                    )
                    upload_btn = gr.Button(
                        f'<span class="icon-label">{ICONS["upload"]} Upload & Process</span>',
                        variant="primary",
                        elem_classes="btn-primary"
                    )

                with gr.Column(scale=1):
                    upload_output = gr.Textbox(
                        label="Status",
                        lines=10,
                        interactive=False,
                    )

            upload_btn.click(
                fn=upload_and_process_document,
                inputs=[file_input],
                outputs=[upload_output],
            )

        # Knowledge Graph View
        with gr.Column(visible=False, elem_id="graph-view") as graph_view:
            gr.Markdown("### Knowledge Graph Visualization")
            gr.Markdown("Explore the knowledge graph built from your documents.")

            # Graph stats
            with gr.Row():
                graph_stats_output = gr.JSON(label="Graph Statistics")
                refresh_stats_btn = gr.Button(
                    f'<span class="icon-label">{ICONS["refresh"]} Refresh Stats</span>',
                    elem_classes="btn-secondary"
                )

            # Graph visualization placeholder
            gr.Markdown("#### Graph Visualization")
            gr.Markdown("*Note: Full interactive graph visualization will be implemented using a JavaScript library like D3.js or Cytoscape.js*")

            # For now, show graph data as JSON
            graph_data_output = gr.JSON(label="Graph Data (Sample)")
            load_graph_btn = gr.Button(
                f'<span class="icon-label">{ICONS["graph"]} Load Graph Data</span>',
                variant="primary",
                elem_classes="btn-primary"
            )

            def load_graph_data():
                """Load graph data from backend."""
                try:
                    response = requests.get(f"{BACKEND_API}/graph/data?limit=50", timeout=30)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return {"error": f"Failed to load graph: {response.status_code}"}
                except Exception as e:
                    return {"error": str(e)}

            refresh_stats_btn.click(
                fn=get_graph_stats,
                outputs=[graph_stats_output],
            )

            load_graph_btn.click(
                fn=load_graph_data,
                outputs=[graph_data_output],
            )

        # Library View
        with gr.Column(visible=False, elem_id="library-view") as library_view:
            gr.Markdown("### Processed Documents")
            gr.Markdown("View all documents that have been processed and indexed in the RAG system.")

            docs_output = gr.Textbox(
                label="Processed Documents",
                lines=20,
                interactive=False,
            )

            refresh_docs_btn = gr.Button(
                f'<span class="icon-label">{ICONS["refresh"]} Refresh List</span>',
                variant="primary",
                elem_classes="btn-primary"
            )

            refresh_docs_btn.click(
                fn=get_processed_documents,
                outputs=[docs_output],
            )

    # ========================================================================
    # SETTINGS MODAL
    # ========================================================================
    with gr.Column(visible=False, elem_classes="modal-overlay", elem_id="settings-modal") as settings_modal:
        with gr.Column(elem_classes="modal-dialog"):

            # Modal Header
            with gr.Row(elem_classes="modal-header"):
                gr.HTML('<h2 class="modal-title">Settings</h2>')
                close_modal_btn = gr.Button(
                    f'{ICONS["close"]}',
                    elem_classes="modal-close btn-icon",
                    size="sm"
                )

            # Modal Content
            gr.Markdown("### Configuration Management")

            # Backend status
            with gr.Row():
                status_text = gr.Textbox(
                    label="Backend Status",
                    value="Checking...",
                    interactive=False,
                    scale=3,
                )
                refresh_status_btn = gr.Button(
                    f'{ICONS["refresh"]}',
                    size="sm",
                    scale=1,
                    elem_classes="btn-secondary btn-icon"
                )

            # Current configuration
            gr.Markdown("#### Current Configuration")
            current_config_output = gr.Code(
                label="",
                language="json",
                lines=15,
                interactive=False,
            )
            load_config_btn = gr.Button(
                "Load Current Config",
                elem_classes="btn-secondary"
            )

            # Configuration reload
            gr.Markdown("#### Hot-Reload Configuration")
            gr.Markdown("*Warning: This reloads environment variables but does not reinitialize services. For full changes, restart the server.*")

            config_files_input = gr.Textbox(
                label="Config Files (comma-separated)",
                placeholder=".env.backend",
                value=".env.backend",
            )
            reload_btn = gr.Button(
                "Reload Configuration",
                variant="primary",
                elem_classes="btn-primary"
            )
            reload_output = gr.Textbox(
                label="Reload Status",
                lines=5,
                interactive=False,
            )

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    # Helper function for status check
    def check_status():
        healthy, message = check_backend_health()
        return message

    # Settings Modal Toggle
    def toggle_settings_modal(current_visible):
        return not current_visible

    settings_btn.click(
        fn=lambda: gr.update(visible=True),
        outputs=[settings_modal]
    )

    close_modal_btn.click(
        fn=lambda: gr.update(visible=False),
        outputs=[settings_modal]
    )

    # Settings Panel Actions
    refresh_status_btn.click(
        fn=check_status,
        outputs=[status_text],
    )

    load_config_btn.click(
        fn=get_current_config,
        outputs=[current_config_output],
    )

    def reload_config_wrapper(files_str):
        files = [f.strip() for f in files_str.split(",") if f.strip()]
        return reload_config(files if files else None)

    reload_btn.click(
        fn=reload_config_wrapper,
        inputs=[config_files_input],
        outputs=[reload_output],
    )

    # Mode Switching (Chat vs Document Viewer)
    def switch_to_chat():
        return (
            gr.update(visible=True),   # chat_view
            gr.update(visible=False),  # document_view
        )

    def switch_to_document():
        return (
            gr.update(visible=False),  # chat_view
            gr.update(visible=True),   # document_view
        )

    chat_mode_btn.click(
        fn=switch_to_chat,
        outputs=[chat_view, document_view]
    )

    document_mode_btn.click(
        fn=switch_to_document,
        outputs=[chat_view, document_view]
    )

    # Secondary Menu Switching (Upload/Graph/Library)
    def show_upload():
        return (
            gr.update(visible=True),   # upload_view
            gr.update(visible=False),  # graph_view
            gr.update(visible=False),  # library_view
        )

    def show_graph():
        return (
            gr.update(visible=False),  # upload_view
            gr.update(visible=True),   # graph_view
            gr.update(visible=False),  # library_view
        )

    def show_library():
        return (
            gr.update(visible=False),  # upload_view
            gr.update(visible=False),  # graph_view
            gr.update(visible=True),   # library_view
        )

    upload_tab_btn.click(
        fn=show_upload,
        outputs=[upload_view, graph_view, library_view]
    )

    graph_tab_btn.click(
        fn=show_graph,
        outputs=[upload_view, graph_view, library_view]
    )

    library_tab_btn.click(
        fn=show_library,
        outputs=[upload_view, graph_view, library_view]
    )

    # Auto-check backend status on load
    app.load(
        fn=check_status,
        outputs=[status_text],
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG-Anything Frontend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind to")
    parser.add_argument("--share", action="store_true", help="Create public link")
    args = parser.parse_args()
    
    print(f"Starting RAG-Anything frontend on {args.host}:{args.port}")
    print(f"Backend URL: {BACKEND_URL}")
    
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )

