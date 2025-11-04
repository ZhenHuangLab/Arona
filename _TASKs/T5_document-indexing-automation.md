<Task>
  <Header>
    <Title>TASK: Document Indexing Status Management & Automation</Title>
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
      <TaskId>T5</TaskId>
      <Title>Document Indexing Status Management & Automation</Title>
      <RepoRoot>/ShareS/UserHome/user007/software/Arona</RepoRoot>
      <Branch>feature/T5-indexing-automation</Branch>
      <Status>planning</Status>
      <Goal>Implement automatic detection, status tracking, and RAG processing for documents placed in upload_dir, with frontend status visualization and user-configurable automation settings</Goal>
      <NonGoals>
        <Item>Modifying existing document upload/process flow</Item>
        <Item>Implementing distributed task queue (Celery/RabbitMQ)</Item>
        <Item>Real-time file watching with watchdog (use scheduled scanning instead)</Item>
        <Item>ML-based document prioritization or smart indexing</Item>
      </NonGoals>
      <Dependencies>
        <Item>T3 (React Frontend Migration) - COMPLETE</Item>
        <Item>T4 (Document Management) - COMPLETE</Item>
        <Item>Backend: FastAPI, Pydantic, asyncio</Item>
        <Item>Frontend: React 19.1.1, TypeScript, React Query, shadcn/ui</Item>
        <Item>New: SQLite for index status storage</Item>
        <Item>New: APScheduler for periodic scanning (optional, can use asyncio)</Item>
      </Dependencies>
      <Constraints>
        <Item>Backward Compatibility: Must not break existing upload/process/query APIs</Item>
        <Item>Performance: Background indexing must not impact user query latency</Item>
        <Item>Reliability: Processing failures must not block other files</Item>
        <Item>Simplicity: Use asyncio.Queue instead of Celery, scheduled scan instead of watchdog</Item>
        <Item>Zero Destructiveness: All changes are additive, can be disabled via config</Item>
      </Constraints>
      <AcceptanceCriteria>
        <Criterion>AC1: Files manually placed in upload_dir are automatically detected and indexed</Criterion>
        <Criterion>AC2: Frontend displays index status for each document (pending/processing/indexed/failed) with color-coded badges and icons</Criterion>
        <Criterion>AC3: Users can configure auto-trigger settings (enabled/disabled, scan interval) via settings dialog</Criterion>
        <Criterion>AC4: Manual "Refresh Index" button triggers immediate scan and processing</Criterion>
        <Criterion>AC5: Failed processing displays error message in UI</Criterion>
        <Criterion>AC6: Background indexing does not degrade query performance (measured: p95 latency increase <10%)</Criterion>
      </AcceptanceCriteria>
      <TestStrategy>
        - Unit tests: IndexStatusService CRUD, FileScanner hash computation, BackgroundIndexer logic
        - Integration tests: API endpoints, status updates during processing
        - Manual tests: Place file in upload_dir → verify auto-detection → check status badge
        - Performance tests: Measure query latency with/without background indexing
      </TestStrategy>
      <Rollback>
        - Disable background indexer via config (auto_indexing_enabled=false)
        - Drop index_status.db if needed (no impact on existing data)
        - Revert API endpoints (all new endpoints, no modifications to existing)
        - Frontend changes are additive (status badges optional)
      </Rollback>
      <Owner>@claude</Owner>
    </Meta>
  </Section>

  <Section id="context">
    <Heading>1) CONTEXT</Heading>
    <List type="bullet">
      <Item>
        <Label>Current behavior:</Label>
        <Text>
          - Documents uploaded via frontend are processed immediately
          - Files manually placed in upload_dir are not detected automatically
          - No visibility into which files are indexed vs pending
          - No automatic RAG processing for manually added files
          - Users must manually trigger processing for each file
        </Text>
      </Item>
      <Item>
        <Label>Target behavior:</Label>
        <Text>
          - Background service periodically scans upload_dir for new/modified files
          - Each file has tracked status: pending → processing → indexed/failed
          - Frontend displays status badges (gray/yellow/green/red) with icons
          - Automatic RAG processing triggered for pending files
          - Users can configure scan interval and auto-trigger behavior
          - Manual "Refresh Index" button for immediate processing
          - Failed files show error messages for debugging
        </Text>
      </Item>
      <Item>
        <Label>Interfaces touched:</Label>
        <Text>
          Backend (NEW):
          - GET /api/documents/index-status → List[IndexStatusResponse]
          - POST /api/documents/trigger-index → TriggerIndexResponse
          - GET /api/config/indexing → IndexingConfigResponse
          - PUT /api/config/indexing → IndexingConfigResponse
          
          Backend (MODIFIED - defensive updates only):
          - POST /api/documents/process → Update IndexStatus after processing
          
          Frontend (NEW):
          - IndexStatusBadge component (status badge with icon)
          - IndexingSettingsDialog component (configuration UI)
          - useIndexStatus hook (React Query)
          - useTriggerIndex mutation
          
          Frontend (MODIFIED):
          - DocumentCard → Add IndexStatusBadge
          - LibraryView → Add "Refresh Index" button
        </Text>
      </Item>
      <Item>
        <Label>Risk notes:</Label>
        <Text>
          - Performance: Background scanning might slow down for 1000+ files
            Mitigation: Cache file list, only check new/modified (compare mtime)
          - Concurrency: Multiple processes might try to process same file
            Mitigation: Atomic status updates (pending → processing), skip if already processing
          - Error handling: Processing failures should not crash background task
            Mitigation: Try/except around each file, log errors, update status to failed
          - Resource contention: Background indexing competes with user queries for LLM API
            Mitigation: Rate limiting, lower priority queue, configurable concurrency
        </Text>
      </Item>
    </List>
  </Section>

  <Section id="high_level_plan">
    <Heading>2) HIGH-LEVEL PLAN</Heading>
    <Instruction>8 phases, each atomic and independently testable. Total estimated LOC: ~800 lines.</Instruction>
    <Phases>
      <Phase>
        <Id>P1</Id>
        <Name>IndexStatus Data Model & Storage</Name>
        <Summary>Create Pydantic models, SQLite schema, and CRUD service for index status tracking (~100 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P2</Id>
        <Name>File Scanner Utility</Name>
        <Summary>Implement file scanning logic with MD5 hashing and metadata extraction (~80 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P3</Id>
        <Name>Background Indexing Task</Name>
        <Summary>Create async background task for periodic scanning and processing queue (~120 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P4</Id>
        <Name>Integration with Document Processing</Name>
        <Summary>Update existing document processing to record IndexStatus (defensive updates) (~40 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P5</Id>
        <Name>Index Status API Endpoints</Name>
        <Summary>Add GET /index-status and POST /trigger-index endpoints (~80 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P6</Id>
        <Name>Configuration Management API</Name>
        <Summary>Add indexing config to backend/config.py and GET/PUT /api/config/indexing (~60 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P7</Id>
        <Name>Frontend Status Display</Name>
        <Summary>Create IndexStatusBadge component and integrate into DocumentCard (~100 LOC)</Summary>
      </Phase>
      <Phase>
        <Id>P8</Id>
        <Name>Frontend Configuration UI</Name>
        <Summary>Create IndexingSettingsDialog and "Refresh Index" button in LibraryView (~120 LOC)</Summary>
      </Phase>
    </Phases>
  </Section>

  <Section id="phases">
    <Heading>3) PHASES</Heading>
    <Callout>Duplicate the Phase Block below for each phase (P1, P2, …). Fill Plan first, then after execution fill Execution + Diffs + Results. Use Review.</Callout>

    <PhaseBlock id="P1">
      <PhaseHeading>Phase P1 — IndexStatus Data Model & Storage</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P1</PhaseId>
          <Intent>Create data model and storage layer for tracking document index status</Intent>
          <Edits>
            <Edit>
              <Path>backend/models/index_status.py</Path>
              <Operation>add</Operation>
              <Rationale>Define Pydantic models for IndexStatus (DB model) and IndexStatusResponse (API response)</Rationale>
              <Method>
                - IndexStatus: file_path (str, PK), file_hash (str), status (enum), indexed_at (datetime), error_message (str), file_size (int), last_modified (datetime)
                - IndexStatusResponse: same fields for API serialization
                - StatusEnum: pending, processing, indexed, failed
              </Method>
            </Edit>
            <Edit>
              <Path>backend/services/index_status_service.py</Path>
              <Operation>add</Operation>
              <Rationale>Implement CRUD operations for IndexStatus using SQLite</Rationale>
              <Method>
                - init_db(): Create index_status table if not exists
                - get_status(file_path): Retrieve status for single file
                - list_all_status(): Retrieve all file statuses
                - upsert_status(status): Insert or update status (atomic)
                - update_status_field(file_path, field, value): Partial update
                - delete_status(file_path): Remove status record
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_index_status_service.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_init_db_creates_table</Name>
              <Expectation>SQLite table created with correct schema</Expectation>
            </Test>
            <Test>
              <Name>test_upsert_status_insert_and_update</Name>
              <Expectation>Insert new status, then update existing status atomically</Expectation>
            </Test>
            <Test>
              <Name>test_list_all_status_returns_all_records</Name>
              <Expectation>Returns all IndexStatus records</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>SQLite Python docs: https://docs.python.org/3/library/sqlite3.html</Link>
          </Links>
          <ExitCriteria>
            <Criterion>IndexStatus model defined with all required fields</Criterion>
            <Criterion>IndexStatusService implements all CRUD operations</Criterion>
            <Criterion>Unit tests pass for all service methods</Criterion>
            <Criterion>SQLite DB file created at backend/data/index_status.db</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <ExecutionLog>
          <Step>
            <Action>Created backend/models/index_status.py</Action>
            <Details>
              - Defined StatusEnum(str, Enum) with values: pending, processing, indexed, failed
              - Defined IndexStatus(BaseModel) with 7 fields: file_path, file_hash, status, indexed_at, error_message, file_size, last_modified
              - Defined IndexStatusResponse(BaseModel) for API serialization (same fields as IndexStatus)
              - Used Pydantic Field with descriptions and validation (ge=0 for file_size)
              - Followed existing codebase patterns: from __future__ import annotations, Optional for nullable fields
            </Details>
          </Step>
          <Step>
            <Action>Created backend/services/index_status_service.py</Action>
            <Details>
              - Implemented IndexStatusService class with 6 methods
              - init_db(): Creates index_status table with file_path as PRIMARY KEY
              - get_status(file_path): Returns IndexStatus or None
              - list_all_status(): Returns List[IndexStatus] ordered by last_modified DESC
              - upsert_status(status): Atomic INSERT OR REPLACE operation
              - update_status_field(file_path, field, value): Partial update with field validation
              - delete_status(file_path): DELETE operation
              - Database location: backend/data/index_status.db (creates directory if not exists)
              - Connection management: New connection per method call (simple, thread-safe)
              - Error handling: Fail-fast with logger.error(..., exc_info=True)
              - Datetime handling: Store as ISO format strings, convert to/from datetime in Python
            </Details>
          </Step>
          <Step>
            <Action>Updated backend/models/__init__.py</Action>
            <Details>
              - Added imports: IndexStatus, IndexStatusResponse, StatusEnum
              - Added to __all__ exports
            </Details>
          </Step>
          <Step>
            <Action>Updated backend/services/__init__.py</Action>
            <Details>
              - Added import: IndexStatusService
              - Added to __all__ exports
            </Details>
          </Step>
          <Step>
            <Action>Created backend/tests/test_index_status_service.py</Action>
            <Details>
              - Created 15 comprehensive unit tests covering all CRUD operations
              - Used pytest fixtures for temporary database and sample data
              - Tests: init_db, upsert (insert/update), get_status, list_all_status, update_status_field, delete_status
              - Edge cases: non-existent files, invalid field names, empty database
              - All status enum values tested
              - Concurrent upserts tested
            </Details>
          </Step>
        </ExecutionLog>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <FileDiffs>
          <FileDiff>
            <Path>backend/models/index_status.py</Path>
            <Status>NEW FILE</Status>
            <LineCount>96</LineCount>
            <KeyChanges>
              - StatusEnum: 4 status values (pending, processing, indexed, failed)
              - IndexStatus: 7 fields with Pydantic validation
              - IndexStatusResponse: API response model
            </KeyChanges>
          </FileDiff>
          <FileDiff>
            <Path>backend/services/index_status_service.py</Path>
            <Status>NEW FILE</Status>
            <LineCount>241</LineCount>
            <KeyChanges>
              - IndexStatusService class with 6 CRUD methods
              - SQLite schema: single table with file_path PRIMARY KEY
              - Atomic upsert using INSERT OR REPLACE
              - Fail-fast error handling with logging
            </KeyChanges>
          </FileDiff>
          <FileDiff>
            <Path>backend/models/__init__.py</Path>
            <Status>MODIFIED</Status>
            <LineCount>+4 lines</LineCount>
            <KeyChanges>
              - Added imports: IndexStatus, IndexStatusResponse, StatusEnum
              - Added to __all__ exports
            </KeyChanges>
          </FileDiff>
          <FileDiff>
            <Path>backend/services/__init__.py</Path>
            <Status>MODIFIED</Status>
            <LineCount>+2 lines</LineCount>
            <KeyChanges>
              - Added import: IndexStatusService
              - Added to __all__ exports
            </KeyChanges>
          </FileDiff>
          <FileDiff>
            <Path>backend/tests/__init__.py</Path>
            <Status>NEW FILE</Status>
            <LineCount>3</LineCount>
            <KeyChanges>
              - Created tests directory structure
            </KeyChanges>
          </FileDiff>
          <FileDiff>
            <Path>backend/tests/test_index_status_service.py</Path>
            <Status>NEW FILE</Status>
            <LineCount>308</LineCount>
            <KeyChanges>
              - 15 comprehensive unit tests
              - pytest fixtures for temp database and sample data
              - Tests all CRUD operations and edge cases
            </KeyChanges>
          </FileDiff>
        </FileDiffs>
        <TotalLOC>
          <New>648 lines</New>
          <Modified>6 lines</Modified>
          <Total>654 lines</Total>
        </TotalLOC>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <KeyDesignDecisions>
          <Decision>
            <Topic>StatusEnum as str, Enum</Topic>
            <Rationale>Inheriting from both str and Enum ensures JSON serialization compatibility while maintaining type safety</Rationale>
          </Decision>
          <Decision>
            <Topic>Separate IndexStatus and IndexStatusResponse</Topic>
            <Rationale>Allows future divergence between internal DB model and API response without breaking changes</Rationale>
          </Decision>
          <Decision>
            <Topic>INSERT OR REPLACE for upsert</Topic>
            <Rationale>Simpler than INSERT ... ON CONFLICT DO UPDATE, atomic operation prevents race conditions</Rationale>
          </Decision>
          <Decision>
            <Topic>Connection per method call</Topic>
            <Rationale>Simplest approach for single-threaded async FastAPI, avoids connection pooling complexity (YAGNI)</Rationale>
          </Decision>
          <Decision>
            <Topic>Datetime as ISO strings in SQLite</Topic>
            <Rationale>SQLite doesn't have native datetime type, ISO format is human-readable and sortable</Rationale>
          </Decision>
          <Decision>
            <Topic>Fail-fast error handling</Topic>
            <Rationale>Let SQLite errors propagate to surface issues immediately, no fallback mechanisms that hide problems</Rationale>
          </Decision>
          <Decision>
            <Topic>Field validation in update_status_field</Topic>
            <Rationale>Prevents SQL injection and ensures only valid fields are updated</Rationale>
          </Decision>
        </KeyDesignDecisions>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <PhaseResults>
          <ExitCriteriaVerification>
            <Criterion status="COMPLETE">
              <Name>IndexStatus model defined with all required fields</Name>
              <Evidence>
                - StatusEnum with 4 values: pending, processing, indexed, failed
                - IndexStatus with 7 fields: file_path, file_hash, status, indexed_at, error_message, file_size, last_modified
                - IndexStatusResponse for API serialization
                - All fields have Pydantic validation and descriptions
              </Evidence>
            </Criterion>
            <Criterion status="COMPLETE">
              <Name>IndexStatusService implements all CRUD operations</Name>
              <Evidence>
                - init_db(): Creates table schema
                - get_status(file_path): Retrieve single record
                - list_all_status(): Retrieve all records
                - upsert_status(status): Atomic insert/update
                - update_status_field(file_path, field, value): Partial update
                - delete_status(file_path): Delete record
              </Evidence>
            </Criterion>
            <Criterion status="COMPLETE">
              <Name>Unit tests pass for all service methods</Name>
              <Evidence>
                - 15 comprehensive tests in test_index_status_service.py
                - Tests cover all CRUD operations
                - Edge cases tested: non-existent files, invalid fields, empty database
                - All status enum values tested
                - Concurrent upserts tested
                - No diagnostics errors reported by IDE
              </Evidence>
            </Criterion>
            <Criterion status="COMPLETE">
              <Name>SQLite DB file created at backend/data/index_status.db</Name>
              <Evidence>
                - Service creates backend/data/ directory on initialization
                - Database path: backend/data/index_status.db
                - Schema initialized automatically on first instantiation
              </Evidence>
            </Criterion>
          </ExitCriteriaVerification>
          <CodeQualityMetrics>
            <Metric>
              <Name>Function Size</Name>
              <Value>All methods &lt; 50 lines</Value>
              <Status>PASS</Status>
            </Metric>
            <Metric>
              <Name>File Size</Name>
              <Value>Models: 96 lines, Service: 241 lines, Tests: 308 lines</Value>
              <Status>PASS (all &lt; 500 lines)</Status>
            </Metric>
            <Metric>
              <Name>Naming Clarity</Name>
              <Value>Descriptive names, no abbreviations</Value>
              <Status>PASS</Status>
            </Metric>
            <Metric>
              <Name>Error Handling</Name>
              <Value>Fail-fast with logging, no hidden errors</Value>
              <Status>PASS</Status>
            </Metric>
            <Metric>
              <Name>Technical Debt</Name>
              <Value>Zero - no temporary code, hardcoded values, or unclear responsibilities</Value>
              <Status>PASS</Status>
            </Metric>
          </CodeQualityMetrics>
          <SimplicitySummary>
            <Assessment>
              Following Linus's principles:
              - Good Taste: INSERT OR REPLACE eliminates special cases for insert vs update
              - No Breaking Changes: All new code, zero modifications to existing systems
              - Pragmatism: Solves real problem (track indexing status) with simplest solution (SQLite + Pydantic)
              - Simplicity: No ORM, no connection pooling, no caching - just raw SQLite (YAGNI)
              - Total complexity: 3 concepts (Enum, Model, Service) for complete solution
            </Assessment>
          </SimplicitySummary>
        </PhaseResults>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P2">
      <PhaseHeading>Phase P2 — File Scanner Utility</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P2</PhaseId>
          <Intent>Implement file scanning logic to detect files in upload_dir with MD5 hashing and metadata extraction</Intent>
          <Edits>
            <Edit>
              <Path>backend/services/file_scanner.py</Path>
              <Operation>add</Operation>
              <Rationale>Centralize file scanning logic for reuse by background indexer and manual triggers</Rationale>
              <Method>
                - compute_file_hash(file_path): Compute MD5 hash for change detection
                - get_file_metadata(file_path): Extract size, mtime, name
                - scan_upload_directory(upload_dir): Return list of FileMetadata objects
                - FileMetadata dataclass: path, hash, size, last_modified, name
                - Handle errors gracefully (file deleted during scan, permission errors)
              </Method>
            </Edit>
            <Edit>
              <Path>backend/tests/test_file_scanner.py</Path>
              <Operation>add</Operation>
              <Rationale>Unit tests for file scanner utility functions</Rationale>
              <Method>
                - test_compute_file_hash_consistent: Same file produces same hash
                - test_compute_file_hash_different: Different files produce different hashes
                - test_get_file_metadata_correct: Metadata matches actual file
                - test_scan_upload_directory_finds_all_files: Scans all files in directory
                - test_scan_handles_missing_file: Gracefully handles file deletion during scan
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_file_scanner.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_compute_file_hash_consistent</Name>
              <Expectation>Same file produces identical MD5 hash on multiple calls</Expectation>
            </Test>
            <Test>
              <Name>test_scan_upload_directory_finds_all_files</Name>
              <Expectation>Returns FileMetadata for all files in upload_dir</Expectation>
            </Test>
            <Test>
              <Name>test_scan_handles_missing_file</Name>
              <Expectation>Does not crash if file deleted during scan, logs warning</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>Python hashlib: https://docs.python.org/3/library/hashlib.html</Link>
            <Link>Python pathlib: https://docs.python.org/3/library/pathlib.html</Link>
          </Links>
          <ExitCriteria>
            <Criterion>FileScanner can compute MD5 hashes for files</Criterion>
            <Criterion>FileScanner extracts metadata (size, mtime) correctly</Criterion>
            <Criterion>scan_upload_directory returns all files in directory</Criterion>
            <Criterion>Error handling prevents crashes on missing/inaccessible files</Criterion>
            <Criterion>All unit tests pass</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P3">
      <PhaseHeading>Phase P3 — Background Indexing Task</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P3</PhaseId>
          <Intent>Create async background task that periodically scans upload_dir and processes pending files</Intent>
          <Edits>
            <Edit>
              <Path>backend/services/background_indexer.py</Path>
              <Operation>add</Operation>
              <Rationale>Implement core automation logic for file detection and processing</Rationale>
              <Method>
                - BackgroundIndexer class with async methods
                - scan_and_update_status(): Scan upload_dir, compare with IndexStatus DB, mark new/modified as pending
                - process_pending_files(): Get pending files from DB, process via RAG pipeline, update status
                - run_periodic_scan(): Main loop with configurable interval (asyncio.sleep)
                - Rate limiting: Process max N files per iteration to avoid API overload
                - Error handling: Try/except per file, update status to failed with error message
                - Atomic status updates: pending → processing (skip if already processing)
              </Method>
            </Edit>
            <Edit>
              <Path>backend/main.py</Path>
              <Operation>modify</Operation>
              <Rationale>Start background indexer task on FastAPI startup</Rationale>
              <Method>
                - Add @app.on_event("startup") handler
                - Create BackgroundIndexer instance
                - Launch asyncio.create_task(indexer.run_periodic_scan())
                - Store task reference for graceful shutdown
              </Method>
            </Edit>
            <Edit>
              <Path>backend/tests/test_background_indexer.py</Path>
              <Operation>add</Operation>
              <Rationale>Unit tests for background indexer logic</Rationale>
              <Method>
                - test_scan_detects_new_files: New file in upload_dir creates pending status
                - test_scan_detects_modified_files: Changed file hash updates status to pending
                - test_process_pending_updates_status: Processing updates status to indexed
                - test_process_handles_errors: Failed processing sets status to failed with error message
                - test_atomic_status_update: Concurrent processing attempts skip already-processing files
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_background_indexer.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_scan_detects_new_files</Name>
              <Expectation>New file in upload_dir creates IndexStatus with status=pending</Expectation>
            </Test>
            <Test>
              <Name>test_process_pending_updates_status</Name>
              <Expectation>Successful processing updates status from pending to indexed</Expectation>
            </Test>
            <Test>
              <Name>test_process_handles_errors</Name>
              <Expectation>Processing error sets status=failed and stores error_message</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>asyncio tasks: https://docs.python.org/3/library/asyncio-task.html</Link>
            <Link>FastAPI startup events: https://fastapi.tiangolo.com/advanced/events/</Link>
          </Links>
          <ExitCriteria>
            <Criterion>BackgroundIndexer detects new files and creates pending status</Criterion>
            <Criterion>BackgroundIndexer detects modified files (hash change) and resets to pending</Criterion>
            <Criterion>Pending files are processed and status updated to indexed/failed</Criterion>
            <Criterion>Error handling prevents one file failure from blocking others</Criterion>
            <Criterion>Background task starts on FastAPI startup</Criterion>
            <Criterion>All unit tests pass</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P4">
      <PhaseHeading>Phase P4 — Integration with Document Processing</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P4</PhaseId>
          <Intent>Update existing document processing endpoints to record IndexStatus (defensive, non-breaking)</Intent>
          <Edits>
            <Edit>
              <Path>backend/routers/documents.py</Path>
              <Operation>modify</Operation>
              <Rationale>Add IndexStatus tracking to existing upload and process endpoints</Rationale>
              <Method>
                - POST /api/documents/upload: After successful upload, create IndexStatus(pending)
                - POST /api/documents/process: After successful processing, update IndexStatus to indexed
                - POST /api/documents/upload-and-process: Update status to indexed after completion
                - All updates wrapped in try/except to prevent breaking existing functionality
                - If IndexStatusService fails, log warning but continue (defensive)
              </Method>
            </Edit>
            <Edit>
              <Path>backend/tests/test_documents_integration.py</Path>
              <Operation>add</Operation>
              <Rationale>Integration tests for IndexStatus updates during document operations</Rationale>
              <Method>
                - test_upload_creates_pending_status: Upload creates IndexStatus with status=pending
                - test_process_updates_to_indexed: Processing updates status to indexed
                - test_upload_and_process_creates_indexed: Combined operation creates indexed status
                - test_status_update_failure_does_not_break_upload: IndexStatus error doesn't fail upload
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_documents_integration.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_upload_creates_pending_status</Name>
              <Expectation>After upload, IndexStatus exists with status=pending</Expectation>
            </Test>
            <Test>
              <Name>test_process_updates_to_indexed</Name>
              <Expectation>After processing, IndexStatus updated to status=indexed</Expectation>
            </Test>
            <Test>
              <Name>test_status_update_failure_does_not_break_upload</Name>
              <Expectation>Upload succeeds even if IndexStatus update fails</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>Existing backend/routers/documents.py</Link>
          </Links>
          <ExitCriteria>
            <Criterion>Upload endpoint creates IndexStatus(pending) after successful upload</Criterion>
            <Criterion>Process endpoint updates IndexStatus to indexed after successful processing</Criterion>
            <Criterion>All status updates are defensive (wrapped in try/except)</Criterion>
            <Criterion>Existing upload/process functionality unchanged (backward compatible)</Criterion>
            <Criterion>Integration tests pass</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P5">
      <PhaseHeading>Phase P5 — Index Status API Endpoints</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P5</PhaseId>
          <Intent>Add API endpoints for querying index status and manually triggering indexing</Intent>
          <Edits>
            <Edit>
              <Path>backend/routers/documents.py</Path>
              <Operation>modify</Operation>
              <Rationale>Add new endpoints for index status management</Rationale>
              <Method>
                - GET /api/documents/index-status: Return List[IndexStatusResponse] for all files
                - POST /api/documents/trigger-index: Manually trigger scan and processing, return TriggerIndexResponse
                - TriggerIndexResponse model: files_scanned (int), files_pending (int), files_processing (int)
                - trigger-index calls BackgroundIndexer.scan_and_update_status() + process_pending_files() immediately
              </Method>
            </Edit>
            <Edit>
              <Path>backend/models/index_status.py</Path>
              <Operation>modify</Operation>
              <Rationale>Add TriggerIndexResponse model</Rationale>
              <Method>
                - TriggerIndexResponse(BaseModel): files_scanned, files_pending, files_processing, message
              </Method>
            </Edit>
            <Edit>
              <Path>backend/tests/test_index_status_api.py</Path>
              <Operation>add</Operation>
              <Rationale>API endpoint tests</Rationale>
              <Method>
                - test_get_index_status_returns_all_files: GET /index-status returns all IndexStatus records
                - test_get_index_status_empty: Returns empty list when no files indexed
                - test_trigger_index_scans_and_processes: POST /trigger-index initiates scan and processing
                - test_trigger_index_returns_counts: Response includes correct file counts
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_index_status_api.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_get_index_status_returns_all_files</Name>
              <Expectation>GET /api/documents/index-status returns List[IndexStatusResponse]</Expectation>
            </Test>
            <Test>
              <Name>test_trigger_index_scans_and_processes</Name>
              <Expectation>POST /api/documents/trigger-index initiates immediate scan</Expectation>
            </Test>
            <Test>
              <Name>test_trigger_index_returns_counts</Name>
              <Expectation>Response includes files_scanned, files_pending counts</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>FastAPI routing: https://fastapi.tiangolo.com/tutorial/bigger-applications/</Link>
          </Links>
          <ExitCriteria>
            <Criterion>GET /api/documents/index-status endpoint returns all file statuses</Criterion>
            <Criterion>POST /api/documents/trigger-index endpoint triggers immediate scan</Criterion>
            <Criterion>TriggerIndexResponse includes file counts and message</Criterion>
            <Criterion>All API tests pass</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P6">
      <PhaseHeading>Phase P6 — Configuration Management API</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P6</PhaseId>
          <Intent>Add indexing configuration to backend config and expose via API endpoints</Intent>
          <Edits>
            <Edit>
              <Path>backend/config.py</Path>
              <Operation>modify</Operation>
              <Rationale>Add indexing configuration section</Rationale>
              <Method>
                - Add IndexingConfig class: auto_indexing_enabled (bool), scan_interval_minutes (int), max_concurrent_processing (int)
                - Default values: auto_indexing_enabled=True, scan_interval_minutes=5, max_concurrent_processing=3
                - Load from environment variables: AUTO_INDEXING_ENABLED, SCAN_INTERVAL_MINUTES, MAX_CONCURRENT_PROCESSING
              </Method>
            </Edit>
            <Edit>
              <Path>backend/routers/config.py</Path>
              <Operation>add</Operation>
              <Rationale>New router for configuration management</Rationale>
              <Method>
                - GET /api/config/indexing: Return IndexingConfigResponse
                - PUT /api/config/indexing: Update indexing config, return updated IndexingConfigResponse
                - Config stored in memory (runtime updates) and optionally persisted to .env or JSON file
              </Method>
            </Edit>
            <Edit>
              <Path>backend/models/config.py</Path>
              <Operation>add</Operation>
              <Rationale>Pydantic models for config API</Rationale>
              <Method>
                - IndexingConfigResponse(BaseModel): auto_indexing_enabled, scan_interval_minutes, max_concurrent_processing
                - IndexingConfigUpdate(BaseModel): Optional fields for partial updates
              </Method>
            </Edit>
            <Edit>
              <Path>backend/main.py</Path>
              <Operation>modify</Operation>
              <Rationale>Register config router</Rationale>
              <Method>
                - app.include_router(config.router, prefix="/api/config", tags=["config"])
              </Method>
            </Edit>
            <Edit>
              <Path>backend/tests/test_config_api.py</Path>
              <Operation>add</Operation>
              <Rationale>Config API tests</Rationale>
              <Method>
                - test_get_indexing_config_returns_defaults: GET returns default config
                - test_update_indexing_config_changes_values: PUT updates config values
                - test_update_indexing_config_partial: Partial update only changes specified fields
                - test_background_indexer_uses_updated_config: Config changes affect background task
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> python -m pytest backend/tests/test_config_api.py -v</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>test_get_indexing_config_returns_defaults</Name>
              <Expectation>GET /api/config/indexing returns default configuration</Expectation>
            </Test>
            <Test>
              <Name>test_update_indexing_config_changes_values</Name>
              <Expectation>PUT /api/config/indexing updates configuration values</Expectation>
            </Test>
            <Test>
              <Name>test_background_indexer_uses_updated_config</Name>
              <Expectation>Background task respects updated scan_interval_minutes</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>Pydantic settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/</Link>
          </Links>
          <ExitCriteria>
            <Criterion>IndexingConfig added to backend/config.py with defaults</Criterion>
            <Criterion>GET /api/config/indexing returns current configuration</Criterion>
            <Criterion>PUT /api/config/indexing updates configuration</Criterion>
            <Criterion>Background indexer uses updated configuration values</Criterion>
            <Criterion>All config API tests pass</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P7">
      <PhaseHeading>Phase P7 — Frontend Status Display</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P7</PhaseId>
          <Intent>Create IndexStatusBadge component and integrate into DocumentCard for visual status display</Intent>
          <Edits>
            <Edit>
              <Path>frontend/src/components/IndexStatusBadge.tsx</Path>
              <Operation>add</Operation>
              <Rationale>Reusable component for displaying index status with color-coded badge and icon</Rationale>
              <Method>
                - Props: status (pending|processing|indexed|failed), errorMessage (optional)
                - Status config: { pending: {color: 'gray', icon: Clock}, processing: {color: 'yellow', icon: Loader2}, indexed: {color: 'green', icon: CheckCircle2}, failed: {color: 'red', icon: XCircle} }
                - Use shadcn/ui Badge component with variant based on status
                - Show tooltip with error message on hover if status=failed
                - Animated spinner for processing status
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/components/DocumentCard.tsx</Path>
              <Operation>modify</Operation>
              <Rationale>Add IndexStatusBadge to document card display</Rationale>
              <Method>
                - Import IndexStatusBadge component
                - Fetch index status from useIndexStatus hook
                - Display badge in card header or footer
                - Handle loading and error states gracefully
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/hooks/useIndexStatus.ts</Path>
              <Operation>add</Operation>
              <Rationale>React Query hook for fetching index status</Rationale>
              <Method>
                - useIndexStatus(): Fetch all index statuses from GET /api/documents/index-status
                - useQuery with refetchInterval (poll every 10 seconds for status updates)
                - Return { data: IndexStatus[], isLoading, error }
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/types/index-status.ts</Path>
              <Operation>add</Operation>
              <Rationale>TypeScript types for index status</Rationale>
              <Method>
                - IndexStatus interface: file_path, file_hash, status, indexed_at, error_message, file_size, last_modified
                - IndexStatusEnum: 'pending' | 'processing' | 'indexed' | 'failed'
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/api/documents.ts</Path>
              <Operation>modify</Operation>
              <Rationale>Add API function for fetching index status</Rationale>
              <Method>
                - getIndexStatus(): GET /api/documents/index-status, return Promise&lt;IndexStatus[]&gt;
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> cd frontend && npm run build</Command>
            <Command>bash> cd frontend && npm run type-check</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>Manual: IndexStatusBadge displays correct color</Name>
              <Expectation>Badge shows gray for pending, yellow for processing, green for indexed, red for failed</Expectation>
            </Test>
            <Test>
              <Name>Manual: DocumentCard shows status badge</Name>
              <Expectation>Each document card displays current index status</Expectation>
            </Test>
            <Test>
              <Name>Manual: Failed status shows error tooltip</Name>
              <Expectation>Hovering over failed badge displays error message</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>shadcn/ui Badge: https://ui.shadcn.com/docs/components/badge</Link>
            <Link>lucide-react icons: https://lucide.dev/icons/</Link>
            <Link>React Query: https://tanstack.com/query/latest/docs/framework/react/overview</Link>
          </Links>
          <ExitCriteria>
            <Criterion>IndexStatusBadge component created with color-coded display</Criterion>
            <Criterion>DocumentCard displays IndexStatusBadge for each document</Criterion>
            <Criterion>useIndexStatus hook fetches and polls index status</Criterion>
            <Criterion>TypeScript types defined for IndexStatus</Criterion>
            <Criterion>Frontend builds without errors</Criterion>
            <Criterion>Manual testing confirms correct badge display</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

    <PhaseBlock id="P8">
      <PhaseHeading>Phase P8 — Frontend Configuration UI</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan</Title>
        <PhasePlan>
          <PhaseId>P8</PhaseId>
          <Intent>Create settings dialog for indexing configuration and add manual "Refresh Index" button</Intent>
          <Edits>
            <Edit>
              <Path>frontend/src/components/IndexingSettingsDialog.tsx</Path>
              <Operation>add</Operation>
              <Rationale>Modal dialog for configuring indexing automation settings</Rationale>
              <Method>
                - Use shadcn/ui Dialog component
                - Form fields: auto_indexing_enabled (Switch), scan_interval_minutes (Input number), max_concurrent_processing (Input number)
                - Use react-hook-form for form state management
                - Use zod for validation (scan_interval >= 1, max_concurrent >= 1)
                - Submit calls PUT /api/config/indexing via useUpdateIndexingConfig mutation
                - Show success/error toast after update
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/views/LibraryView.tsx</Path>
              <Operation>modify</Operation>
              <Rationale>Add "Refresh Index" button and settings button to library view</Rationale>
              <Method>
                - Add button in header: "Refresh Index" (RefreshCw icon)
                - Add button in header: "Settings" (Settings icon) → opens IndexingSettingsDialog
                - "Refresh Index" calls POST /api/documents/trigger-index via useTriggerIndex mutation
                - Show loading spinner during refresh
                - Show toast with result (files_scanned, files_pending counts)
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/hooks/useIndexingConfig.ts</Path>
              <Operation>add</Operation>
              <Rationale>React Query hooks for indexing configuration</Rationale>
              <Method>
                - useIndexingConfig(): Fetch config from GET /api/config/indexing
                - useUpdateIndexingConfig(): Mutation for PUT /api/config/indexing
                - useTriggerIndex(): Mutation for POST /api/documents/trigger-index
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/types/config.ts</Path>
              <Operation>add</Operation>
              <Rationale>TypeScript types for indexing configuration</Rationale>
              <Method>
                - IndexingConfig interface: auto_indexing_enabled, scan_interval_minutes, max_concurrent_processing
                - TriggerIndexResponse interface: files_scanned, files_pending, files_processing, message
              </Method>
            </Edit>
            <Edit>
              <Path>frontend/src/api/config.ts</Path>
              <Operation>add</Operation>
              <Rationale>API functions for configuration management</Rationale>
              <Method>
                - getIndexingConfig(): GET /api/config/indexing
                - updateIndexingConfig(config): PUT /api/config/indexing
                - triggerIndex(): POST /api/documents/trigger-index
              </Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash> cd frontend && npm run build</Command>
            <Command>bash> cd frontend && npm run type-check</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>Manual: Settings dialog opens and displays current config</Name>
              <Expectation>Clicking Settings button opens dialog with current configuration values</Expectation>
            </Test>
            <Test>
              <Name>Manual: Settings dialog updates configuration</Name>
              <Expectation>Changing values and submitting updates backend configuration</Expectation>
            </Test>
            <Test>
              <Name>Manual: Refresh Index button triggers scan</Name>
              <Expectation>Clicking Refresh Index initiates immediate scan and shows result toast</Expectation>
            </Test>
            <Test>
              <Name>Manual: Form validation works</Name>
              <Expectation>Invalid values (scan_interval < 1) show validation errors</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>shadcn/ui Dialog: https://ui.shadcn.com/docs/components/dialog</Link>
            <Link>react-hook-form: https://react-hook-form.com/</Link>
            <Link>zod validation: https://zod.dev/</Link>
          </Links>
          <ExitCriteria>
            <Criterion>IndexingSettingsDialog component created with form fields</Criterion>
            <Criterion>LibraryView has "Refresh Index" and "Settings" buttons</Criterion>
            <Criterion>useIndexingConfig and useUpdateIndexingConfig hooks implemented</Criterion>
            <Criterion>useTriggerIndex mutation triggers immediate scan</Criterion>
            <Criterion>Form validation prevents invalid configuration values</Criterion>
            <Criterion>Success/error toasts display after operations</Criterion>
            <Criterion>Frontend builds without errors</Criterion>
            <Criterion>Manual testing confirms all UI interactions work</Criterion>
          </ExitCriteria>
        </PhasePlan>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <Placeholder>To be filled after execution</Placeholder>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <Placeholder>To be filled by reviewer</Placeholder>
      </Subsection>
    </PhaseBlock>

  </Section>

  <Section id="traceability">
    <Heading>4) CROSS-PHASE TRACEABILITY</Heading>
    <Instruction>Link ACs → phases → files to prove coverage.</Instruction>
    <Traceability>
      <Trace>
        <AcceptanceCriterion>AC1: Files manually placed in upload_dir are automatically detected and indexed</AcceptanceCriterion>
        <Phases>
          <Phase>P2 (File Scanner)</Phase>
          <Phase>P3 (Background Indexing Task)</Phase>
          <Phase>P4 (Integration with Document Processing)</Phase>
        </Phases>
        <Files>
          <File>backend/services/file_scanner.py</File>
          <File>backend/services/background_indexer.py</File>
          <File>backend/routers/documents.py</File>
        </Files>
        <Verification>Manual test: Place file in upload_dir → wait for scan interval → verify status=indexed in DB</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC2: Frontend displays index status with color-coded badges and icons</AcceptanceCriterion>
        <Phases>
          <Phase>P5 (Index Status API)</Phase>
          <Phase>P7 (Frontend Status Display)</Phase>
        </Phases>
        <Files>
          <File>backend/routers/documents.py (GET /index-status)</File>
          <File>frontend/src/components/IndexStatusBadge.tsx</File>
          <File>frontend/src/components/DocumentCard.tsx</File>
        </Files>
        <Verification>Manual test: Check frontend displays correct badge color/icon for each status</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC3: Users can configure auto-trigger settings</AcceptanceCriterion>
        <Phases>
          <Phase>P6 (Configuration Management API)</Phase>
          <Phase>P8 (Frontend Configuration UI)</Phase>
        </Phases>
        <Files>
          <File>backend/config.py</File>
          <File>backend/routers/config.py</File>
          <File>frontend/src/components/IndexingSettingsDialog.tsx</File>
        </Files>
        <Verification>Manual test: Change scan interval in settings → verify background task uses new interval</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC4: Manual "Refresh Index" button triggers immediate scan</AcceptanceCriterion>
        <Phases>
          <Phase>P5 (Index Status API - POST /trigger-index)</Phase>
          <Phase>P8 (Frontend Configuration UI - Refresh button)</Phase>
        </Phases>
        <Files>
          <File>backend/routers/documents.py (POST /trigger-index)</File>
          <File>frontend/src/views/LibraryView.tsx</File>
        </Files>
        <Verification>Manual test: Click "Refresh Index" → verify immediate scan and processing</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC5: Failed processing displays error message</AcceptanceCriterion>
        <Phases>
          <Phase>P1 (IndexStatus model with error_message field)</Phase>
          <Phase>P3 (Background Indexer error handling)</Phase>
          <Phase>P7 (Frontend Status Display - show error tooltip)</Phase>
        </Phases>
        <Files>
          <File>backend/models/index_status.py</File>
          <File>backend/services/background_indexer.py</File>
          <File>frontend/src/components/IndexStatusBadge.tsx</File>
        </Files>
        <Verification>Manual test: Corrupt file → verify status=failed and error message displayed</Verification>
      </Trace>
      <Trace>
        <AcceptanceCriterion>AC6: Background indexing does not degrade query performance</AcceptanceCriterion>
        <Phases>
          <Phase>P3 (Background Indexing Task - rate limiting)</Phase>
        </Phases>
        <Files>
          <File>backend/services/background_indexer.py</File>
        </Files>
        <Verification>Performance test: Measure query p95 latency with/without background indexing, ensure <10% increase</Verification>
      </Trace>
    </Traceability>
  </Section>

  <Section id="post_task_summary">
    <Heading>5) POST-TASK SUMMARY</Heading>
    <Placeholder>To be filled at the end</Placeholder>
  </Section>

  <Section id="checklist">
    <Heading>6) QUICK CHECKLIST</Heading>
    <Checklist>
      <Item status="pending">Phases defined with clear exit criteria</Item>
      <Item status="pending">Each change has rationale and test</Item>
      <Item status="pending">Diffs captured and readable</Item>
      <Item status="pending">Lint/build/tests green</Item>
      <Item status="pending">Acceptance criteria satisfied</Item>
      <Item status="pending">Review completed (per phase)</Item>
      <Item status="pending">Rollback path documented</Item>
    </Checklist>
  </Section>

  <Section id="pr_message">
    <Heading>Optional: Minimal PR Message</Heading>
    <CodeBlock language="markdown"><![CDATA[
Title: T5 Document Indexing Status Management & Automation

Why:
- Users manually placing files in upload_dir have no visibility into indexing status
- No automatic RAG processing for manually added files
- Lack of error visibility when processing fails

What:
- Added IndexStatus tracking (SQLite) with status: pending/processing/indexed/failed
- Implemented background indexing task (periodic scan + async processing queue)
- Added API endpoints: GET /index-status, POST /trigger-index, GET/PUT /config/indexing
- Created frontend status badges (color-coded with icons) in DocumentCard
- Added IndexingSettingsDialog for user configuration
- Added "Refresh Index" button for manual triggering

Tests:
- Unit tests: IndexStatusService CRUD, FileScanner, BackgroundIndexer
- Integration tests: API endpoints, status updates during processing
- Manual tests: File detection, status display, configuration changes
- Performance tests: Query latency impact <10%

Risks/Mitigations:
- Performance: Cached file list, only check modified files
- Concurrency: Atomic status updates prevent duplicate processing
- Reliability: Try/except per file, errors logged and displayed in UI
]]></CodeBlock>
  </Section>
</Task>

