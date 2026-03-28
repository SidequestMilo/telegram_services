param(
    [string]$Ec2Host = "3.110.182.233",
    [string]$User = "ubuntu",
    [string]$KeyPath = "./ai-microservices-key.pem",
    [string]$AppPath = ""
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

if (-not (Test-Path -LiteralPath $KeyPath)) {
    throw "Key file not found: $KeyPath"
}

$resolvedPath = Resolve-AppPath
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputPath = Join-Path -Path (Get-Location) -ChildPath "ec2_audit_$timestamp.log"

"==== EC2 Audit: $Ec2Host ($resolvedPath) ====" | Tee-Object -FilePath $outputPath

function Run-Section {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Command
    )

    "`n----- $Title -----" | Tee-Object -FilePath $outputPath -Append
    $result = Invoke-Ssh -Command $Command | Out-String
    $result.TrimEnd() | Tee-Object -FilePath $outputPath -Append
}

Run-Section -Title "Host + Docker Versions" -Command "set -e; hostname; uname -a; docker --version; docker compose version"
Run-Section -Title "App Path + Files" -Command "set -e; cd $resolvedPath; pwd; ls -la"
Run-Section -Title "Compose Services + Effective Config" -Command "set -e; cd $resolvedPath; sudo docker compose config --services; echo '---'; sudo docker compose config | sed -n '1,240p'"
Run-Section -Title "Container Status" -Command "set -e; cd $resolvedPath; sudo docker compose ps; echo '---'; sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
Run-Section -Title "Screen + Poller Process" -Command "set -e; screen -ls || true; echo '---'; ps -ef | grep -E 'local_poller.py|SCREEN' | grep -v grep || true"
Run-Section -Title "Environment Keys (Values Redacted)" -Command "set -e; cd $resolvedPath; if [ -f .env ]; then sed 's/=.*$/=***REDACTED***/' .env; else echo '.env missing'; fi"
Run-Section -Title "Telegram Webhook Info" -Command "set -e; cd $resolvedPath; TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' .env 2>/dev/null | cut -d= -f2-); if [ -n \"$TOKEN\" ]; then curl -s https://api.telegram.org/bot$TOKEN/getWebhookInfo; else echo 'TELEGRAM_BOT_TOKEN missing in .env'; fi"
Run-Section -Title "Gateway Logs (Last 200)" -Command "set -e; cd $resolvedPath; sudo docker compose logs --tail=200 telegram_gateway"

"`nSaved audit report to: $outputPath" | Tee-Object -FilePath $outputPath -Append
