# 小米互传右键发送 —— 弹出设备窗口，选中后发送
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Files
)

$ErrorActionPreference = 'Continue'

$logFile = $null
try {
    $logDir = Join-Path $env:LOCALAPPDATA 'MiDropSend'
    if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force -ErrorAction Stop | Out-Null }
    $logFile = Join-Path $logDir 'send.log'
} catch { $logFile = $null }
function Log($msg) {
    if (-not $logFile) { return }
    try { Add-Content -LiteralPath $logFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' | ' + $msg) -Encoding UTF8 -ErrorAction Stop } catch {}
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root = Join-Path $env:ProgramFiles 'MI\XiaomiPCManager'
$cli = Get-ChildItem -LiteralPath $root -Filter xpmcli.exe -Recurse -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $cli) {
    [System.Windows.Forms.MessageBox]::Show('找不到 xpmcli.exe，请重新安装小米电脑管家。', '小米互传') | Out-Null
    exit 1
}
$cli = $cli.FullName

$Files = @($Files | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
if ($Files.Count -eq 0) {
    [System.Windows.Forms.MessageBox]::Show('没有选中文件。', '小米互传') | Out-Null
    exit 1
}
Log ('--- invoked; args=' + ($Files -join ' ; '))

$form = New-Object System.Windows.Forms.Form
$form.Text = '小米互传'
$form.Size = New-Object System.Drawing.Size(420, 360)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false

$lblTip = New-Object System.Windows.Forms.Label
$lblTip.Text = '选择接收设备：'
$lblTip.Location = New-Object System.Drawing.Point(14, 12)
$lblTip.AutoSize = $true
$form.Controls.Add($lblTip)

$list = New-Object System.Windows.Forms.ListBox
$list.Location = New-Object System.Drawing.Point(14, 36)
$list.Size = New-Object System.Drawing.Size(376, 170)
$form.Controls.Add($list)

$lblFile = New-Object System.Windows.Forms.Label
$lblFile.Text = ('待发送：' + (($Files | ForEach-Object { [System.IO.Path]::GetFileName($_) }) -join '、'))
$lblFile.Location = New-Object System.Drawing.Point(14, 214)
$lblFile.Size = New-Object System.Drawing.Size(376, 20)
$lblFile.AutoEllipsis = $true
$form.Controls.Add($lblFile)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = '正在扫描设备...'
$lblStatus.Location = New-Object System.Drawing.Point(14, 240)
$lblStatus.Size = New-Object System.Drawing.Size(376, 24)
$form.Controls.Add($lblStatus)

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = '刷新'
$btnRefresh.Location = New-Object System.Drawing.Point(14, 276)
$btnRefresh.Size = New-Object System.Drawing.Size(90, 32)
$form.Controls.Add($btnRefresh)

$btnSend = New-Object System.Windows.Forms.Button
$btnSend.Text = '发送'
$btnSend.Location = New-Object System.Drawing.Point(300, 276)
$btnSend.Size = New-Object System.Drawing.Size(90, 32)
$btnSend.Enabled = $false
$form.Controls.Add($btnSend)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = '取消'
$btnCancel.Location = New-Object System.Drawing.Point(204, 276)
$btnCancel.Size = New-Object System.Drawing.Size(90, 32)
$btnCancel.Add_Click({ $form.Close() })
$form.Controls.Add($btnCancel)

$script:devices = @()

function Load-Devices {
    $lblStatus.Text = '正在扫描设备...'
    $form.Refresh()
    $list.Items.Clear()
    $script:devices = @()
    for ($i = 1; $i -le 4; $i++) {
        $raw = & $cli smartshare midrop devices list 2>$null | Select-Object -Last 1
        try {
            $d = @((($raw | ConvertFrom-Json).result.result.data.devices))
        } catch { $d = @() }
        if ($d.Count -gt 0) { $script:devices = $d; break }
        Start-Sleep -Milliseconds 1500
    }
    foreach ($d in $script:devices) {
        $label = $d.name
        if (-not $label) { $label = $d.deviceName }
        [void]$list.Items.Add($label)
    }
    $btnSend.Enabled = ($script:devices.Count -gt 0)
    if ($script:devices.Count -gt 0) {
        $list.SelectedIndex = 0
        $lblStatus.Text = ('发现 ' + $script:devices.Count + ' 台设备')
    } else {
        $lblStatus.Text = '没有发现设备：请打开电脑管家、确认互传已开启、手机保持解锁'
    }
    Log ('scan done, count=' + $script:devices.Count)
}

$btnRefresh.Add_Click({ Load-Devices })

$btnSend.Add_Click({
    if ($list.SelectedIndex -lt 0) { return }
    $d = $script:devices[$list.SelectedIndex]
    $id = $d.deviceId
    if (-not $id) { $id = $d.id }
    $btnSend.Enabled = $false
    $btnRefresh.Enabled = $false
    $lblStatus.Text = '正在发送...'
    $form.Refresh()

    $cliArgs = @('smartshare', 'midrop', 'send', '--device-id', [string]$id)
    foreach ($f in $Files) { $cliArgs += '--file'; $cliArgs += $f }
    $result = & $cli @cliArgs 2>$null | Select-Object -Last 1
    Log ('send.result=' + $result)
    $form.Refresh()

    try {
        Start-Sleep -Seconds 4
        $stRaw = & $cli smartshare midrop task status get 2>$null | Select-Object -Last 1
        $st = ($stRaw | ConvertFrom-Json).result.result.data.statuses
        $mine = @($st | Where-Object { $_.task.deviceId -eq [uint32]$id }) | Sort-Object { $_.taskId } | Select-Object -Last 1
        if ($mine -and $mine.error -and $mine.error -ne 0) {
            Log ('task error=' + $mine.error)
            $lblStatus.Text = ('传输失败（错误码 ' + $mine.error + '）')
            $msg = '传输失败（错误码 ' + $mine.error + '）。手机端没有确认通道时请保持手机解锁、停在互传界面，或把接收模式设为自动接收后重试。'
            [System.Windows.Forms.MessageBox]::Show($msg, '小米互传') | Out-Null
        } else {
            $lblStatus.Text = '已发送到 ' + $d.name
            Log 'OK'
            Start-Sleep -Milliseconds 800
            $form.Close()
        }
    } catch {
        Log ('status parse fail: ' + $_.Exception.Message)
        $lblStatus.Text = '已提交发送任务'
    }
    $btnSend.Enabled = $true
    $btnRefresh.Enabled = $true
})

$form.Add_Shown({ Load-Devices })
[void]$form.ShowDialog()
exit 0
