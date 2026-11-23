#Requires -Version 5.1
<#
.SYNOPSIS
  Diagnoza wolnego tworzenia worktree w Agent Managerze Kilo (VS Code, Windows).

.DESCRIPTION
  Mierzy osobno trzy warstwy kosztu, zeby nie optymalizowac na slepo:
    1) uruchomienie procesu (AV/EDR, polityka firmy),
    2) lancuch konfiguracji git (globalna/systemowa, include.path, profile przekierowane),
    3) operacje na repo (status -uall, for-each-ref, liczba untracked).
  Domyslnie NICZEGO nie zmienia. -Fix stosuje bezpieczne ustawienia git globalnego i drukuje rollback.
  -WorktreeTest tworzy i usuwa dwa worktree pod rzad (cold start vs stala wada).

.EXAMPLE
  .\kilo-worktree-doctor.ps1 -RepoPath "$env:USERPROFILE\GitHub\ciahciach-skills"

.EXAMPLE
  .\kilo-worktree-doctor.ps1 -WorktreeTest

.EXAMPLE
  .\kilo-worktree-doctor.ps1 -Fix
#>
[CmdletBinding()]
param(
    [string]$RepoPath  = "",
    [switch]$Fix,
    [switch]$WorktreeTest,
    [string]$OutDir    = ""
)

$ErrorActionPreference = 'Continue'
$ProgressPreference    = 'SilentlyContinue'

$script:Checks   = New-Object System.Collections.ArrayList
$script:Findings = New-Object System.Collections.ArrayList

function Say {
    param([string]$Text, [string]$Color = "Gray")
    Write-Host $Text -ForegroundColor $Color
}

function Head {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=== " + $Text + " " + ("=" * [Math]::Max(0, 60 - $Text.Length))) -ForegroundColor Cyan
}

function Add-Check {
    param([string]$Name, [string]$Value, [string]$Verdict = "-", [string]$Note = "")
    $null = $script:Checks.Add([pscustomobject]@{
        name = $Name; value = $Value; verdict = $Verdict; note = $Note
    })
    $color = "Gray"
    if ($Verdict -eq "OK")   { $color = "Green" }
    if ($Verdict -eq "WARN") { $color = "Yellow" }
    if ($Verdict -eq "BAD")  { $color = "Red" }
    Write-Host ("  [{0,-4}] {1,-44} {2}" -f $Verdict, $Name, $Value) -ForegroundColor $color
    if ($Note -ne "") { Write-Host ("         -> " + $Note) -ForegroundColor DarkGray }
}

function Add-Finding {
    param([string]$Text)
    $null = $script:Findings.Add($Text)
}

function Measure-Proc {
    param([string]$Exe, [string[]]$ArgList = @(), [hashtable]$EnvVars = @{})
    $saved = @{}
    foreach ($k in $EnvVars.Keys) {
        $saved[$k] = [Environment]::GetEnvironmentVariable($k, 'Process')
        [Environment]::SetEnvironmentVariable($k, $EnvVars[$k], 'Process')
    }
    $sw   = [System.Diagnostics.Stopwatch]::StartNew()
    $out  = ""
    $code = -1
    try {
        $out  = (& $Exe @ArgList 2>&1 | Out-String).Trim()
        $code = $LASTEXITCODE
    } catch {
        $out = "ERR: " + $_.Exception.Message
    }
    $sw.Stop()
    foreach ($k in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($k, $saved[$k], 'Process')
    }
    return [pscustomobject]@{ ms = [int]$sw.ElapsedMilliseconds; exit = $code; out = $out }
}

function Get-Median {
    param($Values)
    $arr = @($Values | Where-Object { $_ -ne $null } | Sort-Object)
    if ($arr.Count -eq 0) { return 0 }
    $n = $arr.Count
    if (($n % 2) -eq 1) { return [int]$arr[[int](($n - 1) / 2)] }
    return [int](( $arr[$n / 2 - 1] + $arr[$n / 2] ) / 2)
}

