# 🚀 BankX Frontend Docker - Quick Start

## ⚡ TL;DR

```powershell
# Navigate to frontend directory
cd app/frontend

# Run automated test
.\test-frontend.ps1

# Access at http://localhost:8081
```

That's it! The script will build, start, and verify everything.

---

## 📋 Prerequisites

1. ✅ Docker Desktop installed and running
2. ✅ Backend running on port 8080 (optional for build, required for testing)

---

## 🎯 Step-by-Step

### 1. Make sure you're in the frontend directory
```powershell
cd D:\Metakaal\BankX\claude_bank\app\frontend
```

### 2. Start your backend (in another terminal)
```powershell
cd D:\Metakaal\BankX\claude_bank\app\copilot
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3. Run the test script
```powershell
.\test-frontend.ps1
```

### 4. Open your browser
Go to: http://localhost:8081

---

## ✅ What the Script Does

1. ✓ Checks if Docker is running
2. ✓ Builds the frontend Docker image
3. ✓ Checks if backend is available
4. ✓ Starts the frontend container
5. ✓ Waits for it to be healthy
6. ✓ Verifies it's responding
7. ✓ Gives you the URL to test

---

## 🎮 Other Commands

```powershell
# Just build (no start)
.\test-frontend.ps1 build

# Start (after building)
.\test-frontend.ps1 start

# View logs
.\test-frontend.ps1 logs

# Stop container
.\test-frontend.ps1 stop

# Clean up everything
.\test-frontend.ps1 clean
```

---

## 🐛 Troubleshooting

### "Docker is not running"
**Solution**: Start Docker Desktop

### "Build failed"
**Solution**: Check you're in the correct directory (`app/frontend`)

### "Backend is not running"
**Solution**: Start backend on port 8080 (see step 2 above)

### "Container won't start"
**Solution**: Check logs with `.\test-frontend.ps1 logs`

### "Frontend loads but can't connect to backend"
**Solution**: 
1. Check backend is running: `curl http://localhost:8080/health`
2. Check browser console for errors
3. Verify container logs: `.\test-frontend.ps1 logs`

---

## 📊 Expected Output

When successful, you'll see:

```
======================================
BankX Frontend Docker Test
======================================

Step 1: Building image...
✓ Build successful!

Step 2: Checking if backend is running on port 8080...
✓ Backend is running!

Step 3: Starting frontend container...
✓ Container started!

Step 4: Waiting for container to be healthy...
✓ Frontend is healthy!

Step 5: Testing frontend...
✓ Frontend is responding!

========================================
✓ ALL TESTS PASSED!
========================================

Frontend is running at: http://localhost:8081
```

---

## 🎯 Verification

Once it's running, verify these:

- [ ] Frontend loads at http://localhost:8081
- [ ] Login page appears
- [ ] No console errors in browser
- [ ] Can authenticate
- [ ] Chat interface works
- [ ] Can send messages and get responses

---

## 🛑 Stopping

```powershell
.\test-frontend.ps1 stop
```

Or:
```powershell
docker-compose -f docker-compose.test.yml down
```

---

## 📦 What Was Created

- **Docker Image**: `bankx-frontend:test` (~50-70MB)
- **Container**: `bankx-frontend-test` (running on port 8081)

Check with:
```powershell
docker images bankx-frontend:test
docker ps | findstr bankx-frontend
```

---

## 🔄 Rebuild After Changes

If you make changes to the frontend code:

```powershell
# Stop, rebuild, and start
.\test-frontend.ps1 stop
.\test-frontend.ps1 test
```

Or:
```powershell
docker-compose -f docker-compose.test.yml up --build -d
```

---

## 📚 More Information

- Full documentation: `DOCKER_FRONTEND_README.md`
- Nginx config: `nginx/nginx.conf.template`
- Docker config: `Dockerfile`

---

## ✨ Next Steps

Once frontend works:

1. **Tag the image**:
   ```powershell
   docker tag bankx-frontend:test bankx-frontend:latest
   ```

2. **Push to registry** (Azure Container Registry):
   ```powershell
   az acr login --name youracr
   docker tag bankx-frontend:test youracr.azurecr.io/bankx-frontend:latest
   docker push youracr.azurecr.io/bankx-frontend:latest
   ```

3. **Deploy to Azure** (ACI, AKS, or App Service)

---

## 💡 Pro Tips

1. Always test locally before pushing to registry
2. Use `.\test-frontend.ps1 logs` to debug issues
3. Backend must be running for full end-to-end testing
4. Clear browser cache if you see old content
5. Check Docker Desktop resources if performance is slow

---

## 🆘 Need Help?

1. Check logs: `.\test-frontend.ps1 logs`
2. Review: `DOCKER_FRONTEND_README.md`
3. Verify Docker is running: `docker ps`
4. Test backend: `curl http://localhost:8080/health`
5. Check browser console (F12) for frontend errors

---

**Ready to test? Run: `.\test-frontend.ps1`** 🚀
