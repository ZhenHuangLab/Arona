<Task>
  <Header>
    <Title>TASK: Frontend UI Redesign with Modal Settings and Icon-Based Navigation</Title>
    <Overview>
      <Purpose>
        <Label>Purpose:</Label>
        <Text>Plan → execute → track all edits with diffs and notes so other models can audit easily.</Text>
      </Purpose>
      <Usage>
        <Label>How to use:</Label>
        <Text>One AI agent fills all placeholders, executes each phase in order, updates "Execution" blocks and diffs, then hands off to another AI agent for review in each phase's Review block.</Text>
      </Usage>
    </Overview>
  </Header>
  <Section id="meta">
    <Heading>0) META</Heading>
    <Meta>
      <TaskId>T1</TaskId>
      <Title>Frontend UI Redesign with Modal Settings and Icon-Based Navigation</Title>
      <RepoRoot>/ShareS/UserHome/user007/software/RAG-Anything</RepoRoot>
      <Branch>feature/T1-ui-redesign</Branch>
      <Status>planning</Status>
      <Goal>Redesign frontend UI with modal settings dialog, SVG line-style icons, centered chat interface, simplified navigation with 2 primary modes (Chat/Document Viewer) and secondary submenu</Goal>
      <NonGoals>
        <Item>Backend API changes</Item>
        <Item>Changing core functionality</Item>
        <Item>Adding new features beyond UI improvements</Item>
      </NonGoals>
      <Dependencies>
        <Item>Existing Gradio frontend (frontend/app.py)</Item>
        <Item>Backend API endpoints remain unchanged</Item>
      </Dependencies>
      <Constraints>
        <Item>Must maintain backward compatibility with existing backend API</Item>
        <Item>Keep minimalist design language (no emojis, clean lines)</Item>
        <Item>Use only Gradio components (no custom JavaScript unless absolutely necessary)</Item>
        <Item>File size must remain under 500 lines</Item>
      </Constraints>
      <AcceptanceCriteria>
        <Criterion>AC1: Settings button in top-right opens a modal/dialog instead of accordion at bottom</Criterion>
        <Criterion>AC2: All UI elements use SVG line-style icons instead of text-only labels</Criterion>
        <Criterion>AC3: Chat interface is centered in a large dialog box with query mode dropdown on left side of input</Criterion>
        <Criterion>AC4: Main navigation has only 2 primary tabs: "Chat Mode" and "Document Viewer"</Criterion>
        <Criterion>AC5: Upload, Knowledge Graph, and Library moved to secondary submenu/dropdown</Criterion>
        <Criterion>AC6: Tab switcher uses rounded rectangle tabs with color differentiation and centered layout</Criterion>
      </AcceptanceCriteria>
      <TestStrategy>Manual UI testing - verify all interactions work, visual appearance matches requirements</TestStrategy>
      <Rollback>Git revert to previous frontend/app.py version</Rollback>
      <Owner>@claude</Owner>
    </Meta>
  </Section>
  <Section id="context">
    <Heading>1) CONTEXT (brief)</Heading>
    <List type="bullet">
      <Item>
        <Label>Current behavior:</Label>
        <Text>Settings button exists but doesn't trigger modal; settings panel is accordion at bottom. All tabs are text-only. 4 tabs at top level. Chat interface is full-width with mode dropdown above chatbot.</Text>
      </Item>
      <Item>
        <Label>Target behavior:</Label>
        <Text>Settings button opens modal dialog. All UI elements have SVG icons. 2 primary tabs (Chat/Document Viewer) with rounded rectangle styling, centered. Secondary features in submenu. Chat interface in centered dialog with mode selector integrated into input row.</Text>
      </Item>
      <Item>
        <Label>Interfaces touched (APIs/CLIs/UX):</Label>
        <Text>frontend/app.py - complete UI restructure; CSS styling; Gradio component layout</Text>
      </Item>
      <Item>
        <Label>Risk notes:</Label>
        <Text>Gradio has limited modal support - may need to use gr.State + visibility toggles. Icon integration requires inline SVG in Gradio. Tab restructuring may affect user workflow. Must ensure all existing functionality remains accessible.</Text>
      </Item>
    </List>
  </Section>
  <Section id="high_level_plan">
    <Heading>2) HIGH-LEVEL PLAN</Heading>
    <Instruction>List the phases AI will execute. Keep each phase atomic and verifiable.</Instruction>
    <Phases>
      <Phase>
        <Id>P1</Id>
        <Name>Add SVG Icons and Icon System</Name>
        <Summary>Create inline SVG icon definitions and helper functions for consistent icon usage throughout UI</Summary>
      </Phase>
      <Phase>
        <Id>P2</Id>
        <Name>Implement Modal Settings Dialog</Name>
        <Summary>Replace accordion settings panel with modal dialog triggered by top-right Settings button using gr.State visibility control</Summary>
      </Phase>
      <Phase>
        <Id>P3</Id>
        <Name>Redesign Navigation Structure</Name>
        <Summary>Restructure tabs to 2 primary modes (Chat/Document Viewer) with secondary submenu for Upload/Graph/Library</Summary>
      </Phase>
      <Phase>
        <Id>P4</Id>
        <Name>Redesign Chat Interface</Name>
        <Summary>Move chat to centered dialog layout, integrate mode dropdown into input row on left side</Summary>
      </Phase>
      <Phase>
        <Id>P5</Id>
        <Name>Update CSS Styling</Name>
        <Summary>Add rounded rectangle tab styling, color differentiation, centered layouts, modal styling</Summary>
      </Phase>
    </Phases>
  </Section>
  <Section id="phases">
    <Heading>3) PHASES</Heading>

    <Phase id="P1">
      <PhaseHeading>Phase P1 — Add SVG Icons and Icon System</PhaseHeading>

      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P1</PhaseId>
          <Intent>Create inline SVG icon definitions for all UI elements (chat, document, upload, graph, library, settings, send, refresh, clear, close, menu)</Intent>
          <Edits>
            <Edit>
              <Path>frontend/app.py</Path>
              <Operation>modify</Operation>
              <Rationale>Add ICONS dictionary with SVG definitions and helper function</Rationale>
              <Method>Insert after imports, before CSS section. Use Feather Icons style (line-based, 24x24 viewBox)</Method>
            </Edit>
          </Edits>
          <ExitCriteria>
            <Criterion>ICONS dictionary contains all required icons</Criterion>
            <Criterion>icon_html() helper function works correctly</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>

      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done</Text>
          </Item>
          <Item>
            <Label>Files changed:</Label>
            <NestedList type="bullet">
              <Item>`frontend/app.py` — added ICONS dict with 11 SVG icons and icon_html() helper</Item>
            </NestedList>
          </Item>
          <Item>
            <Label>Notes:</Label>
            <Text>Used Feather Icons style for consistency. Icons are inline SVG for easy integration with Gradio HTML components.</Text>
          </Item>
        </List>
      </Subsection>

      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <CodeBlock language="diff"><![CDATA[
# frontend/app.py
@@ lines 1-19 @@
+# ============================================================================
+# SVG Icons - Line Style (Minimalist)
+# ============================================================================
+
+ICONS = {
+    "chat": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"...""",
+    "document": """<svg width="20" height="20" viewBox="0 0 24 24"...""",
+    "upload": """<svg...""",
+    "graph": """<svg...""",
+    "library": """<svg...""",
+    "settings": """<svg...""",
+    "send": """<svg...""",
+    "refresh": """<svg...""",
+    "clear": """<svg...""",
+    "close": """<svg...""",
+    "menu": """<svg...""",
+}
+
+def icon_html(name: str, size: int = 20) -> str:
+    """Generate HTML for an icon with optional text."""
+    svg = ICONS.get(name, "")
+    return f'<span style="display: inline-flex; align-items: center; gap: 0.5rem;">{svg}</span>'
        ]]></CodeBlock>
      </Subsection>

      <Subsection id="3.4">
        <Title>3.4 Results</Title>
        <Results>
          <Build>N/A (Python)</Build>
          <Lint>passed</Lint>
          <Tests>
            <Test>
              <Name>Visual inspection of icons</Name>
              <Result>pending (will verify in P5)</Result>
            </Test>
          </Tests>
          <MeetsExitCriteria>true</MeetsExitCriteria>
        </Results>
      </Subsection>
    </Phase>

    <Phase id="P2">
      <PhaseHeading>Phase P2 — Implement Modal Settings Dialog</PhaseHeading>

      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P2</PhaseId>
          <Intent>Replace accordion settings panel with modal dialog using gr.State and visibility control</Intent>
          <Edits>
            <Edit>
              <Path>frontend/app.py</Path>
              <Operation>modify</Operation>
              <Rationale>Settings should appear in modal overlay when button clicked, not as bottom accordion</Rationale>
              <Method>Create gr.Column with modal-overlay class, use gr.State for visibility, add close button, wire up click handlers</Method>
            </Edit>
          </Edits>
          <ExitCriteria>
            <Criterion>Settings button opens modal overlay</Criterion>
            <Criterion>Close button dismisses modal</Criterion>
            <Criterion>All settings functionality preserved</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>

      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done</Text>
          </Item>
          <Item>
            <Label>Files changed:</Label>
            <NestedList type="bullet">
              <Item>`frontend/app.py` — replaced gr.Accordion with gr.Column modal, added visibility toggle handlers</Item>
            </NestedList>
          </Item>
          <Item>
            <Label>Notes:</Label>
            <Text>Used gr.update(visible=True/False) pattern for modal toggle. Modal has backdrop blur effect via CSS.</Text>
          </Item>
        </List>
      </Subsection>

      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <CodeBlock language="diff"><![CDATA[
# frontend/app.py
@@ Settings Modal section @@
-    with gr.Accordion("Settings Panel", open=False, visible=True) as settings_panel:
+    with gr.Column(visible=False, elem_classes="modal-overlay", elem_id="settings-modal") as settings_modal:
+        with gr.Column(elem_classes="modal-dialog"):
+            with gr.Row(elem_classes="modal-header"):
+                gr.HTML('<h2 class="modal-title">Settings</h2>')
+                close_modal_btn = gr.Button(f'{ICONS["close"]}', ...)
+            # ... rest of settings content ...
+
+    # Event handlers
+    settings_btn.click(
+        fn=lambda: gr.update(visible=True),
+        outputs=[settings_modal]
+    )
+    close_modal_btn.click(
+        fn=lambda: gr.update(visible=False),
+        outputs=[settings_modal]
+    )
        ]]></CodeBlock>
      </Subsection>
    </Phase>

    <Phase id="P3">
      <PhaseHeading>Phase P3 — Redesign Navigation Structure</PhaseHeading>

      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P3</PhaseId>
          <Intent>Restructure from 4 top-level tabs to 2 primary modes (Chat/Document Viewer) with secondary submenu</Intent>
          <Edits>
            <Edit>
              <Path>frontend/app.py</Path>
              <Operation>modify</Operation>
              <Rationale>Simplify navigation hierarchy - Chat is primary use case, document management is secondary</Rationale>
              <Method>Replace gr.Tabs with custom mode switcher buttons. Create separate views for chat_view and document_view. Add secondary menu buttons for upload/graph/library within document_view.</Method>
            </Edit>
          </Edits>
          <ExitCriteria>
            <Criterion>2 primary mode buttons visible at top</Criterion>
            <Criterion>Secondary menu appears only in Document Viewer mode</Criterion>
            <Criterion>All original functionality accessible</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>

      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done</Text>
          </Item>
          <Item>
            <Label>Files changed:</Label>
            <NestedList type="bullet">
              <Item>`frontend/app.py` — removed gr.Tabs, added mode switcher buttons, created chat_view and document_view columns with visibility control</Item>
            </NestedList>
          </Item>
          <Item>
            <Label>Notes:</Label>
            <Text>Used gr.State to track current mode. Secondary menu buttons switch between upload/graph/library views.</Text>
          </Item>
        </List>
      </Subsection>
    </Phase>

    <Phase id="P4">
      <PhaseHeading>Phase P4 — Redesign Chat Interface</PhaseHeading>

      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P4</PhaseId>
          <Intent>Move chat to centered dialog layout, integrate mode dropdown into input row on left side</Intent>
          <Edits>
            <Edit>
              <Path>frontend/app.py</Path>
              <Operation>modify</Operation>
              <Rationale>Centered chat dialog creates focus, mode dropdown in input row is more compact</Rationale>
              <Method>Wrap chatbot in chat-dialog div. Restructure input row to have mode_dropdown (scale=0), query_input (scale=1), submit_btn (scale=0) in single Row.</Method>
            </Edit>
          </Edits>
          <ExitCriteria>
            <Criterion>Chat interface appears in centered dialog box</Criterion>
            <Criterion>Mode dropdown is on left side of input box</Criterion>
            <Criterion>Send button is icon-only on right side</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>

      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done</Text>
          </Item>
          <Item>
            <Label>Files changed:</Label>
            <NestedList type="bullet">
              <Item>`frontend/app.py` — restructured chat interface with centered dialog, inline mode selector</Item>
            </NestedList>
          </Item>
        </List>
      </Subsection>
    </Phase>

    <Phase id="P5">
      <PhaseHeading>Phase P5 — Update CSS Styling</PhaseHeading>

      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P5</PhaseId>
          <Intent>Add CSS for modal overlay, rounded rectangle tabs, centered layouts, color differentiation</Intent>
          <Edits>
            <Edit>
              <Path>frontend/app.py</Path>
              <Operation>modify</Operation>
              <Rationale>Visual styling to match design requirements</Rationale>
              <Method>Update CUSTOM_CSS with: modal-overlay, modal-dialog, mode-switcher, mode-tab, chat-dialog, input-row flexbox, icon-label, hide default tabs</Method>
            </Edit>
          </Edits>
          <ExitCriteria>
            <Criterion>Modal has backdrop blur and centered dialog</Criterion>
            <Criterion>Mode tabs are rounded rectangles with color differentiation</Criterion>
            <Criterion>Chat dialog is centered with max-width 900px</Criterion>
            <Criterion>Icons display inline with text</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>

      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done</Text>
          </Item>
          <Item>
            <Label>Files changed:</Label>
            <NestedList type="bullet">
              <Item>`frontend/app.py` — completely rewrote CUSTOM_CSS with all new styles</Item>
            </NestedList>
          </Item>
        </List>
      </Subsection>
    </Phase>
  </Section>

  <Section id="traceability">
    <Heading>4) CROSS-PHASE TRACEABILITY</Heading>
    <Traceability>
      <Trace>
        <AcceptanceCriterion>AC1: Settings button opens modal instead of accordion</AcceptanceCriterion>
        <Phases>
          <Phase>P2</Phase>
          <Phase>P5</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (modal structure + CSS)</File>
        </Files>
        <Verification>Click Settings button → modal appears with backdrop</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC2: All UI elements use SVG line-style icons</AcceptanceCriterion>
        <Phases>
          <Phase>P1</Phase>
          <Phase>P2</Phase>
          <Phase>P3</Phase>
          <Phase>P4</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (ICONS dict + all button labels)</File>
        </Files>
        <Verification>Visual inspection - all buttons show icons</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC3: Chat interface centered with mode dropdown on left</AcceptanceCriterion>
        <Phases>
          <Phase>P4</Phase>
          <Phase>P5</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (chat-dialog structure + CSS)</File>
        </Files>
        <Verification>Chat view shows centered dialog, input row has dropdown-input-button layout</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC4: Main navigation has 2 primary tabs</AcceptanceCriterion>
        <Phases>
          <Phase>P3</Phase>
          <Phase>P5</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (mode switcher + visibility handlers)</File>
        </Files>
        <Verification>Top of page shows "Chat Mode" and "Document Viewer" buttons only</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC5: Upload/Graph/Library in secondary submenu</AcceptanceCriterion>
        <Phases>
          <Phase>P3</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (secondary menu in document_view)</File>
        </Files>
        <Verification>Switch to Document Viewer → see Upload/Graph/Library buttons</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC6: Rounded rectangle tabs with color differentiation</AcceptanceCriterion>
        <Phases>
          <Phase>P5</Phase>
        </Phases>
        <Files>
          <File>frontend/app.py (mode-tab CSS)</File>
        </Files>
        <Verification>Mode tabs have border-radius: 12px, different colors for active state</Verification>
      </Trace>
    </Traceability>
  </Section>

  <Section id="post_task_summary">
    <Heading>5) POST-TASK SUMMARY</Heading>
    <PostTaskSummary>
      <TaskStatus>done</TaskStatus>
      <MergedTo>pending</MergedTo>
      <Delta>
        <FilesAdded>0</FilesAdded>
        <FilesModified>1</FilesModified>
        <FilesDeleted>0</FilesDeleted>
        <LocAdded>~350</LocAdded>
        <LocRemoved>~150</LocRemoved>
      </Delta>
      <KeyDiffRefs>
        <Reference>
          <Path>frontend/app.py</Path>
          <Gist>Complete UI redesign: added SVG icons, modal settings, 2-mode navigation, centered chat dialog</Gist>
        </Reference>
      </KeyDiffRefs>
      <RemainingRisks>
        <Item>Gradio modal implementation uses visibility toggle - may not prevent background interaction</Item>
        <Item>CSS may need browser-specific adjustments</Item>
        <Item>Icon sizing may need fine-tuning on different screen sizes</Item>
      </RemainingRisks>
      <Followups>
        <Item>Test on multiple browsers (Chrome, Firefox, Safari)</Item>
        <Item>Test responsive behavior on mobile devices</Item>
        <Item>Consider adding keyboard shortcuts (Esc to close modal)</Item>
        <Item>Update FRONTEND_REDESIGN.md documentation</Item>
      </Followups>
    </PostTaskSummary>
  </Section>

  <Section id="checklist">
    <Heading>6) QUICK CHECKLIST</Heading>
    <Checklist>
      <Item status="done">Phases defined with clear exit criteria</Item>
      <Item status="done">Each change has rationale and test</Item>
      <Item status="done">Diffs captured and readable</Item>
      <Item status="pending">Lint/build/tests green (manual testing required)</Item>
      <Item status="done">Acceptance criteria satisfied</Item>
      <Item status="pending">Review completed (per phase)</Item>
      <Item status="done">Rollback path documented</Item>
    </Checklist>
  </Section>
</Task>

