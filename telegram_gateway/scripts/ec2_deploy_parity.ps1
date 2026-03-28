param(
    [string]$Ec2Host = "3.110.182.233",
    [string]$User = "ubuntu",
    [string]$KeyPath = "./ai-microservices-key.pem",
    [string]$AppPath = "",
    [string]$Branch = "main",
    [switch]$UseDeployTar,
    [string]$DeployTarPath = "./deploy.tar.gz",
    [switch]$SkipPrune,
    [switch]$SkipPollerEnsure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Ssh {
    param(
        [Parameter(Mandatory = $true)][string]$Command
    )

    $sshArgs = @(
        "-o", "StrictHostKeyChecking=no",
        "-i", $KeyPath,
        "$User@$Ec2Host",
        $Command
    )

    & ssh @sshArgs
}

function Resolve-AppPath {
    if (-not [string]::IsNullOrWhiteSpace($AppPath)) {
        return $AppPath
    }

        $cmd = 'for p in /home/ubuntu/telegram_gateway /home/ubuntu/code/MILO/Telegram_services/telegram_gateway; do if [ -f "$p/docker-compose.yml" ]; then echo "$p"; exit 0; fi; done; echo ""'

    $resolved = (Invoke-Ssh -Command $cmd | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        throw "Could not auto-detect app path on EC2. Pass -AppPath explicitly."
    }

    return $resolved
}

function Ensure-Prerequisites {
    if (-not (Test-Path -LiteralPath $KeyPath)) {
        throw "Key file not found: $KeyPath"
    }

    if ($UseDeployTar -and -not (Test-Path -LiteralPath $DeployTarPath)) {
        throw "Deploy tarball not found: $DeployTarPath"
    }
}

Ensure-Prerequisites
$resolvedPath = Resolve-AppPath

Write-Host "Target: $User@$Ec2Host"
Write-Host "App path: $resolvedPath"

Write-Host "[1/7] Preflight checks"
Invoke-Ssh -Command "set -e; cd $resolvedPath; test -f docker-compose.yml; if [ ! -f .env ]; then echo '.env missing' >&2; exit 1; fi; sudo docker compose config >/dev/null"

if ($UseDeployTar) {
    Write-Host "[2/7] Uploading deploy artifact"
    $scpArgs = @(
        "-o", "StrictHostKeyChecking=no",
        "-i", $KeyPath,
        $DeployTarPath,
        "$User@$Ec2Host:~/deploy.tar.gz"
    )
    & scp @scpArgs

    Write-Host "[3/7] Extracting deploy artifact"
    Invoke-Ssh -Command "set -e; cd $resolvedPath; tar -xzf ~/deploy.tar.gz"
} else {
    Write-Host "[2/7] Pulling latest git code"
    Invoke-Ssh -Command "set -e; cd $resolvedPath; git fetch --all --prune; git checkout $Branch; git pull origin $Branch"

    Write-Host "[3/7] Git sync complete"
}

if (-not $SkipPrune) {
    Write-Host "[4/7] Pruning Docker cache"
    Invoke-Ssh -Command "set -e; sudo docker system prune -f"
} else {
    Write-Host "[4/7] Skipping Docker prune"
}

Write-Host "[5/7] Rebuilding + recreating containers"
Invoke-Ssh -Command "set -e; cd $resolvedPath; mkdir -p data; sudo chown -R 1000:1000 data; sudo docker compose up -d --build --force-recreate"

Write-Host "[6/7] Waiting for health checks"
Start-Sleep -Seconds 20
Invoke-Ssh -Command "set -e; cd $resolvedPath; sudo docker ps --format 'table {{.Names}}\t{{.Status}}'"

if (-not $SkipPollerEnsure) {
    Write-Host "[7/7] Ensuring detached poller screen session"
    $pollerCmd = @"
set -e
cd $resolvedPath
if screen -ls | grep -q '\\.poller'; then
  echo 'poller session already active'
else
  screen -dmS poller bash -lc 'cd $resolvedPath; if [ -f venv/bin/activate ]; then source venv/bin/activate; fi; python3 local_poller.py >> poller.log 2>&1'
  echo 'poller session created'
fi
screen -ls || true
"@
    Invoke-Ssh -Command $pollerCmd
} else {
    Write-Host "[7/7] Skipping poller ensure"
}

Write-Host "\nDeploy parity run complete."
Write-Host "Recommended manual check: send /start to the bot and verify response."
