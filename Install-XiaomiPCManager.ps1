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

# 在 $ErrorActionPreference='Stop' 下调用原生命令并把输出并入日志。
# PS 5.1 的坑：2>&1 会把 stderr 首行包装成终止错误，脚本会在 $LASTEXITCODE
# 检查之前直接中断，所以这里临时降为 Continue。
function Invoke-PyLogged {
  param([string]$Py, [string]$Script, [string[]]$ScriptArgs)
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & $Py $Script @ScriptArgs 2>&1 | ForEach-Object { Log $_ }
    return $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prev
  }
}

# 真正试运行一次再认数：WindowsApps 的 python.exe 存根能通过 Get-Command 和
# Test-Path，但执行只会弹商店（退出码非 0），必须验证解释器可用
function Test-PythonRunnable([string]$Exe) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & $Exe -c "import sys; sys.exit(0)" 2>$null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $prev
  }
}

# 版本目录按版本号数值比较：字符串排序会把 10.x 排在 9.x 之后
function Get-LatestVersionDir([string]$Root) {
  return Get-ChildItem $Root -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+(\.\d+)+$' } |
    Sort-Object { [version]$_.Name } -Descending |
    Select-Object -First 1
}

# ---- 自提权 ----
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  $argsList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
  if ($Installer) { $argsList += @('-Installer', "`"$Installer`"") }
  if ($ModelOnly) { $argsList += '-ModelOnly' }
  if ($NoLaunch) { $argsList += '-NoLaunch' }
  try {
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argsList | Out-Null
  } catch {
    Log "提权被取消或启动失败: $($_.Exception.Message)"
    exit 1
  }
  exit
}

# ---- Python ----
$python = $null
foreach ($cand in 'python', 'py') {
  $src = (Get-Command $cand -ErrorAction SilentlyContinue).Source
  if ($src -and (Test-PythonRunnable $src)) { $python = $src; break }
}
if (-not $python) { Log "找不到可用的 Python 3（python / py 都不可用），请先安装并加入 PATH"; exit 1 }
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
  $rc = Invoke-PyLogged $python $py @('patch-installer', $Installer, '-o', $patched)
  if ($rc -ne 0) { Log "打补丁失败"; exit 1 }

  # 2) 静默安装
  Log "开始静默安装（可能需要几分钟）..."
  $p = Start-Process -FilePath $patched -ArgumentList '/Silent' -Wait -PassThru
  Log "安装程序退出码: $($p.ExitCode)"
  if ($p.ExitCode -ne 0) { Log "警告: 安装程序返回非零退出码，后续步骤可能不完整" }

  # 3) 等版本目录出现
  $v = $null
  for ($i = 0; $i -lt 30; $i++) {
    $v = Get-LatestVersionDir $root
    if ($v) { break }
    Start-Sleep -Seconds 2
  }
  Log "安装完成，版本目录: $(if($v){$v.FullName}else{'(未知)'})"
}

# 4) 已安装目录补丁 + 运行时伪装
Log "给已安装目录打补丁并写入运行时伪装..."
$rc = Invoke-PyLogged $python $py @('patch-installed')
if ($rc -ne 0) { Log "已安装目录补丁失败"; exit 1 }

# 4.5) 部署社区 WMI 伪装补丁（msimg32 代理，仅对加载 MiSmartShareDLL 的进程生效）
$spoofDll = Join-Path $here 'wmi_spoof_msimg32.dll'
$verDir = Get-LatestVersionDir $root
if ((Test-Path $spoofDll) -and $verDir) {
  $msDir = Join-Path $verDir.FullName 'MiSmartShare'
  if (Test-Path $msDir) {
    try {
      Copy-Item $spoofDll (Join-Path $msDir 'msimg32.dll') -Force
      Log "已部署 WMI 伪装补丁: $msDir\msimg32.dll"
    } catch {
      Log "部署 WMI 伪装补丁失败（文件被占用？可稍后手动复制）: $($_.Exception.Message)"
    }
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
  $null = Invoke-PyLogged $python $padGate @('apply')
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
  $exe = Get-LatestVersionDir $root
  if ($exe) {
    $app = Join-Path $exe.FullName 'XiaomiPCManager.exe'
    if (Test-Path $app) { Start-Process $app | Out-Null; Log "已启动应用" }
  }
}

Log "==== 完成 ===="
