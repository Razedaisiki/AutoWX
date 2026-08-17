# 等待微信扫码登录（最多 2 分钟），检测主窗口尺寸变化。
param(
    [int]$TimeoutMinutes = 2
)

Add-Type @"
using System;
using System.Runtime.InteropServices;

public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(
        IntPtr hWnd,
        out RECT lpRect
    );

    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

Write-Host "Waiting for login..."
Write-Host "Maximum: $TimeoutMinutes minutes."

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$loggedIn = $false

while ((Get-Date) -lt $deadline) {
    $processes = Get-Process `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -match "Weixin|WeChat"
        }

    foreach ($p in $processes) {
        $p.Refresh()

        if ($p.MainWindowHandle -eq 0) {
            continue
        }

        $rect = New-Object Win32+RECT

        if ([Win32]::GetWindowRect($p.MainWindowHandle, [ref]$rect)) {
            $width = $rect.Right - $rect.Left
            $height = $rect.Bottom - $rect.Top

            Write-Host (
                "[{0}] PID={1} Process={2} Size={3}x{4}" -f `
                (Get-Date -Format "HH:mm:ss"),
                $p.Id,
                $p.ProcessName,
                $width,
                $height
            )

            if ($width -ge 500 -and $height -ge 400) {
                Write-Host ""
                Write-Host "======================================"
                Write-Host "LOGIN SUCCESS DETECTED"
                Write-Host "======================================"

                $loggedIn = $true
                break
            }
        }
    }

    if ($loggedIn) {
        break
    }

    Start-Sleep -Seconds 3
}

if (-not $loggedIn) {
    throw "Login timeout."
}

Start-Sleep -Seconds 3
