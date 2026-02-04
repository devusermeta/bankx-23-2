# BankX Frontend Docker Test Script
# This script helps you build and test the frontend Docker image

param(
    [Parameter(Position=0)]
    [ValidateSet('build', 'start', 'stop', 'logs', 'test', 'clean')]
    [string]$Action = 'test'
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Info {
    Write-Host $args -ForegroundColor Cyan
}

function Write-Success {
    Write-Host $args -ForegroundColor Green
}

function Write-Warning {
    Write-Host $args -ForegroundColor Yellow
}

function Write-Error {
    Write-Host $args -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Blue
Write-Host "BankX Frontend Docker Test" -ForegroundColor Blue
Write-Host "======================================" -ForegroundColor Blue
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker is not running. Please start Docker Desktop."
    exit 1
}

switch ($Action) {
    'build' {
        Write-Info "Building frontend Docker image..."
        docker build -t bankx-frontend:test .
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Frontend image built successfully!"
            Write-Host ""
            Write-Info "Image details:"
            docker images bankx-frontend:test
        } else {
            Write-Error "✗ Build failed!"
            exit 1
        }
    }
    
    'start' {
        Write-Info "Starting frontend container..."
        Write-Warning "Make sure your backend is running on port 8080!"
        Write-Host ""
        
        docker-compose -f docker-compose.test.yml up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Frontend container started!"
            Write-Host ""
            Write-Info "Access frontend at: http://localhost:8081"
            Write-Host ""
            Write-Info "To view logs: .\test-frontend.ps1 logs"
            Write-Info "To stop: .\test-frontend.ps1 stop"
        } else {
            Write-Error "✗ Failed to start container!"
            exit 1
        }
    }
    
    'stop' {
        Write-Info "Stopping frontend container..."
        docker-compose -f docker-compose.test.yml down
        Write-Success "✓ Container stopped!"
    }
    
    'logs' {
        Write-Info "Showing frontend logs (Ctrl+C to exit)..."
        docker-compose -f docker-compose.test.yml logs -f
    }
    
    'test' {
        Write-Info "Running complete test..."
        Write-Host ""
        
        # Step 1: Build
        Write-Info "Step 1: Building image..."
        docker build -t bankx-frontend:test .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "✗ Build failed!"
            exit 1
        }
        Write-Success "✓ Build successful!"
        Write-Host ""
        
        # Step 2: Check if backend is running
        Write-Info "Step 2: Checking if backend is running on port 8080..."
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -UseBasicParsing
            Write-Success "✓ Backend is running!"
        } catch {
            Write-Warning "⚠ Backend is not running on port 8080"
            Write-Host ""
            Write-Host "Please start your backend first:"
            Write-Host "  cd ..\..\copilot"
            Write-Host "  .venv\Scripts\Activate.ps1"
            Write-Host "  `$env:PROFILE=`"dev`""
            Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8080"
            Write-Host ""
            $continue = Read-Host "Continue anyway? (y/n)"
            if ($continue -ne 'y') {
                exit 1
            }
        }
        Write-Host ""
        
        # Step 3: Start container
        Write-Info "Step 3: Starting frontend container..."
        docker-compose -f docker-compose.test.yml up -d
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "✗ Failed to start container!"
            exit 1
        }
        Write-Success "✓ Container started!"
        Write-Host ""
        
        # Step 4: Wait for container to be healthy
        Write-Info "Step 4: Waiting for container to be healthy..."
        $maxAttempts = 30
        $attempt = 0
        
        while ($attempt -lt $maxAttempts) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 2 -UseBasicParsing
                if ($response.StatusCode -eq 200) {
                    Write-Success "✓ Frontend is healthy!"
                    break
                }
            } catch {
                # Continue waiting
            }
            
            $attempt++
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline
        }
        
        if ($attempt -eq $maxAttempts) {
            Write-Error "`n✗ Container failed to become healthy!"
            Write-Host ""
            Write-Info "Showing logs:"
            docker-compose -f docker-compose.test.yml logs
            exit 1
        }
        Write-Host ""
        Write-Host ""
        
        # Step 5: Test frontend
        Write-Info "Step 5: Testing frontend..."
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8081" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "✓ Frontend is responding!"
            }
        } catch {
            Write-Error "✗ Frontend is not responding!"
            exit 1
        }
        Write-Host ""
        
        # Success!
        Write-Host ""
        Write-Success "========================================" 
        Write-Success "✓ ALL TESTS PASSED!" 
        Write-Success "========================================" 
        Write-Host ""
        Write-Info "Frontend is running at: http://localhost:8081"
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "  1. Open http://localhost:8081 in your browser"
        Write-Host "  2. Test the application"
        Write-Host "  3. View logs: .\test-frontend.ps1 logs"
        Write-Host "  4. When done: .\test-frontend.ps1 stop"
        Write-Host ""
    }
    
    'clean' {
        Write-Warning "This will remove the test container and image."
        $confirm = Read-Host "Are you sure? (y/n)"
        
        if ($confirm -eq 'y') {
            Write-Info "Stopping and removing container..."
            docker-compose -f docker-compose.test.yml down
            
            Write-Info "Removing image..."
            docker rmi bankx-frontend:test -f
            
            Write-Success "✓ Cleanup complete!"
        } else {
            Write-Info "Cleanup cancelled."
        }
    }
    
    default {
        Write-Error "Invalid action: $Action"
        Write-Host ""
        Write-Host "Usage: .\test-frontend.ps1 [action]"
        Write-Host ""
        Write-Host "Actions:"
        Write-Host "  build  - Build the frontend Docker image"
        Write-Host "  start  - Start the frontend container"
        Write-Host "  stop   - Stop the frontend container"
        Write-Host "  logs   - View container logs"
        Write-Host "  test   - Run complete test (build + start + verify)"
        Write-Host "  clean  - Remove container and image"
        Write-Host ""
        Write-Host "Default action is 'test'"
        exit 1
    }
}

Write-Host ""
