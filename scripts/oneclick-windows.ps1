# GetSomeHints 一键部署（Windows）
# 适用于：无环境或仅有系统的 Windows 10/11
# 用法：在项目根目录右键“在终端中打开”，执行：
#   powershell -ExecutionPolicy Bypass -File scripts\oneclick-windows.ps1
# 或：在资源管理器中双击运行 scripts\oneclick-windows.bat
# 完成后在浏览器打开提示的链接即可使用

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$RepoRoot\backend") -or -not (Test-Path "$RepoRoot\frontend")) {
  $RepoRoot = Get-Location
}
Set-Location $RepoRoot

Write-Host "========== GetSomeHints 一键部署 (Windows) ==========" -ForegroundColor Cyan
Write-Host "项目目录: $RepoRoot"
Write-Host ""

# ----- 1. 检测/安装 Python 与 Node -----
$needPython = $false
$needNode = $false
try {
  $pv = (python --version 2>&1) -replace "Python ", ""
  $v = [int]($pv.Split(".")[0]), [int]($pv.Split(".")[1])
  if ($v[0] -lt 3 -or ($v[0] -eq 3 -and $v[1] -lt 9)) { $needPython = $true }
} catch { $needPython = $true }

try {
  $nv = (node -v 2>&1) -replace "v", ""
  $major = [int]($nv.Split(".")[0])
  if ($major -lt 18) { $needNode = $true }
} catch { $needNode = $true }

if ($needPython -or $needNode) {
  Write-Host "[1/6] 正在安装运行环境（若已安装可忽略）..." -ForegroundColor Yellow
  if ($needPython) {
    try {
      winget install --id Python.Python.3.11 -e --silent --accept-package-agreements
      $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } catch {
      Write-Host "请从 https://www.python.org/downloads/ 安装 Python 3.11+ 并勾选 Add to PATH，然后重新运行本脚本。" -ForegroundColor Red
      Start-Process "https://www.python.org/downloads/"
      exit 1
    }
  }
  if ($needNode) {
    try {
      winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements
      $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } catch {
      Write-Host "请从 https://nodejs.org/ 安装 Node.js LTS，然后重新运行本脚本。" -ForegroundColor Red
      Start-Process "https://nodejs.org/"
      exit 1
    }
  }
  Write-Host "若刚安装 Python/Node，请关闭本窗口，重新打开终端后再运行一次本脚本。" -ForegroundColor Yellow
  exit 0
} else {
  Write-Host "[1/6] 运行环境已满足 (Python, Node)" -ForegroundColor Green
}
Write-Host ""

# ----- 2. 后端：虚拟环境 + 依赖 -----
Write-Host "[2/6] 配置后端 (Python)" -ForegroundColor Cyan
$Backend = Join-Path $RepoRoot "backend"
Set-Location $Backend
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
pip install -q -r requirements.txt
playwright install chromium 2>$null
Write-Host "  后端依赖就绪" -ForegroundColor Green
Write-Host ""

# ----- 3. 后端 .env -----
if (-not (Test-Path "$Backend\.env")) {
  Copy-Item "$Backend\.env.example" "$Backend\.env"
  (Get-Content "$Backend\.env") -replace "API_PORT=.*", "API_PORT=8000" | Set-Content "$Backend\.env"
  Write-Host "[3/6] 已生成 backend\.env（默认端口 8000）" -ForegroundColor Green
} else {
  Write-Host "[3/6] backend\.env 已存在，跳过"
}
Write-Host ""

# ----- 4. 前端：依赖 -----
Write-Host "[4/6] 配置前端 (Node)" -ForegroundColor Cyan
$Frontend = Join-Path $RepoRoot "frontend"
Set-Location $Frontend
if (-not (Test-Path "node_modules")) {
  npm install --silent
}
@"
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
"@ | Set-Content "$Frontend\.env" -Encoding utf8
Write-Host "  前端依赖就绪" -ForegroundColor Green
Write-Host ""

# ----- 5. 启动服务 -----
Write-Host "[5/6] 启动后端与前端服务" -ForegroundColor Cyan
$ApiPort = 8000
$FrontPort = 5173

$BackendLog = Join-Path $RepoRoot "backend.log"
$FrontendLog = Join-Path $RepoRoot "frontend.log"

Set-Location $Backend
& ".\.venv\Scripts\Activate.ps1"
$env:API_PORT = $ApiPort
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", $ApiPort, "--reload" -WindowStyle Hidden -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendLog

Start-Sleep -Seconds 3
for ($i = 1; $i -le 15; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/api/debug/whoami" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { break }
  } catch {}
  Start-Sleep -Seconds 1
}

Set-Location $Frontend
Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--host", "0.0.0.0", "--port", $FrontPort -WindowStyle Hidden -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendLog

Start-Sleep -Seconds 5
for ($i = 1; $i -le 20; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$FrontPort" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { break }
  } catch {}
  Start-Sleep -Seconds 1
}

Write-Host "  后端端口: $ApiPort" -ForegroundColor Green
Write-Host "  前端端口: $FrontPort" -ForegroundColor Green
Write-Host ""

# ----- 6. 打开浏览器 -----
Write-Host "[6/6] 部署完成" -ForegroundColor Green
$AppUrl = "http://localhost:$FrontPort"
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "  点开下面链接即可使用：" -ForegroundColor Yellow
Write-Host "  $AppUrl" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""
Write-Host "日志: backend.log / frontend.log"
Write-Host "关闭服务: 在任务管理器中结束 python / node 进程，或关闭本终端窗口后重新打开并运行 scripts\oneclick-windows-stop.ps1"
Write-Host ""

Start-Process $AppUrl
