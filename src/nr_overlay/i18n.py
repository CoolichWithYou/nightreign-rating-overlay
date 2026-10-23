"""UI strings for the tray and message boxes. The overlay page keeps its own copy in overlay.html."""

DEFAULT_LANGUAGE = "en"

# Shown in the language menu, each in its own language.
LANGUAGES = {"en": "English", "ru": "Русский", "zh": "中文"}

STRINGS = {
    "en": {
        "rating": "Rating: {rating} (depth {depth})",
        "session": "This session: {delta} · {wins} W / {losses} L",
        "waiting": "Waiting for the save…",
        "save_not_found": "NR0000.sl2 save not found",
        "read_failed": "Could not read the save",
        "open_overlay": "Open overlay in browser",
        "copy_url": "Copy OBS link",
        "new_session": "Start new session",
        "open_save_folder": "Open save folder",
        "language": "Language",
        "quit": "Quit",
        "already_running": "The app is already running — look for its icon in the tray.",
        "port_busy": 'Could not use port {port}: {error}\n\nChange "port" in {config} and start again.',
    },
    "ru": {
        "rating": "Рейтинг: {rating} (глубина {depth})",
        "session": "За сессию: {delta} · {wins} побед / {losses} пораж.",
        "waiting": "Ожидание сейва…",
        "save_not_found": "Сейв NR0000.sl2 не найден",
        "read_failed": "Не удалось прочитать сейв",
        "open_overlay": "Открыть оверлей в браузере",
        "copy_url": "Скопировать ссылку для OBS",
        "new_session": "Начать новую сессию",
        "open_save_folder": "Открыть папку с сейвом",
        "language": "Язык",
        "quit": "Выход",
        "already_running": "Приложение уже запущено — ищите иконку в трее.",
        "port_busy": 'Не удалось занять порт {port}: {error}\n\nПоменяйте "port" в {config} и запустите снова.',
    },
    "zh": {
        "rating": "评分：{rating}（深度 {depth}）",
        "session": "本场：{delta} · {wins} 胜 / {losses} 负",
        "waiting": "正在等待存档…",
        "save_not_found": "未找到存档 NR0000.sl2",
        "read_failed": "无法读取存档",
        "open_overlay": "在浏览器中打开叠加层",
        "copy_url": "复制 OBS 链接",
        "new_session": "开始新的统计",
        "open_save_folder": "打开存档文件夹",
        "language": "语言",
        "quit": "退出",
        "already_running": "程序已在运行，请在系统托盘中查找图标。",
        "port_busy": "无法使用端口 {port}：{error}\n\n请修改 {config} 中的 \"port\" 后重新启动。",
    },
}


def normalize_language(lang: str | None) -> str:
    return lang if lang in STRINGS else DEFAULT_LANGUAGE


def tr(lang: str, key: str, **kwargs) -> str:
    return STRINGS[normalize_language(lang)][key].format(**kwargs)
