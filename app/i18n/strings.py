STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>AI Digest Bot</b>\n\n"
            "Персональные AI-сводки из Telegram-каналов — без шума, только важное.\n\n"
            "<b>Шаг 1 из 4</b> — выберите язык:"
        ),
        "step_channels": (
            "<b>Шаг 2 из 4</b> — каналы для дайджеста\n\n"
            "Нажмите, чтобы включить или выключить канал.\n"
            "Выбрано: <b>{count}</b>\n\n"
            "Когда готовы — нажмите «Продолжить»."
        ),
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
            "Personal AI digests from Telegram channels — no noise, just what matters.\n\n"
            "<b>Step 1 of 4</b> — choose your language:"
        ),
        "step_channels": (
            "<b>Step 2 of 4</b> — channels for your digest\n\n"
            "Tap to enable or disable a channel.\n"
            "Selected: <b>{count}</b>\n\n"
            "When ready — tap «Continue»."
        ),
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