function Format-Bytes {
    param([double]$Bytes)
    if ($Bytes -ge 1GB) { return ("{0:N1} GB" -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ("{0:N1} MB" -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ("{0:N0} KB" -f ($Bytes / 1KB)) }
    return ("{0:N0} B" -f $Bytes)
}

function Join-Opt {
    param([string]$Base, [string]$Child)
    if ([string]::IsNullOrWhiteSpace($Base)) { return "" }
    try { return (Join-Path $Base $Child) } catch { return "" }
}

# ---------------------------------------------------------------- setup
if ($RepoPath -eq "") { $RepoPath = (Get-Location).Path }
if (-not (Test-Path -LiteralPath $RepoPath)) {
    Say ("Nie ma takiego katalogu: " + $RepoPath) "Red"; exit 2
}
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path

$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) { Say "git nie jest na PATH - uruchom w terminalu, ktory widzi git." "Red"; exit 2 }
$git = $gitCmd.Source

$rp = Measure-Proc $git @('-C', $RepoPath, 'rev-parse', '--show-toplevel')
if ($rp.exit -ne 0) { Say ("To nie jest repo git: " + $RepoPath) "Red"; exit 2 }
$repoTop = $rp.out

Write-Host ""
Say ("kilo-worktree-doctor  |  " + $env:COMPUTERNAME + "  |  " + (Get-Date).ToString("yyyy-MM-dd HH:mm")) "White"
Say ("repo: " + $repoTop) "White"
Say ("git : " + $git) "DarkGray"

# ---------------------------------------------------------------- 1. koszt procesu
Head "1. Koszt uruchomienia procesu (podstawa)"

$verTimes = @()
1..5 | ForEach-Object { $verTimes += (Measure-Proc $git @('--version')).ms }
$verMed = Get-Median $verTimes
$verNote = "git --version x5: " + ($verTimes -join " / ") + " ms"
if ($verMed -le 250) {
    Add-Check "git --version (mediana)" "$verMed ms" "OK" $verNote
} elseif ($verMed -le 800) {
    Add-Check "git --version (mediana)" "$verMed ms" "WARN" "$verNote - podwyzszony koszt startu procesu"
} else {
    Add-Check "git --version (mediana)" "$verMed ms" "BAD" "$verNote - kazde git.exe placi ten koszt"
}

$cmdExe = Join-Opt $env:SystemRoot "System32\cmd.exe"
$cmdTimes = @()
if ($cmdExe -ne "" -and (Test-Path -LiteralPath $cmdExe)) {
    1..3 | ForEach-Object { $cmdTimes += (Measure-Proc $cmdExe @('/c', 'exit')).ms }
}
$cmdMed = Get-Median $cmdTimes
if ($cmdMed -gt 0) {
    if ($cmdMed -le 250) {
        Add-Check "cmd.exe /c exit (mediana)" "$cmdMed ms" "OK" "start innego procesu jest szybki"
    } else {
        Add-Check "cmd.exe /c exit (mediana)" "$cmdMed ms" "BAD" "caly system ma wolny start procesow (polityka/AV/EDR), nie tylko git"
    }
}

$procs = @(Get-Process -Name git -ErrorAction SilentlyContinue)
Add-Check "zywe procesy git" ([string]$procs.Count) $(if ($procs.Count -gt 6) { "WARN" } else { "OK" }) "w trakcie skanowania VS Code odpala ich rownolegle kilkanascie"

# ---------------------------------------------------------------- 2. lancuch config
Head "2. Lancuch konfiguracji git"

$tplPlain = Measure-Proc $git @('-C', $RepoPath, 'config', '--get', 'commit.template')
$tplClean = Measure-Proc $git @('-C', $RepoPath, 'config', '--get', 'commit.template') -EnvVars @{
    GIT_CONFIG_NOSYSTEM = '1'
    GIT_CONFIG_GLOBAL   = 'NUL'
}
if ($tplPlain.ms -le 300) {
    Add-Check "config --get (pelny lancuch)" ("{0} ms" -f $tplPlain.ms) "OK"
} elseif ($tplClean.ms -gt 0 -and $tplClean.ms -lt ($tplPlain.ms / 3)) {
    Add-Check "config --get (pelny lancuch)" ("{0} ms" -f $tplPlain.ms) "BAD" ("bez configu globalnego/systemowego: {0} ms - to wina plikow konfiguracji" -f $tplClean.ms)
} else {
    Add-Check "config --get (pelny lancuch)" ("{0} ms" -f $tplPlain.ms) "BAD" ("bez configu: {0} ms - koszt jest w samym procesie, nie w configu" -f $tplClean.ms)
}
Add-Check "config --get (bez globalnego)" ("{0} ms" -f $tplClean.ms) "OK"

$origins = Measure-Proc $git @('-C', $RepoPath, 'config', '--list', '--show-origin')
$cfgFiles = @()
if ($origins.out -ne "") {
    $cfgFiles = $origins.out -split "`n" | ForEach-Object {
        if ($_ -match '^file:(.+?)\t') { $matches[1] }
    } | Sort-Object -Unique
}
$oddCfg = @($cfgFiles | Where-Object { $_ -match '^(\\\\|//)' })
if ($oddCfg.Count -gt 0) {
    Add-Check "pliki configu poza dyskiem lokalnym" ($oddCfg -join "; ") "BAD" "config z UNC/sieci spowalnia KAZDA komende git"
} else {
    Add-Check "pliki configu" ([string]$cfgFiles.Count + " lokalnych") "OK" ($cfgFiles -join " | ")
}
$missingCfg = @($cfgFiles | Where-Object { $_ -match '^[A-Za-z]:' -and -not (Test-Path -LiteralPath $_ -ErrorAction SilentlyContinue) })
if ($missingCfg.Count -gt 0) {
    Add-Check "config wskazuje nieistniejacy plik" ($missingCfg -join "; ") "WARN" "include.path do brakujacego pliku potrafi kosztowac sekundy"
}

foreach ($key in @('core.fsmonitor', 'core.untrackedCache', 'core.fscache', 'core.preloadindex', 'core.hooksPath', 'gc.auto')) {
    $v = (Measure-Proc $git @('-C', $RepoPath, 'config', '--get', $key)).out
    if ($v -ne "") { Add-Check $key $v "-" }
}
$fsm = (Measure-Proc $git @('-C', $RepoPath, 'config', '--get', 'core.fsmonitor')).out
if ($fsm -ne "" -and $fsm -ne "false" -and $fsm -ne "true") {
    if (-not (Test-Path -LiteralPath $fsm)) {
        Add-Check "core.fsmonitor -> plik" $fsm "BAD" "wskazuje nieistniejaca sciezke - git placi timeout przy kazdej komendzie"
    }
}

# ---------------------------------------------------------------- 3. operacje na repo
Head "3. Operacje na repo (to, co robi rozszerzenie Git w VS Code)"

$statusRun = Measure-Proc $git @('-C', $RepoPath, 'status', '-z', '-uall', '--porcelain=v1')
$ops = @(
    @{ n = 'rev-parse --show-toplevel'; a = @('rev-parse', '--show-toplevel') },
    @{ n = 'config --local -l';         a = @('config', '--local', '-l') },
    @{ n = 'for-each-ref';              a = @('for-each-ref') },
    @{ n = 'merge-base HEAD HEAD';      a = @('merge-base', 'HEAD', 'HEAD') },
    @{ n = 'count-objects -v';          a = @('count-objects', '-v') },
    @{ n = 'check-ignore';              a = @('check-ignore', '--stdin') }
)
$repoTimes = @()
foreach ($op in $ops) {
    $r = Measure-Proc $git (@('-C', $RepoPath) + $op.a)
    $repoTimes += $r.ms
    $v = "-"
    if ($r.ms -gt 2000) { $v = "WARN" }
    if ($r.ms -gt 8000) { $v = "BAD" }
    Add-Check $op.n ("{0} ms" -f $r.ms) $v
}
$v = "-"
if ($statusRun.ms -gt 1500) { $v = "WARN" }
if ($statusRun.ms -gt 5000) { $v = "BAD" }
Add-Check "status -z -uall" ("{0} ms" -f $statusRun.ms) $v "VS Code Agent Host daje gitowi twarde 5000 ms - powyzej tego stan sesji nie dochodzi"
if ($statusRun.ms -gt 5000) {
    Add-Finding ("status -z -uall = {0} ms, a Agent Host VS Code przerywa git po 5000 ms. Dlatego w logu jest 'git status timed out after 5000ms' i 'Not reporting session git state' - worktree wyglada jak zawieszony, choc git pracuje." -f $statusRun.ms)
}
$repoMed = Get-Median $repoTimes

# ---------------------------------------------------------------- 4. inwentarz repo
Head "4. Inwentarz repo"

$plainStatus = Measure-Proc $git @('-C', $RepoPath, 'status', '--porcelain=v1', '-uall')
$stLines  = @($plainStatus.out -split "`n" | Where-Object { $_.Trim().Length -gt 0 })
$untracked = @($stLines | Where-Object { $_ -like '??*' }).Count
$trackedRun = Measure-Proc $git @('-C', $RepoPath, 'ls-files')
$tracked = @($trackedRun.out -split "`n" | Where-Object { $_.Trim().Length -gt 0 }).Count

$gitDir = (Measure-Proc $git @('-C', $RepoPath, 'rev-parse', '--absolute-git-dir')).out
$dotGitSize = 0
if ($gitDir -ne "" -and (Test-Path -LiteralPath $gitDir)) {
    $sum = Get-ChildItem -LiteralPath $gitDir -Recurse -Force -File -ErrorAction SilentlyContinue |
           Measure-Object -Property Length -Sum
    if ($sum -and $sum.Sum) { $dotGitSize = $sum.Sum }
}

$refs    = (Measure-Proc $git @('-C', $RepoPath, 'for-each-ref', '--format=%(refname)')).out
$refCount = @($refs -split "`n" | Where-Object { $_.Trim().Length -gt 0 }).Count
$wtList  = (Measure-Proc $git @('-C', $RepoPath, 'worktree', 'list', '--porcelain')).out
$wtCount = @($wtList -split "`n" | Where-Object { $_ -like 'worktree *' }).Count

Add-Check "pliki sledzone"       ([string]$tracked) "OK"
$v = "OK"
if ($untracked -gt 5000)  { $v = "BAD" }
elseif ($untracked -gt 1000) { $v = "WARN" }
Add-Check "pliki nietracked" ([string]$untracked) $v "status -uall chodzi po kazdym z nich"
$v = "OK"
if ($dotGitSize -gt 500MB) { $v = "WARN" }
Add-Check ".git na dysku" (Format-Bytes $dotGitSize) $v
Add-Check "refy (branch+e tagi)" ([string]$refCount) "-"
$v = "OK"
if ($wtCount -gt 5) { $v = "WARN" }
Add-Check "istniejace worktree" ([string]$wtCount) $v "VS Code skanuje kazdy otwarty jako osobne repo"

if ($untracked -gt 1000) {
    Add-Finding ("W repo jest {0} plikow nietracked - kazde 'status -uall' je odwiedza. Dopisz je do .gitignore albo uzyj sparse checkout." -f $untracked)
}

# ---------------------------------------------------------------- 5. srodowisko
Head "5. Srodowisko (dysk, AV/EDR, ustawienia)"

$item = Get-Item -LiteralPath $RepoPath -Force
$isReparse = (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
Add-Check "repo to reparse point" ([string]$isReparse) $(if ($isReparse) { "WARN" } else { "OK" }) "OneDrive/DFS/symlink pod repo = kazdy stat idzie przez filtr"
$profilePath = $env:USERPROFILE
$onedriveNames = @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer) | Where-Object { $_ }
$inOneDrive = $false
foreach ($od in $onedriveNames) { if ($RepoPath.StartsWith($od, 'OrdinalIgnoreCase')) { $inOneDrive = $true } }
if ($RepoPath -match '\\OneDrive') { $inOneDrive = $true }
Add-Check "repo w OneDrive" ([string]$inOneDrive) $(if ($inOneDrive) { "BAD" } else { "OK" }) "folder syncowany potrafi mnozyc koszt IO"

$drive = ""
try { $drive = (Split-Path -Qualifier $RepoPath -ErrorAction Stop) } catch { $drive = "" }
$freeTxt = "?"
if ($drive -ne "") {
    try {
        $d = Get-PSDrive -Name $drive.TrimEnd(':') -ErrorAction Stop
        $freeTxt = (Format-Bytes $d.Free) + " wolne z " + (Format-Bytes ($d.Free + $d.Used))
    } catch { }
}
Add-Check ("dysk " + $(if ($drive -ne "") { $drive } else { "(nie ustalono)" })) $freeTxt "-"

$defender = "brak"
try {
    $mp = Get-MpPreference -ErrorAction Stop
    $exPaths = @($mp.ExclusionPath)
    $exProcs = @($mp.ExclusionProcess)
    $hits = @($exPaths | Where-Object { $_ -and $RepoPath.StartsWith($_, 'OrdinalIgnoreCase') })
    $procHit = @($exProcs | Where-Object { $_ -match 'git' })
    $defender = "wykluczen: " + $exPaths.Count + " sciezek / " + $exProcs.Count + " procesow"
    if ($hits.Count -gt 0) { $defender += " | repo WYKLUCZONE" }
    else { $defender += " | repo NIE wykluczone" }
    if ($procHit.Count -gt 0) { $defender += " | git.exe wykluczony" }
    else { $defender += " | git.exe NIE wykluczony" }
} catch { $defender = "nie odczytano (brak uprawnien lub inny AV)" }
Add-Check "Defender / wykluczenia" $defender "WARN" "bez wykluczenia git.exe kazdy spawn placi skan"

$edr = @()
try {
    $edr = @(Get-Service -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match 'CrowdStrike|Falcon|Sentinel|Cortex|XDR|Sophos|McAfee|Symantec|Trellix|Bitdefender|ESET|Kaspersky|Cybereason|Carbon' } |
        ForEach-Object { $_.DisplayName + " (" + $_.Status + ")" })
} catch { }
if ($edr.Count -gt 0) {
    Add-Check "agent bezpieczenstwa" ($edr -join "; ") "WARN" "to glowny podejrzany o koszt per-proces na sluzbowym laptopie"
} else {
    Add-Check "agent bezpieczenstwa" "nie wykryto" "-"
}

