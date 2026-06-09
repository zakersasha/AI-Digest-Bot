STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Персональные AI-сводки из разных платформ.\n\n"
            "Выберите язык:"
        ),
        "platforms_menu": "🏠 <b>Ваши платформы</b>\n\nНажмите платформу — внутри подключение и расписание:",
        "platform_linkedin": "LinkedIn",
        "platform_coming_soon": "Скоро будет доступно",
        "soon": "скоро",
        "schedule_not_set": "расписание не задано",
        "schedule_short": "{frequency} в {time}",
        "schedule_label": "Расписание:",
        "schedule_saved": "✅ Расписание сохранено",
        "platform_not_connected": "не подключено",
        "platform_status_channels": "{count} кан.",
        "platform_status_gmail": "✅ {email}",
        "platform_connect_first": "Сначала подключите платформу",
        "platform_not_ready": "Настройте подключение и расписание",
        "platform_unavailable": "Платформа недоступна",
        "step_frequency_platform": "<b>Расписание · {platform}</b>\n\nКак часто присылать дайджест?",
        "telegram_screen_hint": (
            "<b>Два способа:</b>\n"
            "• <b>QR</b> — подключить аккаунт и выбрать каналы из подписок\n"
            "• <b>Ссылки</b> — вставить @channel или t.me/… вручную"
        ),
        "btn_tg_add_links": "🔗 Ссылки",
        "tg_status_manual": "📋 Каналы добавлены вручную",
        "tg_channels_screen_hint_linked": "Выберите из подписок или добавьте ссылкой.",
        "tg_channels_screen_hint_manual": "Добавьте каналы ссылкой. QR — чтобы выбрать из подписок.",
        "tg_channels_screen_title": "📋 Каналы",
        "tg_channels_summary": "Каналов в дайджесте: <b>{count}</b>",
        "tg_no_channels_yet": "Каналы не выбраны — откройте «Каналы».",
        "btn_tg_channels": "📋 Каналы ({count})",
        "tg_qr_prompt": (
            "<b>Сканируйте QR</b> (файл выше, не сжимайте)\n\n"
            "Телефон: <b>Настройки → Устройства → Подключить устройство</b>.\n"
            "Подтвердите вход — бот пришлёт «Telegram подключён».\n\n"
            "QR ~30 сек → «Обновить QR»."
        ),
        "btn_tg_qr_refresh": "🔄 Обновить QR",
        "tg_qr_expired": "QR истёк. Нажмите «Обновить QR» или запросите новый через «Подключить Telegram».",
        "tg_qr_refreshed": "Новый QR отправлен",
        "tg_qr_not_active": "Сначала нажмите «Подключить Telegram»",
        "tg_status_linked": "✅ Аккаунт: <b>{phone}</b>",
        "tg_status_not_linked": "<i>Аккаунт не подключён</i>",
        "platform_status_tg_linked": "✅ {phone}",
        "platform_status_tg_linked_channels": "✅ {phone} · {count} кан.",
        "btn_tg_connect": "🔗 Подключить Telegram",
        "btn_tg_disconnect": "🔌 Отключить Telegram",
        "btn_tg_continue": "✅ Продолжить",
        "btn_tg_pick_channels": "📋 Мои каналы",
        "btn_tg_pick_done": "✅ Готово",
        "btn_share_phone": "📱 Поделиться номером",
        "tg_connect_phone_prompt": (
            "<b>Вход по номеру</b> (запасной способ)\n\n"
            "Telegram может блокировать код с нового устройства — тогда используйте QR.\n\n"
            "Нажмите кнопку ниже или отправьте номер: <code>+79001234567</code>."
        ),
        "tg_code_prompt": "Введите код из Telegram (сообщение от Telegram, не SMS).",
        "tg_2fa_prompt": "Введите пароль двухфакторной аутентификации Telegram.",
        "tg_contact_invalid": "❌ Нужен ваш собственный контакт — нажмите «Поделиться номером».",
        "tg_invalid_phone": "❌ Неверный номер. Пример: <code>+79001234567</code>",
        "tg_invalid_code": "❌ Неверный код. Попробуйте ещё раз.",
        "tg_2fa_invalid": "❌ Неверный пароль 2FA.",
        "tg_code_expired": (
            "Код устарел или был запрошен повторно. "
            "Нажмите «Подключить Telegram» и запросите новый код (старый уже не подойдёт)."
        ),
        "tg_code_retry": "❌ Неверный код. Проверьте цифры в сообщении от Telegram и попробуйте ещё раз.",
        "tg_login_expired": "Сессия входа истекла. Начните подключение заново.",
        "tg_login_failed": "❌ Не удалось подключить Telegram. Попробуйте снова.",
        "tg_flood_wait": "⏳ Слишком много попыток. Подождите {seconds} сек.",
        "tg_linked": "✅ Telegram подключён: <b>{phone}</b>",
        "tg_disconnected": "Telegram отключён.",
        "tg_not_linked": "Сначала подключите Telegram.",
        "tg_oauth_done_notify": (
            "✅ <b>Telegram подключён</b>: {phone}\n\n"
            "Нажмите «Продолжить» — выберите каналы для дайджеста."
        ),
        "tg_picker_hint": "Ваши подписки ({count}). Нажмите, чтобы добавить или убрать:",
        "tg_picker_empty": "Публичных каналов в подписках не найдено. Добавьте канал вручную ссылкой.",
        "telethon_session_expired": "❌ Сессия Telegram устарела. Подключите аккаунт заново.",
        "telethon_not_linked": "❌ Сначала подключите Telegram.",
        "gmail_screen_hint": "Подключите Gmail для дайджеста входящих писем.",
        "btn_schedule": "⏱ Расписание",
        "btn_test_digest": "🔥 Тест дайджеста",
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
        "digest_nothing_new": "ℹ️ За период «{label}» ничего важного — только реклама или новостей нет.",
        "digest_link_label": "перейти",
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
            "Нажмите «Продолжить» — настройте расписание дайджеста."
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
            "Personal AI digests from multiple platforms.\n\n"
            "Choose your language:"
        ),
        "platforms_menu": "🏠 <b>Your platforms</b>\n\nTap a platform — connect and set schedule inside:",
        "platform_linkedin": "LinkedIn",
        "platform_coming_soon": "Coming soon",
        "soon": "soon",
        "schedule_not_set": "schedule not set",
        "schedule_short": "{frequency} at {time}",
        "schedule_label": "Schedule:",
        "schedule_saved": "✅ Schedule saved",
        "platform_not_connected": "not connected",
        "platform_status_channels": "{count} ch.",
        "platform_status_gmail": "✅ {email}",
        "platform_connect_first": "Connect the platform first",
        "platform_not_ready": "Set up connection and schedule",
        "platform_unavailable": "Platform unavailable",
        "step_frequency_platform": "<b>Schedule · {platform}</b>\n\nHow often to send the digest?",
        "telegram_screen_hint": (
            "<b>Two ways:</b>\n"
            "• <b>QR</b> — link account and pick channels from subscriptions\n"
            "• <b>Links</b> — paste @channel or t.me/… manually"
        ),
        "btn_tg_add_links": "🔗 Links",
        "tg_status_manual": "📋 Channels added manually",
        "tg_channels_screen_hint_linked": "Pick from subscriptions or add by link.",
        "tg_channels_screen_hint_manual": "Add channels by link. Use QR to pick from subscriptions.",
        "tg_channels_screen_title": "📋 Channels",
        "tg_channels_summary": "Channels in digest: <b>{count}</b>",
        "tg_no_channels_yet": "No channels selected — open «Channels».",
        "btn_tg_channels": "📋 Channels ({count})",
        "tg_qr_prompt": (
            "<b>Scan the QR</b> (file above — don't compress)\n\n"
            "Phone: <b>Settings → Devices → Link Desktop Device</b>.\n"
            "Confirm — the bot will send «Telegram connected».\n\n"
            "QR ~30 sec → «Refresh QR»."
        ),
        "btn_tg_qr_refresh": "🔄 Refresh QR",
        "tg_qr_expired": "QR expired. Tap «Refresh QR» or start over with «Connect Telegram».",
        "tg_qr_refreshed": "New QR sent",
        "tg_qr_not_active": "Tap «Connect Telegram» first",
        "tg_status_linked": "✅ Account: <b>{phone}</b>",
        "tg_status_not_linked": "<i>Account not connected</i>",
        "platform_status_tg_linked": "✅ {phone}",
        "platform_status_tg_linked_channels": "✅ {phone} · {count} ch.",
        "btn_tg_connect": "🔗 Connect Telegram",
        "btn_tg_disconnect": "🔌 Disconnect Telegram",
        "btn_tg_continue": "✅ Continue",
        "btn_tg_pick_channels": "📋 My channels",
        "btn_tg_pick_done": "✅ Done",
        "btn_share_phone": "📱 Share phone number",
        "tg_connect_phone_prompt": (
            "<b>Phone sign-in</b> (fallback)\n\n"
            "Telegram may block codes from new devices — prefer QR login.\n\n"
            "Tap the button below or send your number: <code>+15551234567</code>."
        ),
        "tg_code_prompt": "Enter the code from Telegram (in-app message, not SMS).",
        "tg_2fa_prompt": "Enter your Telegram two-step verification password.",
        "tg_contact_invalid": "❌ Share your own contact — tap «Share phone number».",
        "tg_invalid_phone": "❌ Invalid number. Example: <code>+15551234567</code>",
        "tg_invalid_code": "❌ Invalid code. Try again.",
        "tg_2fa_invalid": "❌ Invalid 2FA password.",
        "tg_code_expired": (
            "Code expired or was replaced by a new request. "
            "Tap «Connect Telegram» and request a fresh code."
        ),
        "tg_code_retry": "❌ Wrong code. Check the digits in Telegram's message and try again.",
        "tg_login_expired": "Login session expired. Start over.",
        "tg_login_failed": "❌ Failed to connect Telegram. Try again.",
        "tg_flood_wait": "⏳ Too many attempts. Wait {seconds} sec.",
        "tg_linked": "✅ Telegram connected: <b>{phone}</b>",
        "tg_disconnected": "Telegram disconnected.",
        "tg_not_linked": "Connect Telegram first.",
        "tg_oauth_done_notify": (
            "✅ <b>Telegram connected</b>: {phone}\n\n"
            "Tap «Continue» to pick channels for your digest."
        ),
        "tg_picker_hint": "Your subscriptions ({count}). Tap to add or remove:",
        "tg_picker_empty": "No public channels in subscriptions. Add a channel manually by link.",
        "telethon_session_expired": "❌ Telegram session expired. Connect your account again.",
        "telethon_not_linked": "❌ Connect Telegram first.",
        "gmail_screen_hint": "Connect Gmail for inbox digest.",
        "btn_schedule": "⏱ Schedule",
        "btn_test_digest": "🔥 Test digest",
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
        "digest_nothing_new": "ℹ️ Nothing important for «{label}» — only ads or no real news.",
        "digest_link_label": "open",
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
            "Tap Continue to set your digest schedule."
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
