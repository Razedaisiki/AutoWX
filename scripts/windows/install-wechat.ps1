# 解析 → 下载 → 校验 → 安装 → 定位微信
# 读取 env: WECHAT_REPO, GH_PROXY, GH_TOKEN
# 输出 env: WECHAT_EXE (通过 GITHUB_ENV)

$repo = $env:WECHAT_REPO

$headers = @{
    "Accept"        = "application/vnd.github+json"
    "Authorization" = "Bearer $env:GH_TOKEN"
    "User-Agent"    = "AutoWX"
}

$all = @()

for ($page = 1; $page -le 5; $page++) {
    $api = "https://api.github.com/repos/$repo/releases?per_page=100&page=$page"

    $batch = Invoke-RestMethod `
        -Uri $api `
        -Headers $headers

    if (-not $batch -or $batch.Count -eq 0) {
        break
    }

    $all += $batch
}

$release = $all |
    Where-Object {
        $_.tag_name -match '^v4\.1\.8\.'
    } |
    Sort-Object {
        [version]($_.tag_name.TrimStart('v'))
    } -Descending |
    Select-Object -First 1

if (-not $release) {
    throw "No WeChat 4.1.8.x release found."
}

Write-Host "Selected:"
Write-Host $release.tag_name
Write-Host $release.name

$asset = $release.assets |
    Where-Object {
        $_.name -match '\.exe$'
    } |
    Sort-Object size -Descending |
    Select-Object -First 1

if (-not $asset) {
    throw "No EXE asset found."
}

$original = $asset.browser_download_url
$proxyUrl = "$env:GH_PROXY$original"

Write-Host ""
Write-Host "Asset:"
Write-Host $asset.name

Write-Host ""
Write-Host "Proxy URL:"
Write-Host $proxyUrl

# ------------------------------------------------------------
# 下载
# ------------------------------------------------------------
$installer = "$env:TEMP\$($asset.name)"

Write-Host "Downloading:"
Write-Host $proxyUrl

$start = Get-Date

curl.exe `
    -L `
    --fail `
    --retry 3 `
    --retry-delay 2 `
    --connect-timeout 30 `
    --progress-bar `
    -o $installer `
    $proxyUrl

if ($LASTEXITCODE -ne 0) {
    throw "Download failed."
}

$seconds = ((Get-Date) - $start).TotalSeconds
$sizeMB = (Get-Item $installer).Length / 1MB

Write-Host ""
Write-Host "======================================"
Write-Host "Download completed"
Write-Host ("Size:  {0:N2} MB" -f $sizeMB)
Write-Host ("Time:  {0:N2} seconds" -f $seconds)
Write-Host ("Speed: {0:N2} MB/s" -f ($sizeMB / $seconds))
Write-Host "======================================"

# ------------------------------------------------------------
# SHA256 校验（有 digest 则校验，否则仅打印）
# ------------------------------------------------------------
$actual = (
    Get-FileHash `
        $installer `
        -Algorithm SHA256
).Hash.ToLower()

Write-Host "Actual SHA256:"
Write-Host $actual

if ($asset.digest) {
    $expected = $asset.digest `
        -replace "^sha256:", ""

    $expected = $expected.ToLower()

    Write-Host ""
    Write-Host "Expected (from GitHub digest):"
    Write-Host $expected

    if ($actual -ne $expected) {
        Remove-Item $installer -Force
        throw "SHA256 mismatch! Installation aborted."
    }

    Write-Host ""
    Write-Host "SHA256 verification passed."
} else {
    Write-Host ""
    Write-Host "No digest available from release asset."
    Write-Host "Record the SHA256 above to pin it later."
}

# ------------------------------------------------------------
# 安装
# ------------------------------------------------------------
Write-Host "Installing WeChat..."

Start-Process `
    -FilePath $installer `
    -ArgumentList "/S" `
    -Wait

Write-Host "Installation completed."

# ------------------------------------------------------------
# 定位微信
# ------------------------------------------------------------
$candidates = @(
    "C:\Program Files\Tencent\Weixin\Weixin.exe",
    "C:\Program Files (x86)\Tencent\Weixin\Weixin.exe",
    "C:\Program Files\Tencent\WeChat\WeChat.exe",
    "C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"
)

$wechat = $candidates |
    Where-Object {
        Test-Path $_
    } |
    Select-Object -First 1

if (-not $wechat) {
    throw "WeChat executable not found."
}

Write-Host "Found:"
Write-Host $wechat

Write-Host ""
Write-Host "File version:"
Write-Host (Get-Item $wechat).VersionInfo.FileVersion

"WECHAT_EXE=$wechat" >> $env:GITHUB_ENV
