STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Персональные AI-сводки из ваших Telegram-каналов.\n\n"
            "<b>Шаг 1 из 5</b> — выберите язык:"
        ),
        "step_connect_qr": (
            "<b>Шаг 2 из 5</b> — подключите Telegram\n\n"
            "Сканируйте QR-код на фото ниже (рекомендуется).\n"
            "Код из SMS через прокси часто не срабатывает."
        ),
        "step_connect_phone": (
            "<b>Шаг 2 из 5</b> — вход по номеру\n\n"
            "Нажмите «Поделиться номером» внизу чата."
        ),
        "step_qr_caption": (
            "Telegram → <b>Настройки</b> → <b>Устройства</b> → "
            "<b>Подключить устройство</b> → сканируйте этот QR.\n\n"
            "После сканирования бот продолжит автоматически."
        ),
        "qr_scan_hint": "Сканируйте QR на фото выше. Если истёк — «Обновить QR».",
        "qr_failed": "❌ Не удалось запустить QR-вход. Попробуйте «Обновить QR».",
        "btn_refresh_qr": "🔄 Обновить QR",
        "btn_login_by_phone": "📱 Войти по номеру (запасной)",
        "step_2fa_password": "Введите пароль двухфакторной аутентификации Telegram:",
        "share_phone_hint": "Нажмите «Поделиться номером»",
        "step_code": (
            "<b>Шаг 2 из 5</b> — код из Telegram\n\n"
            "Отправьте <b>только цифры</b> из последнего сообщения Telegram "
            "(не из старых уведомлений).\n"
            "Телефон: <code>{phone}</code>"
        ),
        "code_use_latest": "⚠️ Используйте код из <b>последнего</b> сообщения Telegram.",
        "step_2fa": (
            "<b>Двухфакторная защита</b>\n\n"
            "Отправьте пароль облачного пароля Telegram."
        ),
        "step_channels": (
            "<b>Шаг 3 из 5</b> — ваши подписки\n\n"
            "Публичные каналы и группы с @username.\n"
            "Выбрано: <b>{count}</b>\n\n"
            "🔄 — обновить список · ✅ — продолжить"
        ),
        "channels_loading": "⏳ Загружаю ваши подписки из Telegram…",
        "telegram_linked": "✅ Telegram подключён ({phone})",
        "telegram_not_linked": "❌ Сначала подключите Telegram (шаг 2).",
        "btn_share_phone": "📱 Поделиться номером",
        "login_connecting": "⏳ Подключаюсь к Telegram…",
        "login_wait": "⏳ Отправляю код… Дождитесь экрана ввода кода.",
        "login_wait_for_code_screen": "⏳ Сначала дождитесь сообщения с полем для кода.",
        "invalid_phone_format": "❌ Некорректный номер. Поделитесь контактом или введите +79001234567",
        "invalid_code_format": "❌ Код — только цифры из SMS/Telegram.",
        "code_resent": "Новый код отправлен",
        "contact_must_be_yours": "❌ Нужен ваш контакт, не чужой.",
        "btn_resend_code": "🔄 Отправить код снова",
        "btn_disconnect": "🔌 Отключить Telegram",
        "share_phone_hint": "Нажмите кнопку и выберите «Поделиться контактом»",
        "channels_empty": (
            "Не найдено публичных каналов в подписках.\n\n"
            "Подпишитесь на каналы с @username в Telegram и нажмите 🔄."
        ),
        "channels_refreshed": "Список обновлён",
        "digest_truncated": "показана краткая версия",
        "btn_menu": "🏠 В меню",
        "step_frequency": (
            "<b>Шаг 4 из 5</b> — как часто присылать дайджест?\n\n"
            "Период сводки = интервал рассылки:\n"
            "• раз в 12 ч → за последние 12 часов\n"
            "• раз в день → за последние сутки\n"
            "• раз в 3 дня → за 3 дня\n"
            "• раз в неделю → за неделю"
        ),
        "step_time": (
            "<b>Шаг 5 из 5</b> — во сколько присылать?\n\n"
            "Часовой пояс: <b>{timezone}</b>\n"
            "При «раз в 12 ч» — в это время и через 12 часов."
        ),
        "setup_done": (
            "✅ <b>Готово!</b>\n\n"
            "📋 Каналы: <b>{channels}</b>\n"
            "⏱ Расписание: <b>{frequency}</b> в <b>{time}</b>\n\n"
            "Первый дайджест придёт по расписанию. Можно получить сейчас — кнопка ниже."
        ),
        "main_menu": "🏠 <b>Главное меню</b>\n\nВыберите действие:",
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
        "freq_label_1d": "за сутки",
        "freq_label_3d": "за 3 дня",
        "freq_label_1w": "за неделю",
        "digest_generating": "⏳ Генерирую дайджест <b>{label}</b>…",
        "digest_header": "🔥 *AI Дайджест* ({label})",
        "digest_delivered_hint": "Следующий дайджест — по вашему расписанию.",
        "digest_failed": "❌ Не удалось сгенерировать дайджест.",
        "no_channels_selected": "❌ Выберите хотя бы один канал.",
        "pick_channel_first": "❌ Сначала выберите хотя бы один канал.",
        "no_messages": "ℹ️ За период «{label}» сообщений нет.",
        "no_important": "ℹ️ Важных сообщений за этот период нет.",
        "ai_failed": "❌ Ошибка AI ({provider}).",
        "schedule_summary": (
            "<b>Ваше расписание</b>\n\n"
            "⏱ {frequency} в {time} ({timezone})\n"
            "Последний дайджест: {last}"
        ),
        "last_never": "ещё не было",
        "channels_saved": "✅ Каналы сохранены ({count})",
    },
    "en": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Personal AI digests from your Telegram channels.\n\n"
            "<b>Step 1 of 5</b> — choose your language:"
        ),
        "step_connect_qr": (
            "<b>Step 2 of 5</b> — connect Telegram\n\n"
            "Scan the QR code in the photo below (recommended).\n"
            "SMS codes often fail through a proxy."
        ),
        "step_connect_phone": (
            "<b>Step 2 of 5</b> — login by phone\n\n"
            "Tap «Share phone number» at the bottom."
        ),
        "step_qr_caption": (
            "Telegram → <b>Settings</b> → <b>Devices</b> → "
            "<b>Link Desktop Device</b> → scan this QR.\n\n"
            "The bot will continue automatically after scanning."
        ),
        "qr_scan_hint": "Scan the QR in the photo above. If expired — tap «Refresh QR».",
        "qr_failed": "❌ Could not start QR login. Try «Refresh QR».",
        "btn_refresh_qr": "🔄 Refresh QR",
        "btn_login_by_phone": "📱 Login by phone (fallback)",
        "step_2fa_password": "Enter your Telegram 2FA password:",
        "share_phone_hint": "Tap «Share phone number»",
        "step_code": (
            "<b>Step 2 of 5</b> — code from Telegram\n\n"
            "Send <b>digits only</b> from the latest Telegram message "
            "(not old notifications).\n"
            "Phone: <code>{phone}</code>"
        ),
        "code_use_latest": "⚠️ Use the code from the <b>latest</b> Telegram message.",
        "step_2fa": (
            "<b>Two-factor authentication</b>\n\n"
            "Send your Telegram cloud password."
        ),
        "step_channels": (
            "<b>Step 3 of 5</b> — your subscriptions\n\n"
            "Public channels and groups with @username.\n"
            "Selected: <b>{count}</b>\n\n"
            "🔄 — refresh · ✅ — continue"
        ),
        "channels_loading": "⏳ Loading your Telegram subscriptions…",
        "telegram_linked": "✅ Telegram connected ({phone})",
        "telegram_not_linked": "❌ Connect Telegram first (step 2).",
        "btn_share_phone": "📱 Share phone number",
        "login_connecting": "⏳ Connecting to Telegram…",
        "login_wait": "⏳ Sending code… Wait for the code entry screen.",
        "login_wait_for_code_screen": "⏳ Wait until the bot shows the code entry screen.",
        "invalid_phone_format": "❌ Invalid number. Share contact or enter +79001234567",
        "invalid_code_format": "❌ Code must be digits from SMS/Telegram.",
        "code_resent": "New code sent",
        "contact_must_be_yours": "❌ Please share your own contact.",
        "btn_resend_code": "🔄 Resend code",
        "btn_disconnect": "🔌 Disconnect Telegram",
        "share_phone_hint": "Tap the button and choose «Share contact»",
        "channels_empty": (
            "No public channels found in subscriptions.\n\n"
            "Subscribe to channels with @username in Telegram and tap 🔄."
        ),
        "channels_refreshed": "List refreshed",
        "digest_truncated": "short preview shown",
        "btn_menu": "🏠 Menu",
        "step_frequency": (
            "<b>Step 4 of 5</b> — how often to send the digest?\n\n"
            "Digest period = delivery interval:\n"
            "• every 12h → last 12 hours\n"
            "• daily → last 24 hours\n"
            "• every 3 days → last 3 days\n"
            "• weekly → last 7 days"
        ),
        "step_time": (
            "<b>Step 5 of 5</b> — what time to deliver?\n\n"
            "Timezone: <b>{timezone}</b>\n"
            "For «every 12h» — at this time and 12 hours later."
        ),
        "setup_done": (
            "✅ <b>All set!</b>\n\n"
            "📋 Channels: <b>{channels}</b>\n"
            "⏱ Schedule: <b>{frequency}</b> at <b>{time}</b>\n\n"
            "Your first digest will arrive on schedule. Or get one now below."
        ),
        "main_menu": "🏠 <b>Main menu</b>\n\nChoose an action:",
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
        "digest_generating": "⏳ Generating digest <b>{label}</b>…",
        "digest_header": "🔥 *AI Digest* ({label})",
        "digest_delivered_hint": "Next digest — on your schedule.",
        "digest_failed": "❌ Failed to generate digest.",
        "no_channels_selected": "❌ Select at least one channel.",
        "pick_channel_first": "❌ Select at least one channel first.",
        "no_messages": "ℹ️ No messages for «{label}».",
        "no_important": "ℹ️ No important messages for this period.",
        "ai_failed": "❌ AI error ({provider}).",
        "schedule_summary": (
            "<b>Your schedule</b>\n\n"
            "⏱ {frequency} at {time} ({timezone})\n"
            "Last digest: {last}"
        ),
        "last_never": "never",
        "channels_saved": "✅ Channels saved ({count})",
    },
}
