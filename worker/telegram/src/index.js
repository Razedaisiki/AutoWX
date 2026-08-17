async function sendTelegram(env, chatId, text) {
  const body = new URLSearchParams();

  body.set("chat_id", String(chatId));
  body.set("text", text);
  body.set("disable_web_page_preview", "true");

  await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    }
  );
}


async function handleTelegram(update, env) {
  const message = update?.message;

  if (!message?.text) {
    return;
  }

  const chatId = String(message.chat.id);

  // 只允许你自己的 Telegram 账号控制
  if (chatId !== String(env.ALLOWED_CHAT_ID)) {
    return;
  }

  const text = message.text.trim();

  const command = text
    .split(/\s+/)[0]
    .split("@")[0]
    .toLowerCase();

  if (command === "/startvx") {
    await sendTelegram(
      env,
      chatId,
      "🚀 正在启动 AutoWX..."
    );

    const url =
      `https://api.github.com/repos/` +
      `${env.OWNER_GITHUB}/` +
      `${env.REPO_GITHUB}/actions/workflows/` +
      `${env.WORKFLOW_GITHUB}/dispatches`;

    const response = await fetch(url, {
      method: "POST",

      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.TOKEN_GITHUB}`,
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "AutoWX-Telegram",
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        ref: env.REF_GITHUB,
      }),
    });

    const raw = await response.text();

    if (!response.ok) {
      await sendTelegram(
        env,
        chatId,
        `❌ GitHub Actions 启动失败\nHTTP ${response.status}\n${raw.slice(0, 1000)}`
      );

      return;
    }

    let data = {};

    try {
      data = JSON.parse(raw);
    } catch {
      // 某些响应可能没有 JSON body
    }

    let msg = "✅ GitHub Actions 已启动";

    if (data.html_url) {
      msg += `\n${data.html_url}`;
    }

    await sendTelegram(
      env,
      chatId,
      msg
    );

    return;
  }


  if (
    command === "/start" ||
    command === "/help"
  ) {
    await sendTelegram(
      env,
      chatId,
      [
        "AutoWX 控制器",
        "",
        "/startvx - 启动 / 重启 VXBot",
      ].join("\n")
    );

    return;
  }

  await sendTelegram(
    env,
    chatId,
    "未知命令。使用 /startvx 启动 VXBot。"
  );
}


export default {
  async fetch(request, env, ctx) {

    if (request.method !== "POST") {
      return new Response("AutoWX Telegram Bot");
    }

    // 验证 Telegram webhook secret
    const secret = request.headers.get(
      "X-Telegram-Bot-Api-Secret-Token"
    );

    if (
      secret !== env.TELEGRAM_WEBHOOK_SECRET
    ) {
      return new Response(
        "Forbidden",
        {
          status: 403,
        }
      );
    }

    let update;

    try {
      update = await request.json();
    } catch {
      return new Response(
        "Bad Request",
        {
          status: 400,
        }
      );
    }

    // 先立即告诉 Telegram 收到了，
    // 后台再调用 GitHub，防止 webhook 重试。
    ctx.waitUntil(
      handleTelegram(update, env)
    );

    return new Response("OK");
  },
};
