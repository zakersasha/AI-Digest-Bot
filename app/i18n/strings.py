STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Персональные AI-сводки из ваших Telegram-каналов.\n\n"
            "<b>Шаг 1 из 4</b> — выберите язык:"
        ),
        "step_sources": (
            "<b>Шаг 2 из 4</b> — каналы для дайджеста\n\n"
            "Вставьте ссылки одним сообщением (до 10–15 каналов):\n"
            "• каждая ссылка с новой строки, или\n"
            "• через пробел / запятую\n\n"
            "Формат: <code>@channel</code> или <code>https://t.me/channel</code>\n"
            "Когда каналы появятся в списке — нажмите «Продолжить»."
        ),
        "sources_manage": (
            "<b>📋 Ваши каналы</b>\n\n"
            "Отправьте новые ссылки в чат или удалите кнопкой 🗑."
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
            "<b>Шаг 3 из 4</b> — как часто присылать дайджест?\n\n"
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
            "<b>Step 1 of 4</b> — choose your language:"
        ),
        "step_sources": (
            "<b>Step 2 of 4</b> — channels for your digest\n\n"
            "Paste links in <b>one message</b> (up to 10–15 channels):\n"
            "• one link per line, or\n"
            "• separated by space / comma\n\n"
            "Format: <code>@channel</code> or <code>https://t.me/channel</code>\n"
            "When channels appear in the list — tap «Continue»."
        ),
        "sources_manage": (
            "<b>📋 Your channels</b>\n\n"
            "Send new links in chat or remove with 🗑."
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
            "<b>Step 3 of 4</b> — how often to send the digest?\n\n"
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
            "⏱ {frequency} at {time} ({timezone})\n"
            "Last digest: {last}"
        ),
        "last_never": "never",
        "channels_saved": "✅ Channels saved ({count})",
    },
}