$settingsPath = Join-Opt $env:APPDATA "Code\User\settings.json"
if ($settingsPath -ne "" -and (Test-Path -LiteralPath $settingsPath)) {
    $keys = @('"git.autofetch"', '"git.autorefresh"', '"git.autoRepositoryDetection"',
              '"git.repositoryScanMaxDepth"', '"git.scanRepositories"', '"git.decorations.enabled"',
              '"git.ignoreLimitWarning"', '"files.watcherExclude"', '"search.followSymlinks"',
              '"snapshot"', '"kilo.')
    $found = @()
    foreach ($line in (Get-Content -LiteralPath $settingsPath)) {
        foreach ($k in $keys) {
            if ($line -match [regex]::Escape($k)) { $found += $line.Trim() }
        }
    }
    if ($found.Count -gt 0) {
        foreach ($f in ($found | Sort-Object -Unique)) { Add-Check "VS Code" $f "-" }
    } else {
        Add-Check "VS Code settings" "brak wpisow git.*/snapshot" "WARN" "czyli autofetch i autorefresh na domyslnych (wlaczone)"
    }
} else {
    Add-Check "VS Code settings.json" "nie znaleziono" "-"
}

foreach ($kiloCfg in @((Join-Opt $env:USERPROFILE ".config\kilo\kilo.jsonc"), (Join-Path $RepoPath ".kilo\kilo.jsonc"))) {
    if ($kiloCfg -ne "" -and (Test-Path -LiteralPath $kiloCfg)) {
        $lines = @(Get-Content -LiteralPath $kiloCfg | Where-Object { $_ -match 'snapshot|compaction|"lsp"|permission' })
        Add-Check ("kilo config: " + $kiloCfg) ("wpisow: " + $lines.Count) "-"
        foreach ($l in $lines) { if ($l.Trim().Length -gt 0) { Say ("         " + $l.Trim()) "DarkGray" } }
    }
}

