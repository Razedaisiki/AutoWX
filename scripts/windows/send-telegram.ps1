# 发送 Telegram 消息或图片。
# 读取 env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
param(
    [Parameter(Mandatory = $false)]
    [string]$Text,

    [Parameter(Mandatory = $false)]
    [string]$Photo,

    [Parameter(Mandatory = $false)]
    [string]$Caption = ""
)

$token = $env:TELEGRAM_BOT_TOKEN
$chatId = $env:TELEGRAM_CHAT_ID

if ($Photo) {
    curl.exe `
        -sS `
        -X POST `
        "https://api.telegram.org/bot$token/sendPhoto" `
        -F "chat_id=$chatId" `
        -F "caption=$Caption" `
        -F "photo=@$Photo"
} else {
    curl.exe `
        -sS `
        -X POST `
        "https://api.telegram.org/bot$token/sendMessage" `
        -d "chat_id=$chatId" `
        --data-urlencode "text=$Text"
}

if ($LASTEXITCODE -ne 0) {
    throw "Failed to send Telegram message."
}
