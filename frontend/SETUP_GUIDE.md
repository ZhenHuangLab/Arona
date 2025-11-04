# React Frontend Setup Guide

## Problem: Tailwind CSS v4 Incompatibility

**Issue**: The initial setup installed Tailwind CSS v4, but shadcn/ui currently only supports Tailwind CSS v3.

**Solution**: Downgrade to Tailwind CSS v3 and configure properly.

---

## Step-by-Step Fix

### 1. Remove Tailwind CSS v4

```bash
cd frontend-react
npm uninstall tailwindcss @tailwindcss/vite
```

### 2. Install Tailwind CSS v3

```bash
npm install -D tailwindcss@^3.4.1 postcss autoprefixer
```

### 3. Initialize Tailwind CSS

```bash
npx tailwindcss init -p
```

This creates:
- `tailwind.config.js`
- `postcss.config.js`

### 4. Configure Tailwind CSS

Edit `tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 5. Update CSS Entry Point

Edit `src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 6. Verify Configuration

Check that these files exist and are configured:

- ✅ `vite.config.ts` - Has path alias `@` → `./src`
- ✅ `tsconfig.app.json` - Has `baseUrl` and `paths` for `@/*`
- ✅ `tailwind.config.js` - Tailwind v3 config
- ✅ `postcss.config.js` - PostCSS config

### 7. Initialize shadcn/ui

```bash
npx shadcn@latest init
```

**Choose these options:**

```
✔ Preflight checks.
✔ Verifying framework. Found Vite.
✔ Validating Tailwind CSS config.
✔ Validating import alias.

Which style would you like to use? › Default
Which color would you like to use as base color? › Slate
Do you want to use CSS variables for colors? › yes

✔ Writing components.json.
✔ Checking registry.
✔ Updating tailwind.config.js
✔ Updating src/index.css
✔ Installing dependencies.
✔ Created 1 file:
  - src/lib/utils.ts

Success! Project initialization completed.
You may now add components.
```

### 8. Add shadcn/ui Components

```bash
npx shadcn@latest add button
npx shadcn@latest add dialog
npx shadcn@latest add input
npx shadcn@latest add dropdown-menu
npx shadcn@latest add card
npx shadcn@latest add sonner
npx shadcn@latest add label
npx shadcn@latest add select
npx shadcn@latest add textarea
npx shadcn@latest add badge
npx shadcn@latest add separator
```

### 9. Install Additional Dependencies

```bash
npm install \
  @tanstack/react-query \
  @tanstack/react-query-devtools \
  zustand \
  react-router-dom \
  axios \
  react-hook-form \
  zod \
  @hookform/resolvers \
  lucide-react \
  sonner \
  react-dropzone \
  clsx \
  tailwind-merge
```

### 10. Install Dev Dependencies

```bash
npm install -D \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  @playwright/test \
  prettier
```

---

## Verification

### Test Tailwind CSS

Create `src/Test.tsx`:

```tsx
export default function Test() {
  return (
    <div className="p-4 bg-blue-500 text-white rounded-lg">
      Tailwind CSS is working! 🎉
    </div>
  );
}
```

Import in `src/App.tsx`:

```tsx
import Test from './Test';

function App() {
  return <Test />;
}

export default App;
```

Run dev server:

```bash
npm run dev
```

Visit http://localhost:5173 - you should see a blue box with white text.

### Test shadcn/ui

Update `src/App.tsx`:

```tsx
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';

function App() {
  return (
    <div className="p-8">
      <Button>
        <Send className="w-4 h-4 mr-2" />
        Send Message
      </Button>
    </div>
  );
}

export default App;
```

You should see a styled button with an icon.

---

## Common Issues

### Issue 1: "Cannot find module '@/components/ui/button'"

**Solution**: Make sure you've:
1. Added path alias in `vite.config.ts`
2. Added `baseUrl` and `paths` in `tsconfig.app.json`
3. Run `npx shadcn@latest add button`

### Issue 2: "Tailwind classes not working"

**Solution**: 
1. Check `tailwind.config.js` has correct `content` paths
2. Check `src/index.css` has `@tailwind` directives
3. Restart dev server

### Issue 3: "Module not found: Can't resolve 'path'"

**Solution**: Install `@types/node`:

```bash
npm install -D @types/node
```

---

## Project Structure After Setup

```
frontend-react/
├── src/
│   ├── components/
│   │   └── ui/              # shadcn/ui components
│   │       ├── button.tsx
│   │       ├── dialog.tsx
│   │       ├── input.tsx
│   │       └── ...
│   ├── lib/
│   │   └── utils.ts         # Utility functions (cn, etc.)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css            # Tailwind directives
├── components.json          # shadcn/ui config
├── tailwind.config.js       # Tailwind v3 config
├── postcss.config.js        # PostCSS config
├── vite.config.ts           # Vite config with path alias
├── tsconfig.app.json        # TypeScript config with paths
└── package.json
```

---

## Next Steps

Once setup is complete:

1. **Create folder structure**:
   ```bash
   mkdir -p src/api
   mkdir -p src/components/layout
   mkdir -p src/components/chat
   mkdir -p src/components/documents
   mkdir -p src/components/common
   mkdir -p src/hooks
   mkdir -p src/store
   mkdir -p src/types
   mkdir -p src/utils
   mkdir -p src/views
   ```

2. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

3. **Start development**:
   ```bash
   npm run dev
   ```

4. **Begin Phase 1 implementation** (see `_TASKs/T2_react-frontend-migration.md`)

---

## Quick Commands Reference

```bash
# Development
npm run dev              # Start dev server (http://localhost:5173)
npm run build            # Build for production
npm run preview          # Preview production build

# Linting & Formatting
npm run lint             # Run ESLint
npm run format           # Format with Prettier (after adding script)

# Testing
npm run test             # Run unit tests
npm run test:ui          # Run tests with UI
npm run e2e              # Run E2E tests

# shadcn/ui
npx shadcn@latest add <component>  # Add component
npx shadcn@latest diff             # Check for updates
```

---

## Support

- **shadcn/ui Docs**: https://ui.shadcn.com/docs
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **Vite Docs**: https://vitejs.dev/
- **React Query Docs**: https://tanstack.com/query/latest

---

## Summary

✅ **Fixed**: Downgraded Tailwind CSS v4 → v3  
✅ **Configured**: Path alias `@` → `./src`  
✅ **Ready**: shadcn/ui can now be initialized  

**Next**: Run `npx shadcn@latest init` and start building! 🚀

