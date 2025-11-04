<Task>
  <Meta>
    <ID>T3</ID>
    <Name>Frontend Migration Deployment</Name>
    <Created>2025-11-03</Created>
    <Status>complete</Status>
    <Goal>Deploy React frontend to production by replacing Gradio frontend and updating deployment scripts</Goal>
    <Dependencies>
      <Item>Task T2 (React Frontend Migration) - COMPLETE</Item>
      <Item>All 68 tests passing (100% pass rate)</Item>
      <Item>Production build successful</Item>
    </Dependencies>
  </Meta>

  <Context>
    <Problem>
      React frontend is complete and tested, but still in `frontend-react/` directory.
      Deployment scripts still point to old Gradio frontend.
      Need to promote React frontend to production and update all scripts.
    </Problem>
    <CurrentBehavior>
      - Gradio frontend at `frontend/app.py` (port 7860)
      - React frontend at `frontend-react/` (port 5173)
      - `scripts/start_frontend.sh` starts Gradio
      - `scripts/start_all.sh` orchestrates both
    </CurrentBehavior>
    <TargetBehavior>
      - React frontend at `frontend/` (port 5173)
      - Gradio archived at `frontend-gradio-legacy/`
      - `scripts/start_frontend.sh` starts React
      - Support both production and dev modes
    </TargetBehavior>
  </Context>

  <Phases>
    <Phase id="P1">
      <Name>Directory Restructuring</Name>
      <Status>complete</Status>
      <StartDate>2025-11-03</StartDate>
      <EndDate>2025-11-03</EndDate>

      <P1.1_Analysis>
        **What**: Rename directories to promote React frontend
        **Where**: Root directory (frontend/, frontend-react/)
        **Why**: Make React frontend the default, archive Gradio for rollback

        **Actions**:
        1. Rename `frontend/` to `frontend-gradio-legacy/`
        2. Rename `frontend-react/` to `frontend/`
      </P1.1_Analysis>

      <P1.2_Edits>
        **Commands Executed**:
        ```bash
        mv frontend/ frontend-gradio-legacy/
        mv frontend-react/ frontend/
        ```

        **Result**:
        - ✅ React frontend now at `frontend/`
        - ✅ Gradio frontend archived at `frontend-gradio-legacy/`
      </P1.2_Edits>

      <P1.3_Verification>
        ```bash
        $ ls -la | grep frontend
        drwxr-xr-x   7 user007 LiLab   4096 Nov  3 15:33 frontend
        drwxr-xr-x   3 user007 LiLab     51 Nov  3 01:30 frontend-gradio-legacy
        ```

        ✅ Directories renamed successfully
      </P1.3_Verification>

      <P1.4_Status>
        **Status**: COMPLETE ✅
      </P1.4_Status>
    </Phase>

    <Phase id="P2">
      <Name>Update Deployment Scripts</Name>
      <Status>complete</Status>
      <StartDate>2025-11-03</StartDate>
      <EndDate>2025-11-03</EndDate>

      <P2.1_Analysis>
        **What**: Rewrite `scripts/start_frontend.sh` for React
        **Where**: scripts/start_frontend.sh
        **Why**: Enable React frontend startup with production/dev modes

        **Requirements**:
        - Support production mode (default): build + preview
        - Support dev mode: npm run dev with hot reload
        - Auto-install dependencies if node_modules missing
        - Set VITE_BACKEND_URL from BACKEND_URL
        - Use port 5173 instead of 7860
      </P2.1_Analysis>

      <P2.2_Edits>
        **File Modified**: `scripts/start_frontend.sh`

        **Key Changes**:
        1. Changed from Python to Node.js/npm
        2. Added dependency check and auto-install
        3. Added mode selection (production/dev)
        4. Changed port from 7860 to 5173
        5. Set VITE_BACKEND_URL environment variable
        6. Production mode: `npm run build` + `npm run preview`
        7. Dev mode: `npm run dev` with hot reload
      </P2.2_Edits>

      <P2.3_Script_Content>
        ```bash
        #!/bin/bash
        # Start RAG-Anything React Frontend

        set -e

        # Get script directory and project root
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
        FRONTEND_DIR="$PROJECT_ROOT/frontend"

        # Change to frontend directory
        cd "$FRONTEND_DIR"

        # Default values
        HOST=${FRONTEND_HOST:-0.0.0.0}
        PORT=${FRONTEND_PORT:-5173}
        BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
        FRONTEND_MODE=${FRONTEND_MODE:-production}

        # Export backend URL for Vite
        export VITE_BACKEND_URL="$BACKEND_URL"

        # Check if node_modules exists, install dependencies if not
        if [ ! -d "node_modules" ]; then
            echo "📦 Installing npm dependencies..."
            npm install
            echo ""
        fi

        # Start frontend based on mode
        if [ "$FRONTEND_MODE" = "dev" ]; then
            echo "🚀 Starting React frontend in DEVELOPMENT mode..."
            npm run dev -- --host "$HOST" --port "$PORT"
        else
            echo "🏗️  Building React frontend for PRODUCTION..."
            npm run build
            echo ""
            echo "🚀 Starting React frontend in PRODUCTION mode..."
            npm run preview -- --host "$HOST" --port "$PORT"
        fi
        ```
      </P2.3_Script_Content>

      <P2.4_Status>
        **Status**: COMPLETE ✅
      </P2.4_Status>
    </Phase>

    <Phase id="P3">
      <Name>Update Configuration Files</Name>
      <Status>complete</Status>
      <StartDate>2025-11-03</StartDate>
      <EndDate>2025-11-03</EndDate>

      <P3.1_Analysis>
        **What**: Update environment variables and configuration
        **Where**: frontend/.env
        **Why**: Ensure correct port and settings for React frontend
      </P3.1_Analysis>

      <P3.2_Edits>
        **File Modified**: `frontend/.env`

        **Changes**:
        - Added `VITE_PREVIEW_PORT=5173` for production preview
        - Kept `VITE_DEV_PORT=5173` for development
        - Kept `VITE_BACKEND_URL=http://localhost:8000`
      </P3.2_Edits>

      <P3.3_Status>
        **Status**: COMPLETE ✅
      </P3.3_Status>
    </Phase>

    <Phase id="P4">
      <Name>Update Documentation</Name>
      <Status>complete</Status>
      <StartDate>2025-11-03</StartDate>
      <EndDate>2025-11-03</EndDate>

      <P4.1_Analysis>
        **What**: Update all documentation to reflect React frontend
        **Where**: Multiple documentation files
        **Why**: Ensure users have accurate information
      </P4.1_Analysis>

      <P4.2_Edits>
        **Files Modified**:
        1. `README_NEW_ARCHITECTURE.md` - Updated architecture diagram (port 7860 → 5173)
        2. `docs/FRONTEND_REDESIGN.md` - Updated usage instructions
        3. `docs/deployment/REACT_DEPLOYMENT.md` - Already up-to-date

        **Files Created**:
        1. `docs/REACT_MIGRATION_COMPLETED.md` - Complete migration documentation
        2. `_TASKs/T3_frontend-migration-deployment.md` - This task file
      </P4.2_Edits>

      <P4.3_Status>
        **Status**: COMPLETE ✅
      </P4.3_Status>
    </Phase>
  </Phases>

  <Summary>
    <Completed>
      - [x] Archived Gradio frontend to `frontend-gradio-legacy/`
      - [x] Promoted React frontend to `frontend/`
      - [x] Rewrote `scripts/start_frontend.sh` for React
      - [x] Updated port from 7860 to 5173
      - [x] Added production/dev mode support
      - [x] Updated environment variables
      - [x] Updated documentation
      - [x] Created migration guide
    </Completed>

    <Usage>
      **Production Mode (Default)**:
      ```bash
      ./scripts/start_all.sh
      # Frontend: http://localhost:5173
      # Backend: http://localhost:8000
      ```

      **Development Mode**:
      ```bash
      FRONTEND_MODE=dev ./scripts/start_all.sh
      # Frontend: http://localhost:5173 (with hot reload)
      # Backend: http://localhost:8000
      ```
    </Usage>

    <Rollback>
      If needed, rollback to Gradio:
      ```bash
      mv frontend/ frontend-react-backup/
      mv frontend-gradio-legacy/ frontend/
      git checkout scripts/start_frontend.sh
      ./scripts/start_frontend.sh
      # Frontend: http://localhost:7860
      ```
    </Rollback>

    <Outcome>
      ✅ **Migration COMPLETE**
      - React frontend is now the default
      - Gradio frontend archived for rollback
      - Deployment scripts updated
      - Documentation updated
      - Production-ready
    </Outcome>
  </Summary>
</Task>

