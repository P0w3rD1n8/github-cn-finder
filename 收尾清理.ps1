# 收尾清理脚本（2026-11-24）
# 用途：清理仓库迁移后的临时残留。默认只预览，不动任何文件。
#     预览：  powershell -File 收尾清理.ps1
#     执行：  powershell -File 收尾清理.ps1 -Execute
#     可选：  加 -IncludePipCache 删 .tmp-pip(37MB)；加 -IncludePylibs 删 .pylibs(108MB)
#
# 安全原则：路径全部硬编码，不用通配符递归；受保护路径一律拒绝；
#          删除前先确认仓库身份；删除后打印汇总。

param(
    [switch]$Execute,
    [switch]$IncludePipCache,
    [switch]$IncludePylibs
)

$ErrorActionPreference = 'Continue'
$repo = 'C:\work\github-cn-finder'
$userHome = $env:USERPROFILE

Write-Host ''
Write-Host '=== 收尾清理 ===' -ForegroundColor Cyan
Write-Host ("模式：{0}" -f $(if ($Execute) { '执行删除' } else { '仅预览（不删任何东西）' }))

# ---------- 护栏 1：确认仓库身份 ----------
if (-not (Test-Path (Join-Path $repo '.git'))) {
    Write-Host "✗ 找不到 $repo\.git —— 不在预期的仓库位置，停止。" -ForegroundColor Red
    exit 1
}
$remote = (& git -C $repo config --get remote.origin.url) 2>$null
Write-Host ("仓库远端：{0}" -f $(if ($remote) { $remote } else { '(读不到)' }))

# ---------- 护栏 2：受保护路径 ----------
$protected = @(
    (Join-Path $userHome '.dsh\sessions'),
    (Join-Path $userHome '.dsh\attachments'),
    (Join-Path $userHome '.dsh\profiles'),
    (Join-Path $repo '.git'),
    (Join-Path $repo 'content'),
    (Join-Path $repo '.github')
)
function Test-Protected($path) {
    foreach ($p in $protected) {
        if ($path -eq $p) { return $true }
        if ($path.StartsWith($p + '\', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

# ---------- 待清理清单 ----------
$targets = @(
    @{ Path = (Join-Path $userHome '挪仓库.ps1');        Label = '迁移脚本（已用完）';        Always = $true  }
    @{ Path = (Join-Path $repo '.tmp-pw');               Label = '临时脚本目录（已清空）';    Always = $true  }
    @{ Path = (Join-Path $userHome '.dsh\cache');        Label = 'DSH 缓存（会自动重建）';    Always = $true  }
    @{ Path = (Join-Path $userHome 'GitHub中文发现器');   Label = '旧空目录（原仓库位置）';    Always = $true  }
    @{ Path = (Join-Path $repo '.tmp-pip');              Label = 'pip 缓存 37MB（需开关）';   Always = $false; Switch = 'IncludePipCache' }
    @{ Path = (Join-Path $repo '.pylibs');               Label = '本地依赖 108MB（需开关）';  Always = $false; Switch = 'IncludePylibs' }
)

function Get-Size($path) {
    if (-not (Test-Path $path)) { return $null }
    $item = Get-Item $path -Force
    if ($item.PSIsContainer) {
        $s = Get-ChildItem $path -Recurse -File -Force -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum
        return [pscustomobject]@{ Bytes = [double]$s.Sum; Files = $s.Count }
    }
    return [pscustomobject]@{ Bytes = [double]$item.Length; Files = 1 }
}

# ---------- 汇总并打印 ----------
Write-Host ''
Write-Host '--- 计划清理项 ---'
$plan = @()
foreach ($t in $targets) {
    $selected = $true
    if (-not $t.Always) {
        $selected = if ($t.Switch -eq 'IncludePipCache') { [bool]$IncludePipCache } else { [bool]$IncludePylibs }
    }
    $size = Get-Size $t.Path
    $state = if ($null -eq $size) { '不存在' } else { ('{0:N1} MB / {1} 个文件' -f ($size.Bytes / 1MB), $size.Files) }
    $mark = if ($selected) { '[删]' } else { '[留]' }
    $color = if ($selected -and $null -ne $size) { 'Yellow' } else { 'DarkGray' }
    Write-Host ("  {0} {1,-32} {2}" -f $mark, $t.Label, $state) -ForegroundColor $color
    if ($selected -and $null -ne $size) {
        if (Test-Protected $t.Path) {
            Write-Host ("       ✗ 命中受保护路径，强制跳过：{0}" -f $t.Path) -ForegroundColor Red
        } else {
            $plan += $t
        }
    }
}

Write-Host ''
Write-Host '--- 明确不删（受保护）---' -ForegroundColor DarkGray
Write-Host ('  {0}' -f (Join-Path $userHome '.dsh\sessions')) -ForegroundColor DarkGray
Write-Host ('  {0}' -f (Join-Path $userHome '.dsh\attachments')) -ForegroundColor DarkGray
Write-Host ('  {0}' -f (Join-Path $repo '.git')) -ForegroundColor DarkGray

if (-not $Execute) {
    Write-Host ''
    Write-Host '预览结束，未删除任何文件。' -ForegroundColor Cyan
    Write-Host '确认无误后执行：powershell -File 收尾清理.ps1 -Execute' -ForegroundColor Cyan
    exit 0
}

# ---------- 真正删除 ----------
Write-Host ''
Write-Host '--- 开始删除 ---'
$freed = 0.0
$fail = @()
foreach ($t in $plan) {
    $size = Get-Size $t.Path
    try {
        Remove-Item -LiteralPath $t.Path -Recurse -Force -ErrorAction Stop
        $freed += [double]$size.Bytes
        Write-Host ("  ✓ {0}" -f $t.Label) -ForegroundColor Green
    } catch {
        $fail += [pscustomobject]@{ Label = $t.Label; Msg = $_.Exception.Message }
        Write-Host ("  ✗ {0} —— {1}" -f $t.Label, $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host ''
Write-Host ("已释放约 {0:N1} MB" -f ($freed / 1MB)) -ForegroundColor Cyan
if ($fail.Count -gt 0) {
    Write-Host '以下项删除失败（通常是正在被 DSH 占用）：' -ForegroundColor Yellow
    foreach ($f in $fail) { Write-Host ("  - {0}: {1}" -f $f.Label, $f.Msg) -ForegroundColor Yellow }
    Write-Host '处理办法：完全退出 DSH 后再跑一次本脚本 -Execute' -ForegroundColor Yellow
}

# ---------- 删后复查 ----------
Write-Host ''
Write-Host '--- 复查 ---'
& git -C $repo status -sb
Write-Host ''
Write-Host '别忘了：去极空间把三个任务（sessions / attachments / github-cn-finder）各点一次「开始」，' -ForegroundColor Cyan
Write-Host '把今天的提交推到 NAS，公司那边才能拉到。' -ForegroundColor Cyan
