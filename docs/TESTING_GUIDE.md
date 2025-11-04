# Frontend Redesign Testing Guide

## Overview

This guide provides comprehensive testing procedures for the redesigned RAG-Anything frontend. Follow these steps to verify all functionality works correctly.

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:7860`
3. At least one document uploaded and processed
4. Modern browser (Chrome 120+, Firefox 120+, Safari 17+, or Edge 120+)

## Starting the Application

```bash
# Terminal 1: Start Backend
cd backend
python main.py

# Terminal 2: Start Frontend
cd frontend
python app.py

# Or use scripts
bash scripts/start_backend.sh
bash scripts/start_frontend.sh
```

## Test Suite

### 1. Initial Load Test

**Objective**: Verify app loads correctly with default state

**Steps**:
1. Open browser to `http://localhost:7860`
2. Wait for page to load

**Expected Results**:
- ✅ Page loads without errors
- ✅ Header shows "RAG-Anything" on left
- ✅ Settings button (⚙️ icon) visible on right
- ✅ Two mode tabs visible: "💬 Chat Mode" and "📄 Document Viewer"
- ✅ Chat Mode tab is active (green background)
- ✅ Centered chat dialog is visible
- ✅ Mode dropdown shows "Hybrid"
- ✅ Input box shows placeholder text
- ✅ Send button shows ➤ icon
- ✅ Clear Conversation button visible
- ✅ No console errors

**Browser Console Check**:
```javascript
// Should see no errors
console.log("No errors expected");
```

---

### 2. Settings Modal Test

**Objective**: Verify settings modal opens, displays content, and closes

**Steps**:
1. Click ⚙️ Settings button in top-right
2. Observe modal appearance
3. Check modal content
4. Click ✕ close button
5. Click Settings button again
6. Click outside modal (on backdrop)

**Expected Results**:
- ✅ Modal overlay appears with backdrop blur
- ✅ Modal dialog is centered on screen
- ✅ Modal title shows "Settings"
- ✅ Close button (✕) visible in header
- ✅ Backend Status section shows status
- ✅ Current Configuration section visible
- ✅ Hot-Reload Configuration section visible
- ✅ Clicking ✕ closes modal
- ✅ Clicking backdrop closes modal (future enhancement)
- ✅ Modal content is scrollable if needed

**Visual Check**:
- Modal has rounded corners (12px)
- Backdrop has blur effect
- Modal has shadow
- Content is readable

---

### 3. Backend Status Test

**Objective**: Verify backend status check works

**Steps**:
1. Open Settings modal
2. Check Backend Status field
3. Click 🔄 Refresh button
4. Observe status update

**Expected Results**:
- ✅ Status shows "Backend healthy (v...)" or error message
- ✅ Refresh button updates status
- ✅ Status reflects actual backend state
- ✅ Version number displayed if backend is healthy

**Test with Backend Down**:
1. Stop backend server
2. Click Refresh in Settings
3. Should show "Cannot connect to backend at http://localhost:8000"

---

### 4. Configuration Viewer Test

**Objective**: Verify configuration loading works

**Steps**:
1. Open Settings modal
2. Click "Load Current Config" button
3. Observe configuration display

**Expected Results**:
- ✅ Configuration loads in JSON format
- ✅ JSON is properly formatted and readable
- ✅ Shows backend, models, storage, processing config
- ✅ No errors in console

---

### 5. Configuration Reload Test

**Objective**: Verify hot-reload functionality

**Steps**:
1. Open Settings modal
2. Verify config files input shows ".env.backend"
3. Click "Reload Configuration" button
4. Observe reload status

**Expected Results**:
- ✅ Status shows "Status: success"
- ✅ Message indicates files reloaded
- ✅ Reloaded files list shown
- ✅ No errors

**Note**: Actual config changes require backend restart for full effect

---

### 6. Mode Switching Test

**Objective**: Verify switching between Chat and Document Viewer modes

**Steps**:
1. Start in Chat Mode (default)
2. Click "📄 Document Viewer" tab
3. Observe view change
4. Click "💬 Chat Mode" tab
5. Observe view change back

**Expected Results**:
- ✅ Chat Mode tab starts with green background
- ✅ Clicking Document Viewer:
  - Document Viewer tab turns green
  - Chat Mode tab turns white
  - Chat dialog disappears
  - Secondary menu appears (Upload | Graph | Library)
  - Upload view is shown by default
