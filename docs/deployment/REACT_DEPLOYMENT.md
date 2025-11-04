# React Frontend Deployment Guide

This guide covers deploying the RAG-Anything React frontend to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Production Build](#production-build)
- [Deployment Options](#deployment-options)
  - [Docker Deployment](#docker-deployment)
  - [Static Hosting (Vercel, Netlify, etc.)](#static-hosting)
  - [Nginx Deployment](#nginx-deployment)
  - [Apache Deployment](#apache-deployment)
- [Backend Integration](#backend-integration)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Node.js**: 18+ or 20+
- **npm**: 9+ or yarn 1.22+
- **Backend API**: Running and accessible
- **Build tools**: Vite 7.1.7 (included in dependencies)

---

## Environment Configuration

### 1. Create Production Environment File

Create `.env.production` in the `frontend-react/` directory:

```env
# Backend API URL (REQUIRED)
VITE_API_BASE_URL=https://api.your-domain.com

# Optional: Enable production mode
NODE_ENV=production
```

### 2. Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000` | Yes |
| `NODE_ENV` | Environment mode | `development` | No |

**Important**: All environment variables must be prefixed with `VITE_` to be accessible in the frontend.

---

## Production Build

### 1. Install Dependencies

```bash
cd frontend-react
npm install
```

### 2. Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

**Build Output**:
```
dist/
├── index.html           # Entry HTML file
├── assets/
│   ├── index-[hash].js  # Main JavaScript bundle (~343 kB gzipped)
│   ├── index-[hash].css # Styles (~32 kB gzipped)
│   └── [vendor]-[hash].js # Vendor chunks (React, UI libs)
└── favicon.ico          # Favicon
```

### 3. Preview Production Build Locally

```bash
npm run preview
```

This starts a local server at `http://localhost:4173` to preview the production build.

---

## Deployment Options

### Docker Deployment

#### Option 1: Multi-Stage Dockerfile (Recommended)

Create `frontend-react/Dockerfile`:

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create `frontend-react/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

#### Build and Run Docker Container

```bash
# Build image
docker build -t rag-anything-frontend:latest .

# Run container
docker run -d \
  -p 80:80 \
  --name rag-frontend \
  -e VITE_API_BASE_URL=https://api.your-domain.com \
  rag-anything-frontend:latest
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend-react
      dockerfile: Dockerfile
    ports:
      - "80:80"
    environment:
      - VITE_API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://localhost
    restart: unless-stopped
```

Run with:

```bash
docker-compose up -d
```

---

### Static Hosting

The React frontend is a static site and can be deployed to any static hosting service.

#### Vercel

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Deploy**:
   ```bash
   cd frontend-react
   vercel --prod
   ```

3. **Configure Environment Variables** in Vercel dashboard:
   - `VITE_API_BASE_URL`: Your backend API URL

4. **Configure Build Settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

#### Netlify

1. **Install Netlify CLI**:
   ```bash
   npm install -g netlify-cli
   ```

2. **Deploy**:
   ```bash
   cd frontend-react
   netlify deploy --prod
   ```

3. **Configure** in `netlify.toml`:
   ```toml
   [build]
     command = "npm run build"
     publish = "dist"

   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

4. **Set Environment Variables** in Netlify dashboard:
   - `VITE_API_BASE_URL`: Your backend API URL

#### GitHub Pages

1. **Install gh-pages**:
   ```bash
   npm install --save-dev gh-pages
   ```

2. **Add deploy script** to `package.json`:
   ```json
   {
     "scripts": {
       "deploy": "npm run build && gh-pages -d dist"
     }
   }
   ```

3. **Configure base path** in `vite.config.ts`:
   ```typescript
   export default defineConfig({
     base: '/your-repo-name/',
     // ... other config
   });
   ```

4. **Deploy**:
   ```bash
   npm run deploy
   ```

#### AWS S3 + CloudFront

1. **Build the app**:
   ```bash
   npm run build
   ```

2. **Upload to S3**:
   ```bash
   aws s3 sync dist/ s3://your-bucket-name --delete
   ```

3. **Configure S3 bucket** for static website hosting

4. **Create CloudFront distribution** pointing to S3 bucket

5. **Configure CloudFront**:
   - Default Root Object: `index.html`
   - Error Pages: 404 → `/index.html` (for SPA routing)

---

### Nginx Deployment

1. **Build the app**:
   ```bash
   npm run build
   ```

2. **Copy files to web server**:
   ```bash
   sudo cp -r dist/* /var/www/html/rag-anything/
   ```

3. **Configure Nginx** (`/etc/nginx/sites-available/rag-anything`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       root /var/www/html/rag-anything;
       index index.html;

       # Enable gzip
       gzip on;
       gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

       # SPA routing
       location / {
           try_files $uri $uri/ /index.html;
       }

       # Cache static assets
       location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
           expires 1y;
           add_header Cache-Control "public, immutable";
       }

       # Security headers
       add_header X-Frame-Options "SAMEORIGIN" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-XSS-Protection "1; mode=block" always;
   }
   ```

4. **Enable site and reload Nginx**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/rag-anything /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

---

### Apache Deployment

1. **Build the app**:
   ```bash
   npm run build
   ```

2. **Copy files to web server**:
   ```bash
   sudo cp -r dist/* /var/www/html/rag-anything/
   ```

3. **Create `.htaccess`** in `/var/www/html/rag-anything/`:
   ```apache
   <IfModule mod_rewrite.c>
     RewriteEngine On
     RewriteBase /
     RewriteRule ^index\.html$ - [L]
     RewriteCond %{REQUEST_FILENAME} !-f
     RewriteCond %{REQUEST_FILENAME} !-d
     RewriteRule . /index.html [L]
   </IfModule>

   # Enable compression
   <IfModule mod_deflate.c>
     AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript application/json
   </IfModule>

   # Cache static assets
   <IfModule mod_expires.c>
     ExpiresActive On
     ExpiresByType image/jpg "access plus 1 year"
     ExpiresByType image/jpeg "access plus 1 year"
     ExpiresByType image/gif "access plus 1 year"
     ExpiresByType image/png "access plus 1 year"
     ExpiresByType image/svg+xml "access plus 1 year"
     ExpiresByType text/css "access plus 1 year"
     ExpiresByType application/javascript "access plus 1 year"
     ExpiresByType font/woff "access plus 1 year"
     ExpiresByType font/woff2 "access plus 1 year"
   </IfModule>
   ```

4. **Enable mod_rewrite**:
   ```bash
   sudo a2enmod rewrite
   sudo systemctl restart apache2
   ```

---

## Backend Integration

### CORS Configuration

The backend must allow requests from the frontend domain.

**Backend Configuration** (`backend/config.py`):

```python
CORS_ORIGINS = [
    "http://localhost:5173",  # Development
    "https://your-frontend-domain.com",  # Production
]
```

### API Proxy (Optional)

If you want to avoid CORS issues, you can proxy API requests through the frontend server.

**Nginx Proxy Configuration**:

```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

Then set `VITE_API_BASE_URL=""` (empty string) to use relative URLs.

---

## Performance Optimization

### 1. Build Optimization

The production build is already optimized with:
- ✅ Code splitting (React, UI vendors, main bundle)
- ✅ Tree shaking (unused code removed)
- ✅ Minification (JavaScript and CSS)
- ✅ Asset optimization (images, fonts)
- ✅ Lazy loading (routes loaded on demand)

### 2. CDN Configuration

Serve static assets from a CDN for better performance:

1. Upload `dist/assets/*` to CDN
2. Configure `vite.config.ts`:
   ```typescript
   export default defineConfig({
     build: {
       assetsDir: 'assets',
       rollupOptions: {
         output: {
           assetFileNames: 'assets/[name]-[hash][extname]',
         },
       },
     },
   });
   ```

### 3. Caching Strategy

**Recommended Cache Headers**:
- HTML files: `Cache-Control: no-cache` (always revalidate)
- JS/CSS files: `Cache-Control: public, max-age=31536000, immutable` (1 year)
- Images/Fonts: `Cache-Control: public, max-age=31536000, immutable` (1 year)

### 4. Bundle Size Analysis

Analyze bundle size:

```bash
npm run build -- --mode analyze
```

Or use:

```bash
npx vite-bundle-visualizer
```

**Current Bundle Sizes** (gzipped):
- Main bundle: ~108 kB
- React vendor: ~16 kB
- UI vendor: ~12 kB
- Query vendor: ~25 kB
- **Total**: ~161 kB (excellent for a full-featured app)

---

## Troubleshooting

### Issue: Blank Page After Deployment

**Cause**: Incorrect base path or routing configuration

**Solution**:
1. Check browser console for errors
2. Verify `VITE_API_BASE_URL` is set correctly
3. Ensure server is configured for SPA routing (all routes → `index.html`)

### Issue: API Requests Failing

**Cause**: CORS or incorrect API URL

**Solution**:
1. Check `VITE_API_BASE_URL` in environment variables
2. Verify backend CORS configuration allows frontend domain
3. Check browser network tab for actual request URLs

### Issue: Assets Not Loading

**Cause**: Incorrect base path

**Solution**:
1. If deploying to subdirectory, set `base` in `vite.config.ts`:
   ```typescript
   export default defineConfig({
     base: '/subdirectory/',
   });
   ```

### Issue: Environment Variables Not Working

**Cause**: Variables not prefixed with `VITE_`

**Solution**:
1. All environment variables must start with `VITE_`
2. Rebuild after changing environment variables
3. Verify with: `console.log(import.meta.env.VITE_API_BASE_URL)`

---

## Security Checklist

- [ ] Set `VITE_API_BASE_URL` to HTTPS in production
- [ ] Enable HTTPS for frontend (use Let's Encrypt)
- [ ] Configure security headers (CSP, X-Frame-Options, etc.)
- [ ] Enable CORS only for trusted domains
- [ ] Use environment variables for sensitive config
- [ ] Regularly update dependencies (`npm audit`)
- [ ] Implement rate limiting on backend
- [ ] Use secure cookies for authentication (if applicable)

---

## Monitoring and Logging

### 1. Error Tracking

Integrate error tracking service (e.g., Sentry):

```typescript
// src/main.tsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: import.meta.env.MODE,
});
```

### 2. Analytics

Add analytics (e.g., Google Analytics, Plausible):

```typescript
// src/main.tsx
import ReactGA from "react-ga4";

if (import.meta.env.PROD) {
  ReactGA.initialize("your-ga-id");
}
```

### 3. Performance Monitoring

Monitor Core Web Vitals:

```typescript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(console.log);
getFID(console.log);
getFCP(console.log);
getLCP(console.log);
getTTFB(console.log);
```

---

## Rollback Procedure

If issues arise after deployment:

1. **Keep previous build**:
   ```bash
   cp -r dist dist-backup-$(date +%Y%m%d)
   ```

2. **Rollback**:
   ```bash
   rm -rf dist
   cp -r dist-backup-YYYYMMDD dist
   ```

3. **Docker rollback**:
   ```bash
   docker tag rag-anything-frontend:latest rag-anything-frontend:backup
   docker pull rag-anything-frontend:previous-tag
   docker tag rag-anything-frontend:previous-tag rag-anything-frontend:latest
   ```

---

## Production Checklist

Before deploying to production:

- [ ] All tests passing (`npm run test:run`)
- [ ] Production build successful (`npm run build`)
- [ ] Environment variables configured
- [ ] Backend API accessible from frontend
- [ ] CORS configured correctly
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Caching strategy implemented
- [ ] Error tracking configured
- [ ] Monitoring and logging set up
- [ ] Rollback procedure documented
- [ ] Performance tested (Lighthouse score > 90)

---

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review [Frontend README](../frontend-react/README.md)
- Check backend logs for API errors
- Open an issue on GitHub

---

**Last Updated**: 2025-11-03  
**Version**: 1.0.0  
**Maintainer**: RAG-Anything Team

