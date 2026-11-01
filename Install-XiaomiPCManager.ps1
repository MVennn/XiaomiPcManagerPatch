#requires -version 5
<#
  小米电脑管家（非小米电脑）一键补丁/安装脚本

  用法：
    .\Install-XiaomiPCManager.ps1                          # 自动找 Downloads\Archives 下最新的安装包
    .\Install-XiaomiPCManager.ps1 -Installer "D:\xxx.exe"  # 指定安装包
    .\Install-XiaomiPCManager.ps1 -ModelOnly               # 不装，只恢复运行时机型伪装

  做的事情：
    1. 用 xpm_patch.py 把本机型号写进安装包内嵌白名单（长度不变）
    2. 静默安装补丁版（/Silent）
    3. 给已安装的 Uninstall.exe 打同样补丁
    4. 写入 dummy_pc_model（让手机/平板按受支持机型放行）
    5. 重启相关服务并启动应用
#>
param(
  [string]$Installer = "",
  [switch]$ModelOnly,
  [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $here 'xpm_patch.py'
$log = Join-Path $here 'install_log.txt'
$root = 'C:\Program Files\MI\XiaomiPCManager'

function Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  Write-Host $line
  Add-Content -Path $log -Value $line -Encoding utf8
}

# ---- 自提权 ----
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  $argsList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
  if ($Installer) { $argsList += @('-Installer', "`"$Installer`"") }
  if ($ModelOnly) { $argsList += '-ModelOnly' }
  if ($NoLaunch) { $argsList += '-NoLaunch' }
  Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argsList | Out-Null
  exit
}

# ---- Python ----
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python -or -not (Test-Path $python)) { Log "找不到 Python，请先安装 Python 3 并加入 PATH"; exit 1 }
if (-not (Test-Path $py)) { Log "找不到 xpm_patch.py"; exit 1 }

Log "==== 开始 ===="

if (-not $ModelOnly) {
  if (-not $Installer) {
    $dir = Join-Path $env:USERPROFILE 'Downloads\Archives'
    $cand = Get-ChildItem $dir -Filter 'XiaomiPCManager*.exe' -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -notmatch '_patched' } |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $cand) { Log "在 $dir 下没找到 XiaomiPCManager*.exe，请用 -Installer 指定"; exit 1 }
    $Installer = $cand.FullName
  }
  if (-not (Test-Path $Installer)) { Log "安装包不存在: $Installer"; exit 1 }
  Log "安装包: $Installer"

  # 1) 打补丁
  $patched = Join-Path $here ((Split-Path -Leaf $Installer) -replace '\.exe$', '_patched.exe')
  Log "正在打补丁 -> $patched"
  & $python $py patch-installer $Installer -o $patched 2>&1 | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { Log "打补丁失败"; exit 1 }

  # 2) 静默安装
  Log "开始静默安装（可能需要几分钟）..."
  $p = Start-Process -FilePath $patched -ArgumentList '/Silent' -Wait -PassThru
  Log "安装程序退出码: $($p.ExitCode)"

  # 3) 等版本目录出现
  $root = 'C:\Program Files\MI\XiaomiPCManager'
  for ($i = 0; $i -lt 30; $i++) {
    $v = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '^\d+(\.\d+)+$' } | Sort-Object Name -Descending | Select-Object -First 1
    if ($v) { break }
    Start-Sleep -Seconds 2
  }
  Log "安装完成，版本目录: $(if($v){$v.FullName}else{'(未知)'})"
}

# 4) 已安装目录补丁 + 运行时伪装
Log "给已安装目录打补丁并写入运行时伪装..."
& $python $py patch-installed 2>&1 | ForEach-Object { Log $_ }

# 4.5) 部署社区 WMI 伪装补丁（msimg32 代理，仅对加载 MiSmartShareDLL 的进程生效）
$spoofDll = Join-Path $here 'wmi_spoof_msimg32.dll'
$verDir = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '^\d+(\.\d+)+$' } | Sort-Object Name -Descending | Select-Object -First 1
if ((Test-Path $spoofDll) -and $verDir) {
  $msDir = Join-Path $verDir.FullName 'MiSmartShare'
  if (Test-Path $msDir) {
    Copy-Item $spoofDll (Join-Path $msDir 'msimg32.dll') -Force
    Log "已部署 WMI 伪装补丁: $msDir\msimg32.dll"
    $k = 'HKCU:\Software\SmartSharePatch'
    if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null }
    New-ItemProperty -Path $k -Name 'SpoofManufacturer' -Value 'XIAOMI' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $k -Name 'SpoofDevice' -Value 'TM2424' -PropertyType String -Force | Out-Null
  }
}

# 4.6) 通用 PC 模式：micont_service 加 --model=0（这是 PcContinuity 通用版的做法）
$svcKey = 'HKLM:\SYSTEM\CurrentControlSet\Services\micont_service'
if (Test-Path $svcKey) {
  $ip = (Get-ItemProperty $svcKey -ErrorAction SilentlyContinue).ImagePath
  if ($ip -and ($ip -notmatch '--model=0')) {
    $newIp = $ip.Trim() + ' --model=0'
    New-ItemProperty -Path $svcKey -Name ImagePath -PropertyType ExpandString -Value $newIp -Force | Out-Null
    Log "已给 micont_service 增加 --model=0（通用 PC 模式）"
  } elseif ($ip) {
    Log "micont_service 已带 --model=0"
  }
}

# 4.65) 平板镜像：绕过“已连接其他显示设备”的多显示器检查
$padGate = Join-Path $here 'padgate_patch.py'
if (Test-Path $padGate) {
  & $python $padGate apply 2>&1 | ForEach-Object { Log $_ }
} else {
  Log "未找到 padgate_patch.py，跳过平板镜像补丁"
}

# 4.7) 参照对照机配置：ProductModel 设为受支持机型，并停用会覆盖它的 MiDeviceService
foreach ($k in @('HKLM:\SOFTWARE\MI\MiDeviceService', 'HKLM:\SOFTWARE\WOW6432Node\MI\MiDeviceService')) {
  if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null }
  New-ItemProperty -Path $k -Name 'ProductModel' -Value 'TM2309' -PropertyType String -Force | Out-Null
}
Log "已设置 MiDeviceService\ProductModel = TM2309"
if (Get-Service MiDeviceService -ErrorAction SilentlyContinue) {
  Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\MiDeviceService' -Name Start -Value 4 -Type DWord -Force
  Set-Service -Name MiDeviceService -StartupType Disabled -ErrorAction SilentlyContinue
  & sc.exe stop MiDeviceService | Out-Null
  Start-Sleep -Seconds 2
  Get-Process MiDeviceService -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Log "已停用 MiDeviceService（避免用 WMI 覆盖 ProductModel）"
}

# 5) 重启服务
foreach ($svc in 'micont_service', 'DistributedService', 'XiaomiService', 'MiService', 'MiDeviceService') {
  try { Restart-Service -Name $svc -Force -ErrorAction Stop; Log "已重启 $svc" }
  catch { Log "重启 $svc 失败（可忽略）: $($_.Exception.Message)" }
}

# 6) 启动应用
if (-not $NoLaunch) {
  $exe = Get-ChildItem 'C:\Program Files\MI\XiaomiPCManager' -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+(\.\d+)+$' } | Sort-Object Name -Descending | Select-Object -First 1
  if ($exe) {
    $app = Join-Path $exe.FullName 'XiaomiPCManager.exe'
    if (Test-Path $app) { Start-Process $app | Out-Null; Log "已启动应用" }
  }
}

Log "==== 完成 ===="