- ✅ Clicking Chat Mode:
  - Chat Mode tab turns green
  - Document Viewer tab turns white
  - Secondary menu disappears
  - Chat dialog reappears
- ✅ Transitions are smooth
- ✅ No console errors

---

### 7. Chat Interface Test

**Objective**: Verify chat functionality works correctly

**Steps**:
1. Ensure you're in Chat Mode
2. Select "Hybrid" from mode dropdown
3. Type "What is this document about?" in input box
4. Click ➤ Send button (or press Enter)
5. Wait for response
6. Send another message
7. Click "🗑️ Clear Conversation"

**Expected Results**:
- ✅ Mode dropdown shows all options (Hybrid, Local, Global, Naive)
- ✅ Input box accepts text
- ✅ Send button is clickable
- ✅ Pressing Enter sends message
- ✅ User message appears in chat
- ✅ Bot response appears after processing
- ✅ Multiple messages stack correctly
- ✅ Clear Conversation empties chat history
- ✅ Input box is cleared after sending

**Visual Check**:
- Chat dialog is centered (max-width 900px)
- Mode dropdown is on left side of input
- Input box takes most of the width
- Send button is on right side
- Messages are properly formatted

---

### 8. Secondary Menu Test

**Objective**: Verify secondary menu navigation in Document Viewer

**Steps**:
1. Switch to Document Viewer mode
2. Click "⬆️ Upload" button
3. Click "🕸️ Knowledge Graph" button
4. Click "📚 Library" button
5. Click "⬆️ Upload" again

**Expected Results**:
- ✅ Upload view shows file selector and upload button
- ✅ Knowledge Graph view shows stats and graph data
- ✅ Library view shows processed documents list
- ✅ Switching between views is instant
- ✅ Only one view visible at a time
- ✅ No console errors

---

### 9. Document Upload Test

**Objective**: Verify document upload functionality

**Steps**:
1. Switch to Document Viewer mode
2. Ensure Upload view is active
3. Click "Select Document"
4. Choose a PDF file
5. Click "⬆️ Upload & Process"
6. Wait for processing

**Expected Results**:
- ✅ File selector accepts supported formats (.pdf, .docx, etc.)
- ✅ Upload button is clickable after file selected
- ✅ Processing status updates in real-time
- ✅ Success message shows file path
- ✅ Or error message if processing fails
- ✅ No console errors

**Supported Formats**:
- PDF, DOCX, PPTX, XLSX, TXT, MD, HTML

---

### 10. Knowledge Graph Test

**Objective**: Verify graph statistics and data loading

**Steps**:
1. Switch to Document Viewer mode
2. Click "🕸️ Knowledge Graph"
3. Click "🔄 Refresh Stats"
4. Observe statistics
5. Click "🕸️ Load Graph Data"
6. Observe graph data

**Expected Results**:
- ✅ Refresh Stats loads graph statistics (JSON)
- ✅ Statistics show entity count, relation count, etc.
- ✅ Load Graph Data loads sample graph data (JSON)
- ✅ Graph data shows nodes and edges
- ✅ No errors if no documents processed
- ✅ Proper error messages if backend unavailable

---

### 11. Document Library Test

**Objective**: Verify processed documents list

**Steps**:
1. Switch to Document Viewer mode
2. Click "📚 Library"
3. Observe document list
4. Click "🔄 Refresh List"
5. Observe updated list

**Expected Results**:
- ✅ Library shows list of processed documents
- ✅ Each document shows: file path, status, chunks
- ✅ Total count displayed
- ✅ Refresh List updates the list
- ✅ Message shown if no documents processed
- ✅ No console errors

---

### 12. Icon Display Test

**Objective**: Verify all icons display correctly

**Icons to Check**:
- ✅ ⚙️ Settings (header)
- ✅ 💬 Chat Mode (tab)
- ✅ 📄 Document Viewer (tab)
- ✅ ⬆️ Upload (secondary menu + button)
- ✅ 🕸️ Knowledge Graph (secondary menu + button)
- ✅ 📚 Library (secondary menu)
- ✅ ➤ Send (chat input)
- ✅ 🗑️ Clear (clear conversation)
- ✅ 🔄 Refresh (various buttons)
- ✅ ✕ Close (modal)

