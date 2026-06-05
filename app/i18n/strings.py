STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Персональные AI-сводки из Telegram и Gmail.\n\n"
            "<b>Шаг 1 из 3</b> — выберите язык:"
        ),
        "step_sources": (
            "<b>Шаг 2 из 3</b> — ваши источники\n\n"
            "Добавьте <b>Telegram-каналы</b> (ссылки в чат) и/или <b>Gmail</b> (кнопка ниже).\n"
            "Можно использовать оба сразу — один дайджест по расписанию.\n\n"
            "Когда готово — «Продолжить»."
        ),
        "sources_manage": (
            "<b>📋 Источники</b>\n\n"
            "Telegram: ссылки в чат, удаление — кнопкой 🗑.\n"
            "Gmail: подключить или отключить кнопкой ниже."
        ),
        "sources_add_prompt": (
            "Вставьте ссылки (можно несколько сразу, каждая с новой строки).\n"
            "Пример:\n<code>@durov</code>\n<code>https://t.me/durov</code>"
        ),
        "sources_list_header": "Добавлено каналов: <b>{count}</b>",
        "sources_list_empty": "<i>Пока нет каналов — отправьте ссылку в чат.</i>",
        "sources_added": "✅ Добавлено каналов: {count}",
        "sources_already": "ℹ️ Эти каналы уже в списке.",
        "sources_parse_failed": "❌ Не нашёл ссылок. Пример: @channel или https://t.me/channel",
        "source_removed": "Удалено",
        "btn_add_source": "➕ Добавить канал",
        "reader_not_configured": "❌ На сервере не настроен TELEGRAM_SESSION_STRING для чтения каналов.",
        "digest_truncated": "показана краткая версия",
        "btn_menu": "🏠 В меню",
        "step_frequency": (
            "<b>Шаг 3 из 3</b> — как часто присылать дайджест?\n\n"
            "Период сводки = интервал рассылки:\n"
            "• раз в 12 ч → за последние 12 часов\n"
            "• раз в день → за последние сутки\n"
            "• раз в 3 дня → за 3 дня\n"
            "• раз в неделю → за неделю"
        ),
        "step_time": (
            "<b>Шаг 4 из 4</b> — во сколько присылать?\n\n"
            "Часовой пояс: <b>{timezone}</b>\n"
            "Листайте ◀️ ▶️ и нажмите «Готово».\n"
            "При «раз в 12 ч» — в это время и через 12 часов."
        ),
        "btn_confirm_time": "✅ Готово",
        "time_picker_hint": "Выбрано: <b>{time}</b>",
        "setup_done": (
            "✅ <b>Готово!</b>\n\n"
            "📋 Каналы: <b>{channels}</b>\n"
            "📧 Gmail: {gmail}\n"
            "⏱ Расписание: <b>{frequency}</b> в <b>{time}</b>\n\n"
            "Первый дайджест придёт по расписанию. Можно получить сейчас — кнопка ниже."
        ),
        "main_menu": "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        "menu_sources": "📋 Источники",
        "menu_channels": "📋 Каналы",
        "menu_schedule": "⏱ Расписание",
        "menu_digest_now": "🔥 Получить сейчас",
        "menu_reconfigure": "🔄 Настроить заново",
        "btn_continue": "✅ Продолжить",
        "btn_back": "◀️ Назад",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "freq_12h": "⏱ Каждые 12 часов",
        "freq_1d": "📅 Раз в день",
        "freq_3d": "📅 Раз в 3 дня",
        "freq_1w": "📅 Раз в неделю",
        "freq_label_12h": "за 12 часов",
        "freq_label_1d": "за 24 часа",
        "freq_label_3d": "за 3 дня",
        "freq_label_1w": "за неделю",
        "digest_period_12h": "за 12 часов",
        "digest_period_1d": "за 24 часа",
        "digest_period_3d": "за 3 дня",
        "digest_period_1w": "за неделю",
        "digest_generating": "⏳ Генерирую дайджест <b>{label}</b>…",
        "digest_progress_fetch": "📡 Загружаю каналы <b>{label}</b>{dots}",
        "digest_progress_read": "📥 Читаю сообщения <b>{label}</b>{dots}",
        "digest_progress_ai": "🤖 AI формирует дайджест <b>{label}</b>{dots}",
        "digest_header": "🔥 *Твой дайджест {period}*",
        "digest_delivered_hint": "Следующий дайджест — по вашему расписанию.",
        "digest_failed": "❌ Не удалось сгенерировать дайджест.",
        "digest_in_progress": "⏳ Дайджест уже генерируется, подождите.",
        "no_channels_selected": "❌ Выберите хотя бы один канал.",
        "pick_channel_first": "❌ Добавьте хотя бы один канал.",
        "no_messages": "ℹ️ За период «{label}» сообщений нет.",
        "no_important": "ℹ️ Важных сообщений за этот период нет.",
        "ai_failed": "❌ Ошибка AI ({provider}).",
        "schedule_summary": (
            "<b>Ваше расписание</b>\n\n"
            "📋 Каналы: <b>{channels}</b> · 📧 Gmail: <b>{gmail}</b>\n"
            "⏱ {frequency} в {time} ({timezone})\n"
            "Последний дайджест: {last}"
        ),
        "last_never": "ещё не было",
        "channels_saved": "✅ Каналы сохранены ({count})",
        "sources_saved": "✅ Источники сохранены ({count} кан.)",
        "gmail_saved_hint": "+ Gmail",
        "gmail_status_linked": "✅ {email}",
        "gmail_status_not_linked": "<i>не подключён</i>",
        "btn_gmail_check": "🔄 Проверить Gmail",
        "no_content": "ℹ️ За период «{label}» нет новых сообщений и писем.",
        "digest_header_combined": "🔥 *Твой дайджест {period}*",
        "digest_progress_fetch_combined": "📡 Загружаю источники <b>{label}</b>{dots}",
        "digest_progress_read_combined": "📥 Читаю контент <b>{label}</b>{dots}",
        "step_platform": (
            "<b>Шаг 2 из 4</b> — откуда собирать дайджест?\n\n"
            "• <b>Telegram</b> — публичные каналы\n"
            "• <b>Gmail</b> — входящие письма"
        ),
        "platform_menu": (
            "<b>📱 Платформа</b>\n\n"
            "Сейчас: <b>{platform}</b>\n\n"
            "Дайджест собирается из выбранного источника."
        ),
        "platform_telegram": "Telegram",
        "platform_gmail": "Gmail",
        "menu_platform": "📱 Платформа",
        "menu_gmail": "📧 Gmail",
        "gmail_connect": (
            "<b>📧 Подключение Gmail</b>\n\n"
            "1. Нажмите «Подключить Gmail» и разрешите доступ (только чтение).\n"
            "2. После Google вас вернёт на наш сервер — Gmail подключится автоматически.\n"
            "3. Вернитесь в Telegram: придёт сообщение «Gmail подключён» → нажмите «Продолжить»."
        ),
        "gmail_connect_localhost": (
            "<b>📧 Подключение Gmail</b>\n\n"
            "⚠️ Сейчас redirect = <code>localhost</code> — авто-подключение не сработает.\n"
            "Админу: укажите публичный URL сервера в <code>GMAIL_REDIRECT_URI</code>.\n\n"
            "Временный обход: «Вставить ссылку» после авторизации Google.\n\n"
            "<i>Redirect URI:</i> <code>{redirect}</code>"
        ),
        "gmail_oauth_done_notify": (
            "✅ <b>Gmail подключён</b>: {email}\n\n"
            "Вернитесь в «Источники» и нажмите «Продолжить», когда будете готовы."
        ),
        "gmail_paste_prompt": (
            "Вставьте <b>полную ссылку</b> из адресной строки браузера после авторизации Google.\n\n"
            "Пример:\n"
            "<code>http://localhost:8080/oauth/gmail/callback?state=...&code=4/0A...</code>"
        ),
        "gmail_code_invalid": "❌ Не нашёл code= в сообщении. Вставьте всю ссылку из браузера.",
        "gmail_link_failed": "❌ Не удалось подключить Gmail. Код устарел — авторизуйтесь заново.",
        "gmail_api_disabled": (
            "❌ Gmail API не включён в Google Cloud.\n"
            "APIs & Services → Library → Gmail API → Enable, затем подключите Gmail заново."
        ),
        "encryption_key_missing": (
            "❌ На сервере не задан SESSION_ENCRYPTION_KEY в .env.\n"
            "Добавьте любую длинную случайную строку и перезапустите бота."
        ),
        "btn_gmail_paste": "📋 Вставить ссылку",
        "gmail_linked": "✅ Gmail подключён: <b>{email}</b>",
        "gmail_not_linked": "❌ Сначала подключите Gmail.",
        "gmail_not_configured": "❌ Gmail OAuth не настроен на сервере (GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET).",
        "gmail_fetch_failed": "❌ Не удалось загрузить письма из Gmail.",
        "gmail_disconnected": "Gmail отключён.",
        "btn_gmail_connect": "🔗 Подключить Gmail",
        "btn_gmail_disconnect": "🔌 Отключить Gmail",
        "btn_gmail_continue": "✅ Продолжить",
        "no_emails": "ℹ️ За период «{label}» писем нет.",
        "digest_header_gmail": "🔥 *Твой email-дайджест {period}*",
        "digest_progress_fetch_gmail": "📡 Загружаю Gmail <b>{label}</b>{dots}",
        "digest_progress_read_gmail": "📥 Читаю письма <b>{label}</b>{dots}",
        "setup_done_gmail": (
            "✅ <b>Готово!</b>\n\n"
            "📧 Gmail: <b>{email}</b>\n"
            "⏱ Расписание: <b>{frequency}</b> в <b>{time}</b>\n\n"
            "Первый дайджест придёт по расписанию. Можно получить сейчас — кнопка ниже."
        ),
        "pick_source_first": "❌ Настройте источник: каналы или Gmail.",
    },
    "en": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Personal AI digests from Telegram and Gmail.\n\n"
            "<b>Step 1 of 3</b> — choose your language:"
        ),
        "step_sources": (
            "<b>Step 2 of 3</b> — your sources\n\n"
            "Add <b>Telegram channels</b> (paste links in chat) and/or <b>Gmail</b> (button below).\n"
            "You can use both — one digest on your schedule.\n\n"
            "When ready — tap «Continue»."
        ),
        "sources_manage": (
            "<b>📋 Sources</b>\n\n"
            "Telegram: paste links in chat, remove with 🗑.\n"
            "Gmail: connect or disconnect with the button below."
        ),
        "sources_add_prompt": (
            "Paste links (several at once, one per line).\n"
            "Example:\n<code>@durov</code>\n<code>https://t.me/durov</code>"
        ),
        "sources_list_header": "Channels added: <b>{count}</b>",
        "sources_list_empty": "<i>No channels yet — send a link in chat.</i>",
        "sources_added": "✅ Channels added: {count}",
        "sources_already": "ℹ️ These channels are already in your list.",
        "sources_parse_failed": "❌ No links found. Example: @channel or https://t.me/channel",
        "source_removed": "Removed",
        "btn_add_source": "➕ Add channel",
        "reader_not_configured": "❌ TELEGRAM_SESSION_STRING is not configured on the server.",
        "digest_truncated": "short preview shown",
        "btn_menu": "🏠 Menu",
        "step_frequency": (
            "<b>Step 3 of 3</b> — how often to send the digest?\n\n"
            "Digest period = delivery interval:\n"
            "• every 12h → last 12 hours\n"
            "• daily → last 24 hours\n"
            "• every 3 days → last 3 days\n"
            "• weekly → last 7 days"
        ),
        "step_time": (
            "<b>Step 4 of 4</b> — what time to deliver?\n\n"
            "Timezone: <b>{timezone}</b>\n"
            "Use ◀️ ▶️ then tap «Done».\n"
            "For «every 12h» — at this time and 12 hours later."
        ),
        "btn_confirm_time": "✅ Done",
        "time_picker_hint": "Selected: <b>{time}</b>",
        "setup_done": (
            "✅ <b>All set!</b>\n\n"
            "📋 Channels: <b>{channels}</b>\n"
            "📧 Gmail: {gmail}\n"
            "⏱ Schedule: <b>{frequency}</b> at <b>{time}</b>\n\n"
            "Your first digest will arrive on schedule. Or get one now below."
        ),
        "main_menu": "🏠 <b>Main menu</b>\n\nChoose an action:",
        "menu_sources": "📋 Sources",
        "menu_channels": "📋 Channels",
        "menu_schedule": "⏱ Schedule",
        "menu_digest_now": "🔥 Get now",
        "menu_reconfigure": "🔄 Set up again",
        "btn_continue": "✅ Continue",
        "btn_back": "◀️ Back",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "freq_12h": "⏱ Every 12 hours",
        "freq_1d": "📅 Once a day",
        "freq_3d": "📅 Every 3 days",
        "freq_1w": "📅 Once a week",
        "freq_label_12h": "last 12 hours",
        "freq_label_1d": "last 24 hours",
        "freq_label_3d": "last 3 days",
        "freq_label_1w": "last 7 days",
        "digest_period_12h": "for the last 12 hours",
        "digest_period_1d": "for the last 24 hours",
        "digest_period_3d": "for the last 3 days",
        "digest_period_1w": "for the last week",
        "digest_generating": "⏳ Generating digest <b>{label}</b>…",
        "digest_progress_fetch": "📡 Fetching channels <b>{label}</b>{dots}",
        "digest_progress_read": "📥 Reading messages <b>{label}</b>{dots}",
        "digest_progress_ai": "🤖 AI is writing your digest <b>{label}</b>{dots}",
        "digest_header": "🔥 *Your digest {period}*",
        "digest_delivered_hint": "Next digest — on your schedule.",
        "digest_failed": "❌ Failed to generate digest.",
        "digest_in_progress": "⏳ Digest is already being generated, please wait.",
        "no_channels_selected": "❌ Select at least one channel.",
        "pick_channel_first": "❌ Select at least one channel first.",
        "no_messages": "ℹ️ No messages for «{label}».",
        "no_important": "ℹ️ No important messages for this period.",
        "ai_failed": "❌ AI error ({provider}).",
        "schedule_summary": (
            "<b>Your schedule</b>\n\n"
            "📋 Channels: <b>{channels}</b> · 📧 Gmail: <b>{gmail}</b>\n"
            "⏱ {frequency} at {time} ({timezone})\n"
            "Last digest: {last}"
        ),
        "last_never": "never",
        "channels_saved": "✅ Channels saved ({count})",
        "sources_saved": "✅ Sources saved ({count} ch.)",
        "gmail_saved_hint": "+ Gmail",
        "gmail_status_linked": "✅ {email}",
        "gmail_status_not_linked": "<i>not connected</i>",
        "btn_gmail_check": "🔄 Check Gmail",
        "no_content": "ℹ️ No new messages or emails for «{label}».",
        "digest_header_combined": "🔥 *Your digest {period}*",
        "digest_progress_fetch_combined": "📡 Loading sources <b>{label}</b>{dots}",
        "digest_progress_read_combined": "📥 Reading content <b>{label}</b>{dots}",
        "step_platform": (
            "<b>Step 2 of 4</b> — where to collect your digest?\n\n"
            "• <b>Telegram</b> — public channels\n"
            "• <b>Gmail</b> — inbox emails"
        ),
        "platform_menu": (
            "<b>📱 Platform</b>\n\n"
            "Current: <b>{platform}</b>\n\n"
            "Digests are built from the selected source."
        ),
        "platform_telegram": "Telegram",
        "platform_gmail": "Gmail",
        "menu_platform": "📱 Platform",
        "menu_gmail": "📧 Gmail",
        "gmail_connect": (
            "<b>📧 Connect Gmail</b>\n\n"
            "1. Tap «Connect Gmail» and allow read-only access.\n"
            "2. After Google you'll be redirected to our server — Gmail links automatically.\n"
            "3. Return to Telegram: you'll get a «Gmail connected» message → tap «Continue»."
        ),
        "gmail_connect_localhost": (
            "<b>📧 Connect Gmail</b>\n\n"
            "⚠️ Redirect is <code>localhost</code> — auto-connect won't work.\n"
            "Admin: set your server's public URL in <code>GMAIL_REDIRECT_URI</code>.\n\n"
            "Workaround: use «Paste link» after Google authorization.\n\n"
            "<i>Redirect URI:</i> <code>{redirect}</code>"
        ),
        "gmail_oauth_done_notify": (
            "✅ <b>Gmail connected</b>: {email}\n\n"
            "Go to «Sources» and tap «Continue» when ready."
        ),
        "gmail_paste_prompt": (
            "Send the <b>full URL</b> from your browser address bar after Google authorization.\n\n"
            "Example:\n"
            "<code>http://localhost:8080/oauth/gmail/callback?state=...&code=4/0A...</code>"
        ),
        "gmail_code_invalid": "❌ No code= found. Paste the full browser URL.",
        "gmail_link_failed": "❌ Failed to connect Gmail. Code expired — authorize again.",
        "gmail_api_disabled": (
            "❌ Gmail API is not enabled in Google Cloud.\n"
            "APIs & Services → Library → Gmail API → Enable, then connect Gmail again."
        ),
        "encryption_key_missing": (
            "❌ SESSION_ENCRYPTION_KEY is not set in server .env.\n"
            "Add any long random string and restart the bot."
        ),
        "btn_gmail_paste": "📋 Paste link",
        "gmail_linked": "✅ Gmail connected: <b>{email}</b>",
        "gmail_not_linked": "❌ Connect Gmail first.",
        "gmail_not_configured": "❌ Gmail OAuth is not configured on the server (GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET).",
        "gmail_fetch_failed": "❌ Failed to fetch emails from Gmail.",
        "gmail_disconnected": "Gmail disconnected.",
        "btn_gmail_connect": "🔗 Connect Gmail",
        "btn_gmail_disconnect": "🔌 Disconnect Gmail",
        "btn_gmail_continue": "✅ Continue",
        "no_emails": "ℹ️ No emails for «{label}».",
        "digest_header_gmail": "🔥 *Your email digest {period}*",
        "digest_progress_fetch_gmail": "📡 Loading Gmail <b>{label}</b>{dots}",
        "digest_progress_read_gmail": "📥 Reading emails <b>{label}</b>{dots}",
        "setup_done_gmail": (
            "✅ <b>All set!</b>\n\n"
            "📧 Gmail: <b>{email}</b>\n"
            "⏱ Schedule: <b>{frequency}</b> at <b>{time}</b>\n\n"
            "Your first digest will arrive on schedule. Or get one now below."
        ),
        "pick_source_first": "❌ Set up a source first: channels or Gmail.",
    },
}
