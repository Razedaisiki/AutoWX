# 截取当前屏幕并保存为 PNG。
param(
    [string]$OutputPath = "wechat-login.png"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds

$bitmap = New-Object System.Drawing.Bitmap `
    $bounds.Width,
    $bounds.Height

$graphics = [System.Drawing.Graphics]::FromImage($bitmap)

$graphics.CopyFromScreen(
    $bounds.Location,
    [System.Drawing.Point]::Empty,
    $bounds.Size
)

$path = "$env:GITHUB_WORKSPACE\$OutputPath"

$bitmap.Save(
    $path,
    [System.Drawing.Imaging.ImageFormat]::Png
)

$graphics.Dispose()
$bitmap.Dispose()

Write-Host "Screenshot saved: $path"
