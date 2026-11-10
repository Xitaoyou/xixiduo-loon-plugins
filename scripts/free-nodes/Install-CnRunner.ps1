# Run once as Administrator on the Guangzhou Windows Server.
[CmdletBinding()]
param(
    [string]$RunnerUrl = 'https://github.com/actions/runner/releases/download/v2.338.2/actions-runner-win-x64-2.338.2.zip',
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$RunnerSha256 = 'a1f17aa987fc8158bc7521d284912267a0d01b7c2c4684b33c86783b5e8221cc',
    [SecureString]$RegistrationToken
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run as Administrator on the ECS server.' }
if ((Get-CimInstance Win32_OperatingSystem).ProductType -eq 1) { throw 'Windows Server required.' }
if ($RunnerUrl -notmatch '^https://github\.com/actions/runner/releases/download/v[0-9.]+/actions-runner-win-x64-[0-9.]+\.zip$') { throw 'Official Windows runner URL required.' }
$root = 'C:\ProgramData\xixiduo-cn-runner'
if (Test-Path "$root\runner\.runner") {
    if (-not (Test-Path "$root\runner\.service")) { throw 'Partially registered runner: preserve files and inspect diagnostics before repairing registration.' }
    $serviceName = (Get-Content "$root\runner\.service" -Raw).Trim()
    $serviceInfo = Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $serviceName }
    if (-not $serviceInfo -or $serviceInfo.StartName -notmatch '\\cnrunner$') { throw 'Runner service identity mismatch.' }
    Set-Service $serviceName -StartupType Automatic
    Start-Service $serviceName
    Write-Host 'READY: Existing non-administrator runner service is running.'
    exit 0
}
$userName = 'cnrunner'
$existing = Get-LocalUser -Name $userName -ErrorAction SilentlyContinue
if ($existing -and -not (Test-Path "$root\managed-install-v1")) { throw 'Unmanaged cnrunner account exists; refusing to change it.' }
New-Item -ItemType Directory -Path $root -Force | Out-Null
& icacls.exe $root /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Root directory ACL failed.' }
Set-Content -LiteralPath "$root\managed-install-v1" -Value 'xixiduo-cn-probe-v1' -Encoding Ascii
function Get-VerifiedArchive([string]$Url, [string]$Hash, [string]$Path) {
    if ((Test-Path $Path) -and (Get-FileHash $Path -Algorithm SHA256).Hash -eq $Hash) { return }
    $partial = $Path + '.download'
    if ((Test-Path $partial) -and (Get-FileHash $partial -Algorithm SHA256).Hash -eq $Hash) {
        Move-Item -LiteralPath $partial -Destination $Path -Force
        return
    }
    Write-Host ('Downloading official archive (resuming partial file): ' + (Split-Path $Path -Leaf))
    & curl.exe --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 300 --speed-limit 2048 --speed-time 30 --retry 0 --continue-at - --output $partial $Url
    if ($LASTEXITCODE -ne 0) { throw 'Official download interrupted. Partial file retained for the next attempt.' }
    if ((Get-FileHash ($Path + '.download') -Algorithm SHA256).Hash -ne $Hash) { throw 'Official archive checksum mismatch.' }
    Move-Item -LiteralPath ($Path + '.download') -Destination $Path -Force
}
Get-VerifiedArchive $RunnerUrl $RunnerSha256 "$root\runner.zip"
Get-VerifiedArchive 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3' "$root\python.zip"
New-Item -ItemType Directory -Path "$root\runner" -Force | Out-Null
Expand-Archive -LiteralPath "$root\runner.zip" -DestinationPath "$root\runner" -Force
Expand-Archive -LiteralPath "$root\python.zip" -DestinationPath "$root\python" -Force
$signature = Get-AuthenticodeSignature "$root\python\python.exe"
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'Python executable signature validation failed.' }
if (-not $RegistrationToken) { $RegistrationToken = Read-Host 'One-hour GitHub runner registration token' -AsSecureString }
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
$password = [Convert]::ToBase64String($bytes) + '!aA7'
if ($existing) { Set-LocalUser -Name $userName -Password (ConvertTo-SecureString $password -AsPlainText -Force) } else {
    New-LocalUser -Name $userName -Password (ConvertTo-SecureString $password -AsPlainText -Force) -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
}
$admins = Get-LocalGroup -SID 'S-1-5-32-544'
$account = Get-LocalUser -Name $userName
if (Get-LocalGroupMember -Group $admins.Name | Where-Object { $_.SID -eq $account.SID }) { throw 'Runner account must not be an administrator.' }
$users = Get-LocalGroup -SID 'S-1-5-32-545'
if (-not (Get-LocalGroupMember -Group $users.Name | Where-Object { $_.SID -eq $account.SID })) { Add-LocalGroupMember -Group $users.Name -Member $userName }
New-Item -ItemType Directory -Path "$root\runner" -Force | Out-Null
$sid = (Get-LocalUser -Name $userName).SID.Value
& icacls.exe $root /grant:r ("*${sid}:(RX)") | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Runner directory ACL failed.' }
New-Item -ItemType Directory -Path "$root\state" -Force | Out-Null
foreach ($folder in @("$root\runner", "$root\state")) {
    & icacls.exe $folder /grant:r ("*${sid}:(OI)(CI)M") | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Runner writable directory ACL failed.' }
}
& icacls.exe "$root\python" /grant:r ("*${sid}:(OI)(CI)(RX)") | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Python directory ACL failed.' }
$credential = New-Object System.Net.NetworkCredential('', $RegistrationToken)
Push-Location "$root\runner"
try {
    & .\config.cmd --unattended --url 'https://github.com/Xitaoyou/xixiduo-cn-probe' --token $credential.Password --name 'guangzhou-windows' --labels 'cn-guangzhou' --work '_work' --runasservice --windowslogonaccount ".\$userName" --windowslogonpassword $password
    if ($LASTEXITCODE -ne 0) { throw 'Runner registration failed; no success claimed. Inspect local runner diagnostics before retrying.' }
} finally {
    Pop-Location
    $password = $null
    $credential = $null
}
$serviceName = (Get-Content "$root\runner\.service" -Raw).Trim()
$serviceInfo = Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $serviceName }
if (-not $serviceInfo -or $serviceInfo.StartName -notmatch '\\cnrunner$') { throw 'Runner service account mismatch.' }
Set-Service $serviceName -StartupType Automatic
Start-Service $serviceName
if ((Get-Service $serviceName).Status -ne 'Running') { throw 'Runner service is not running.' }
$sshService = Get-Service sshd -ErrorAction SilentlyContinue
if ($sshService -and $sshService.Status -eq 'Stopped') {
    Get-CimInstance Win32_Process -Filter "Name='sshd.exe'" |
        Where-Object { $_.CommandLine -match '(?:\s)-(?:D|ddd)(?:\s|$)' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
}
Write-Host 'READY: Non-administrator Guangzhou runner service is running. No node tests were started.'
