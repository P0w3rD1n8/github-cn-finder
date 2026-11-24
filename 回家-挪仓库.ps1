$ErrorActionPreference = 'Continue'
$log = 'C:\work\move-workspace.log'
$src = 'C:\Users\power\GitHub中文发现器'
$dst = 'C:\work\github-cn-finder'

function Log($m) { Add-Content $log ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) -Encoding utf8 }
"=== 挪仓库 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -Encoding utf8 $log
Log '60 秒后开始；不要关这个窗口'
Start-Sleep -Seconds 60

# 1) 关 DSH
$p = Get-Process 'DeepSeek Harness' -ErrorAction SilentlyContinue
if ($p) {
  $main = $p | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if ($main) { $main.CloseMainWindow() | Out-Null }
  for ($i=0; $i -lt 20; $i++) { Start-Sleep 1; if (-not (Get-Process 'DeepSeek Harness' -ErrorAction SilentlyContinue)) { break } }
}
if (Get-Process 'DeepSeek Harness' -ErrorAction SilentlyContinue) {
  & taskkill.exe /IM "DeepSeek Harness.exe" /F /T | Out-Null
  Start-Sleep 4
}
Log 'DSH 已退出'

# 2) 挪目录（已挪过则跳过）
if (-not (Test-Path $src)) {
  if (Test-Path $dst) { Log '源不存在、目标存在：已经挪过，跳过' }
  else { Log '源和目标都不存在，停止'; exit 1 }
} else {
  New-Item -ItemType Directory 'C:\work' -Force | Out-Null
  try {
    Move-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
    Log "已移动：$src -> $dst"
  } catch {
    Log ('移动失败：' + $_.Exception.Message)
  }
  # 3) 校验，失败回滚
  if (-not (Test-Path (Join-Path $dst 'index.html'))) {
    Log '校验失败：目标里没有 index.html，尝试回滚'
    if ((Test-Path $dst) -and (-not (Test-Path $src))) { Move-Item $dst $src; Log '已回滚' }
  } else {
    Log '校验通过'
  }
}

# 4) 重开 DSH
$exe = @(
  "$env:LOCALAPPDATA\Programs\@deepseek-ai\dsh-desktop\DeepSeek Harness.exe",
  "C:\Program Files\DeepSeek Harness\DeepSeek Harness.exe",
  "D:\DeepSeek Harness\DeepSeek Harness.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) {
  $exe = Get-ChildItem "$env:LOCALAPPDATA\Programs" -Recurse -Depth 4 -Filter 'DeepSeek Harness.exe' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}
if ($exe) { Start-Process $exe; Log ('已启动：' + $exe) } else { Log '没找到 DSH 可执行文件，请手动打开' }
Log '结束'
