# BankX Frontend - Docker Setup

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Backend running on port 8080 (for testing)

### Test the Frontend Image

**Option 1: Automated Test (Recommended)**
```powershell
cd app/frontend
.\test-frontend.ps1
```

This will:
1. Build the Docker image
2. Check if backend is running
3. Start the container
4. Verify it's healthy
5. Open http://localhost:8081

**Option 2: Manual Steps**
```powershell
# 1. Build image
docker build -t bankx-frontend:test .

# 2. Run container
docker run -d -p 8081:80 -e BACKEND_URL=http://host.docker.internal:8080 --name bankx-frontend-test bankx-frontend:test

# 3. Check logs
docker logs -f bankx-frontend-test

# 4. Access
# Open http://localhost:8081
```

## Available Commands

### Using Test Script
```powershell
.\test-frontend.ps1 build    # Build image only
.\test-frontend.ps1 start    # Start container
.\test-frontend.ps1 stop     # Stop container
.\test-frontend.ps1 logs     # View logs
.\test-frontend.ps1 test     # Full test (default)
.\test-frontend.ps1 clean    # Remove container & image
```

### Using Docker Compose
```powershell
# Start
docker-compose -f docker-compose.test.yml up -d

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Stop
docker-compose -f docker-compose.test.yml down
```

## Configuration

### Environment Variables

- `BACKEND_URL`: Backend API URL (default: `http://localhost:8080`)

### For Local Testing

When running locally with host backend:
- Windows/Mac: Use `http://host.docker.internal:8080`
- Linux: Use `http://172.17.0.1:8080`

### For Production

Point to your deployed backend:
```bash
docker run -p 8081:80 -e BACKEND_URL=https://api.bankx.com bankx-frontend:latest
```

## Dockerfile Explanation

### Two-Stage Build

**Stage 1: Build**
- Uses Node.js 18 Alpine
- Installs dependencies with `npm ci`
- Builds React app with Vite
- Output: `build/` directory

**Stage 2: Serve**
- Uses Nginx Alpine (lightweight)
- Copies built files
- Configures Nginx with environment variable support
- Serves on port 80

### Key Features

✅ **Optimized Layer Caching**: Package files copied first  
✅ **Small Image Size**: Alpine-based (~50MB)  
✅ **Environment Variables**: Runtime configuration via `BACKEND_URL`  
✅ **Health Checks**: Built-in health endpoint  
✅ **SPA Routing**: Proper handling of React Router  
✅ **Gzip Compression**: Faster load times  
✅ **Static Asset Caching**: Browser caching for JS/CSS  
✅ **API Proxying**: `/api` requests proxied to backend  

## Nginx Configuration

The nginx configuration (`nginx/nginx.conf.template`) provides:

1. **SPA Routing**: `try_files` for React Router
2. **API Proxy**: `/api` → backend
3. **Compression**: Gzip for text assets
4. **Caching**: 1-year cache for static assets
5. **Health Check**: `/health` endpoint
6. **Streaming Support**: Increased timeouts for real-time features

## Troubleshooting

### Build Fails

```powershell
# Check Docker is running
docker info

# Clean Docker cache
docker builder prune

# Rebuild without cache
docker build --no-cache -t bankx-frontend:test .
```

### Container Won't Start

```powershell
# Check logs
docker logs bankx-frontend-test

# Check if port 8081 is available
netstat -ano | findstr :8081
```

### Can't Connect to Backend

```powershell
# Test from inside container
docker exec bankx-frontend-test wget -O- http://host.docker.internal:8080/health

# Check backend is running
curl http://localhost:8080/health
```

### Frontend Loads but API Fails

1. Check browser console for errors
2. Verify `BACKEND_URL` is correct
3. Check nginx logs:
   ```powershell
   docker exec bankx-frontend-test cat /var/log/nginx/error.log
   ```

## Verification Checklist

After building and running:

- [ ] Container starts without errors
- [ ] Health check passes: `curl http://localhost:8081/health`
- [ ] Frontend loads: http://localhost:8081
- [ ] Login page appears
- [ ] Can connect to backend (check browser console)
- [ ] Chat functionality works
- [ ] API calls succeed

## Image Size

Expected image size: **~50-70MB**

Check with:
```powershell
docker images bankx-frontend:test
```

## Next Steps

Once frontend image works locally:

1. Tag for registry:
   ```powershell
   docker tag bankx-frontend:test youracr.azurecr.io/bankx-frontend:latest
   ```

2. Push to Azure Container Registry:
   ```powershell
   az acr login --name youracr
   docker push youracr.azurecr.io/bankx-frontend:latest
   ```

3. Deploy to Azure Container Instances / AKS / App Service

## Production Deployment

For production, update `BACKEND_URL` to your deployed backend:

```yaml
# docker-compose-production.yml
frontend:
  image: youracr.azurecr.io/bankx-frontend:latest
  environment:
    - BACKEND_URL=https://api.bankx.com
  ports:
    - "80:80"
```

## File Structure

```
app/frontend/
├── Dockerfile                    # Multi-stage Docker build
├── docker-compose.test.yml       # Local testing config
├── test-frontend.ps1             # Test automation script
├── DOCKER_FRONTEND_README.md     # This file
├── nginx/
│   └── nginx.conf.template       # Nginx config with env vars
├── src/                          # React source code
├── build/                        # Build output (created during build)
└── package.json                  # Dependencies
```

## Tips

1. **Always test locally first** before pushing to registry
2. **Check logs** if something doesn't work
3. **Use health endpoint** to verify container is ready
4. **Backend must be running** for full testing
5. **Clear browser cache** if you see old content

## Support

If issues persist:
1. Check `docker logs bankx-frontend-test`
2. Verify backend is accessible
3. Test nginx config: `docker exec bankx-frontend-test nginx -t`
4. Review browser console for frontend errors