$kiloDir = Join-Path $RepoPath ".kilo"
if (Test-Path -LiteralPath $kiloDir) {
    $entries = @(Get-ChildItem -LiteralPath $kiloDir -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    Add-Check ".kilo w repo" ($entries -join ", ") "-" "setup-script = dodatkowy koszt przy kazdym worktree"
}

# --- VS Code i rozszerzenia: wersja vs engines, petla aktualizacji
$codeRoots = @(
    (Join-Opt $env:LOCALAPPDATA "Programs\Microsoft VS Code"),
    (Join-Opt $env:ProgramFiles "Microsoft VS Code")
)
$codeVersion = ""
foreach ($r in $codeRoots) {
    if ($r -eq "") { continue }
    $p = Join-Path $r "resources\app\product.json"
    if (Test-Path -LiteralPath $p) {
        try { $codeVersion = [string](Get-Content -LiteralPath $p -Raw | ConvertFrom-Json).version } catch { }
        if ($codeVersion -ne "") { break }
    }
}
Add-Check "VS Code" $(if ($codeVersion -ne "") { $codeVersion } else { "nie ustalono" }) "-"

$extRoot = Join-Opt $env:USERPROFILE ".vscode\extensions"
$incompatible = @()
$extCount = 0
if ($extRoot -ne "" -and (Test-Path -LiteralPath $extRoot)) {
    $dirs = @(Get-ChildItem -LiteralPath $extRoot -Directory -ErrorAction SilentlyContinue)
    $extCount = $dirs.Count
    if ($codeVersion -match '^(\d+)\.(\d+)') {
        $wantMajor = [int]$matches[1]
        $wantMinor = [int]$matches[2]
        foreach ($d in $dirs) {
            $pj = Join-Path $d.FullName "package.json"
            if (-not (Test-Path -LiteralPath $pj)) { continue }
            try { $pkg = Get-Content -LiteralPath $pj -Raw | ConvertFrom-Json } catch { continue }
            $eng = [string]$pkg.engines.vscode
            if ($eng -match '(\d+)\.(\d+)') {
                $eMaj = [int]$matches[1]
                $eMin = [int]$matches[2]
                if (($eMaj -gt $wantMajor) -or ($eMaj -eq $wantMajor -and $eMin -gt $wantMinor)) {
                    $incompatible += ([string]$pkg.name + "@" + [string]$pkg.version + " wymaga " + $eng)
                }
            }
        }
    }
}
Add-Check "rozszerzenia zainstalowane" ([string]$extCount) "-"
if ($incompatible.Count -gt 0) {
    Add-Check "rozszerzenia niezgodne z VS Code" ([string]$incompatible.Count) "BAD"
    foreach ($i in $incompatible) { Say ("         " + $i) "DarkGray" }
    Add-Finding ("{0} rozszerzen nie dziala z VS Code {1}, a VS Code probuje je dociagnac w kolko - kazda proba skanuje katalog i obciaza shared process. Ustaw 'extensions.autoUpdate: false' i usun te wersje z dysku." -f $incompatible.Count, $codeVersion)
}

# --- MCP: serwery startujace przy kazdym oknie / worktree
$mcpFiles = @()
$candidates = @(
    (Join-Path $RepoPath ".vscode\mcp.json"),
    (Join-Path $RepoPath ".kilo\mcp.json"),
    (Join-Opt $env:USERPROFILE ".config\kilo\mcp.json")
)
$gsRoot = Join-Opt $env:APPDATA "Code\User\globalStorage"
if ($gsRoot -ne "" -and (Test-Path -LiteralPath $gsRoot)) {
    $candidates += @(Get-ChildItem -LiteralPath $gsRoot -Recurse -Filter "mcp*.json" -File -ErrorAction SilentlyContinue |
                     Where-Object { $_.FullName -notmatch 'node_modules' } |
                     ForEach-Object { $_.FullName })
}
foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { $mcpFiles += $c }
}
if ($mcpFiles.Count -gt 0) {
    $total = 0
    foreach ($f in ($mcpFiles | Sort-Object -Unique)) {
        $names = @()
        try {
            $raw = Get-Content -LiteralPath $f -Raw
            $names = @([regex]::Matches($raw, '"([A-Za-z0-9_\-]+)"\s*:\s*\{\s*"(command|type|url|baseUrl)"') |
                       ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
        } catch { }
        $total += $names.Count
        $v = "-"
        if ($names.Count -gt 3) { $v = "WARN" }
        Add-Check ("MCP w " + (Split-Path $f -Leaf)) ($names -join ", ") $v
        Say ("         plik: " + $f) "DarkGray"
    }
    Add-Finding ("{0} serwerow MCP startuje w procesie rozszerzen przy kazdym oknie i worktree. Serwer, ktory pada albo czeka na OAuth, blokuje ten proces na 10-60 s - a to ten sam proces, w ktorym siedzi Kilo i git." -f $total)
} else {
    Add-Check "pliki konfiguracji MCP" "nie znaleziono" "-"
}

# ---------------------------------------------------------------- 6. test worktree
if ($WorktreeTest) {
    Head "6. Dwa worktree pod rzad (czysty test kosztu)"
    Say "  Tworze dwa tymczasowe worktree w TEMP i usuwam je po pomiarze." "DarkGray"
    $base = Join-Path $env:TEMP ("kilo-wt-test-" + (Get-Random))
    New-Item -ItemType Directory -Path $base -Force | Out-Null
    $times = @()
    $i = 0
    foreach ($n in @(1, 2)) {
        $i++
        $target = Join-Path $base ("wt" + $i)
        $r = Measure-Proc $git @('-C', $RepoPath, 'worktree', 'add', '-q', '--detach', $target, 'HEAD')
        $times += $r.ms
        if ($r.exit -ne 0) { Say ("  worktree #" + $i + " FAIL: " + $r.out) "Red" }
        else {
            $s = Measure-Proc $git @('-C', $target, 'status', '--porcelain=v1', '-uall')
            Say ("  worktree #" + $i + ": add " + $r.ms + " ms, pierwszy status " + $s.ms + " ms") "Gray"
            Add-Check ("worktree #" + $i + " add") ("{0} ms" -f $r.ms) $(if ($r.ms -gt 10000) { "BAD" } elseif ($r.ms -gt 3000) { "WARN" } else { "OK" })
            Add-Check ("worktree #" + $i + " 1. status") ("{0} ms" -f $s.ms) $(if ($s.ms -gt 5000) { "WARN" } else { "OK" })
            $null = Measure-Proc $git @('-C', $RepoPath, 'worktree', 'remove', '--force', $target)
        }
    }
    Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction SilentlyContinue
    if ($times.Count -eq 2) {
        $ratio = 0
        if ($times[0] -gt 0) { $ratio = [Math]::Round($times[1] / $times[0], 2) }
        Add-Check "worktree #2 vs #1" ("x" + $ratio) "-" "wyraznie mniej niz 1.0 = cold start (nie ma czego naprawiac); ok. 1.0 = stala wada"
    }
}

# ---------------------------------------------------------------- -Fix
if ($Fix) {
    Head "7. Fix: bezpieczne ustawienia git (globalnie)"

    $apply = @(
        @{ k = 'core.fscache';        v = 'true' },
        @{ k = 'core.preloadindex';   v = 'true' },
        @{ k = 'core.untrackedCache'; v = 'true' },
        @{ k = 'core.commitGraph';    v = 'true' },
        @{ k = 'gc.auto';             v = '6700' }
    )
    $rollback = @()
    foreach ($e in $apply) {
        $old = (Measure-Proc $git @('config', '--global', '--get', $e.k)).out
        $r = Measure-Proc $git @('config', '--global', $e.k, $e.v)
        if ($r.exit -eq 0) {
            Add-Check ("ustawiono " + $e.k) $e.v "OK"
        } else {
            Add-Check ("NIE ustawiono " + $e.k) $r.out "BAD"
        }
        if ($old -eq "") { $rollback += ("git config --global --unset " + $e.k) }
        else             { $rollback += ("git config --global " + $e.k + " " + $old) }
    }
    Say ""
    Say "  Rollback (skopiuj, jesli chcesz cofnac):" "Yellow"
    foreach ($r in $rollback) { Say ("    " + $r) "DarkGray" }

    $fsmNow = (Measure-Proc $git @('-C', $RepoPath, 'config', '--get', 'core.fsmonitor')).out
    if ($fsmNow -ne "" -and $fsmNow -ne "false" -and $fsmNow -ne "true") {
        Say ""
        Say ("  core.fsmonitor wskazuje '" + $fsmNow + "'. Wylacz go: git config --global core.fsmonitor false") "Yellow"
    }

    Say ""
    Say "  Do settings.json VS Code wklej (to wylacza najwiekszy szum git w tle):" "Yellow"
    Say '    "git.autofetch": false,' "DarkGray"
    Say '    "git.autorefresh": false,' "DarkGray"
    Say '    "git.autoRepositoryDetection": "openEditors",' "DarkGray"
    Say '    "git.repositoryScanMaxDepth": 1,' "DarkGray"
    Say '    "git.decorations.enabled": false' "DarkGray"
    Say ""
    Say "  Po zmianie: przeladuj okno (Developer: Reload Window) i zmierz ponownie." "Gray"

    Head "8. Pomiar po zmianie"
    $after1 = Measure-Proc $git @('-C', $RepoPath, 'status', '-z', '-uall', '--porcelain=v1')
    $after2 = Measure-Proc $git @('-C', $RepoPath, 'config', '--get', 'commit.template')
    Add-Check "status -z -uall (po)" ("{0} ms" -f $after1.ms) "-" ("bylo " + $statusRun.ms + " ms")
    Add-Check "config --get (po)"    ("{0} ms" -f $after2.ms) "-" ("bylo " + $tplPlain.ms + " ms")
}

# ---------------------------------------------------------------- werdykt
Head "Werdykt"
$spawnSlow  = ($verMed -gt 800)
$cmdSlow    = ($cmdMed -gt 800)
$configSlow = ($tplClean.ms -gt 0 -and $tplPlain.ms -gt 1000 -and $tplClean.ms -lt ($tplPlain.ms / 3))
$repoSlow   = ($repoMed -gt 3000 -or $statusRun.ms -gt 5000)

if ($spawnSlow -and -not $cmdSlow) {
    Add-Finding "git.exe jest wolny przy starcie, a cmd.exe szybki -> to skanowanie/inspekcja git.exe (AV/EDR). Najwieksza dzwignia: wykluczenie git.exe i katalogu repo, ale wymaga admina."
} elseif ($spawnSlow -and $cmdSlow) {
    Add-Finding "Wolny start dowolnego procesu -> polityka maszyny albo profil przekierowany na siec. Nie naprawisz tego ustawieniami gita."
}
if ($configSlow) {
    Add-Finding "Koszt siedzi w lancuchu configu git (globalny/systemowy). Sprawdz include.path i czy .gitconfig nie lezy na udziale sieciowym."
}
if ($repoSlow) {
    Add-Finding "Operacje na repo sa wolne niezaleznie od procesu -> zawartosc repo lub dysk (duzo untracked, OneDrive, filtrowany folder)."
}
if (-not $spawnSlow -and -not $configSlow -and -not $repoSlow) {
    Add-Finding "Warstwy git wygladaja normalnie - czas zjada inicjalizacja Kilo (snapshot, LSP, indeksowanie), nie samo worktree. Wtedy dzwignia jest 'snapshot: false' i mniej otwartych worktree."
}

if ($script:Findings.Count -eq 0) {
    Say "  brak jednoznacznego wskazania - zobacz tabele wyzej" "Yellow"
} else {
    $n = 0
    foreach ($f in $script:Findings) { $n++; Write-Host ("  " + $n + ") " + $f) -ForegroundColor Yellow }
}

# ---------------------------------------------------------------- zapis
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = $env:TEMP
    if ([string]::IsNullOrWhiteSpace($OutDir)) { $OutDir = (Get-Location).Path }
}
$stamp   = (Get-Date).ToString("yyyyMMdd-HHmmss")
$jsonPath = Join-Path $OutDir ("kilo-worktree-doctor-" + $stamp + ".json")
$payload = [ordered]@{
    generatedAt = (Get-Date).ToString("s")
    computer    = $env:COMPUTERNAME
    user        = $env:USERNAME
    repo        = $repoTop
    git         = $git
    spawnMedianMs  = $verMed
    cmdMedianMs    = $cmdMed
    statusMs       = $statusRun.ms
    configPlainMs  = $tplPlain.ms
    configCleanMs  = $tplClean.ms
    repoMedianMs   = $repoMed
    trackedFiles   = $tracked
    untrackedFiles = $untracked
    dotGitBytes    = $dotGitSize
    refCount       = $refCount
    worktreeCount  = $wtCount
    checks         = $script:Checks
    findings       = $script:Findings
}
try {
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    Say ""
    Say ("  Zapisalem wynik: " + $jsonPath) "Green"
    Say "  Wklej mi ten plik (albo sekcje Werdykt) - dobiore leczenie do wyniku." "Gray"
} catch {
    Say ("  Nie udalo sie zapisac JSON: " + $_.Exception.Message) "Red"
}
Say ""