**Visual Check**:
- All icons are visible
- Icons are properly aligned with text
- Icons are consistent size (20x20px)
- Icons use line style (not filled)
- Icons have proper color (inherit from text)

---

### 13. Responsive Layout Test

**Objective**: Verify layout adapts to different screen sizes

**Steps**:
1. Open browser dev tools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Test different screen sizes:
   - Desktop: 1920x1080
   - Laptop: 1366x768
   - Tablet: 768x1024
   - Mobile: 375x667

**Expected Results**:
- ✅ Chat dialog scales appropriately
- ✅ Mode tabs remain accessible
- ✅ Modal fits on screen
- ✅ Text remains readable
- ✅ Buttons remain clickable
- ✅ No horizontal scrolling (except modal content)

**Known Issues**:
- Mobile optimization is pending
- Some elements may need adjustment on small screens

---

### 14. Browser Compatibility Test

**Objective**: Verify app works across different browsers

**Browsers to Test**:
1. Chrome 120+
2. Firefox 120+
3. Safari 17+
4. Edge 120+

**For Each Browser**:
- ✅ Page loads correctly
- ✅ Icons display properly
- ✅ Modal backdrop blur works
- ✅ Rounded corners render correctly
- ✅ Colors match design spec
- ✅ All interactions work
- ✅ No console errors

**Known Issues**:
- Backdrop blur may not work in older browsers
- Some CSS features may degrade gracefully

---

### 15. Performance Test

**Objective**: Verify app performs well

**Metrics to Check**:
1. Initial page load time: < 2 seconds
2. Modal open/close: < 100ms
3. Mode switching: < 100ms
4. Chat message send: < 5 seconds (depends on backend)
5. Document upload: Varies by file size

**Tools**:
- Browser DevTools > Network tab
- Browser DevTools > Performance tab
- Lighthouse audit

**Expected Results**:
- ✅ No memory leaks
- ✅ No excessive re-renders
- ✅ Smooth animations
- ✅ Responsive interactions

---

## Regression Testing

### Verify Existing Functionality

**Chat Features**:
- ✅ All query modes work (Hybrid, Local, Global, Naive)
- ✅ Conversation history persists during session
- ✅ Clear conversation works
- ✅ Enter key sends message

**Document Features**:
- ✅ File upload works for all supported formats
- ✅ Processing status updates correctly
- ✅ Error messages display properly

**Graph Features**:
- ✅ Statistics load correctly
- ✅ Graph data loads correctly
- ✅ JSON formatting is readable

**Library Features**:
- ✅ Document list loads
- ✅ Metadata displays correctly
- ✅ Refresh works

**Settings Features**:
- ✅ Backend status check works
- ✅ Configuration viewer works
- ✅ Hot-reload works

---

## Bug Reporting Template

If you find a bug, report it with this information:

```markdown
**Bug Title**: [Short description]

**Severity**: Critical / High / Medium / Low

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happens]

**Screenshots**:
[Attach screenshots if applicable]

**Browser**:
- Browser: [Chrome/Firefox/Safari/Edge]
- Version: [120+]
- OS: [Windows/Mac/Linux]

**Console Errors**:
```
[Paste any console errors]
```

**Additional Context**:
[Any other relevant information]
```

---

## Test Results Checklist

### Functional Tests
- [ ] Initial load works
- [ ] Settings modal opens/closes
- [ ] Backend status check works
- [ ] Configuration viewer works
- [ ] Configuration reload works
- [ ] Mode switching works
- [ ] Chat interface works
- [ ] Secondary menu works
- [ ] Document upload works
- [ ] Knowledge graph works
- [ ] Document library works

### Visual Tests
- [ ] All icons display correctly
- [ ] Tabs are rounded rectangles
- [ ] Active tab has green background
- [ ] Chat dialog is centered
- [ ] Modal has backdrop blur
- [ ] Colors match design spec
- [ ] Spacing is consistent

### Browser Tests
- [ ] Chrome 120+
- [ ] Firefox 120+
- [ ] Safari 17+
- [ ] Edge 120+

### Performance Tests
- [ ] Page loads quickly
- [ ] Interactions are responsive
- [ ] No memory leaks
- [ ] No console errors

---

## Sign-off

**Tester**: ___________________  
**Date**: ___________________  
**Status**: ☐ Pass ☐ Fail ☐ Pass with Issues  
**Notes**: ___________________

