"""User-interface translations.

Supported languages are the ones offered by the EVE Online client, plus Italian.
Log messages printed to the terminal stay in English.
"""
from Foundation import NSLocale

AUTO = "auto"
DEFAULT_LANGUAGE = "en"

#: Native name of each supported language, in the order shown in the menu.
LANGUAGE_NAMES = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "ru": "Русский",
    "ja": "日本語",
    "zh": "简体中文",
    "ko": "한국어",
    "it": "Italiano",
}

#: Translated strings, keyed by language code and then by string key.
#: Any key missing from a language falls back to English.
STRINGS = {
    "en": {
        "previews": "Previews",
        "no_clients": "No EVE clients running",
        "show_names": "Show names",
        "highlight_active": "Highlight active client",
        "hide_active_preview": "Hide active client's preview",
        "lock_positions": "Lock positions",
        "snap": "Snap to edges",
        "fps": "FPS: {fps}",
        "hide_all": "Hide all previews",
        "language": "Language",
        "language_auto": "System default",
        "open_config": "Open config folder",
        "reload_config": "Reload configuration",
        "quit": "Quit",
    },
    "de": {
        "previews": "Vorschauen",
        "no_clients": "Keine EVE-Clients aktiv",
        "show_names": "Namen anzeigen",
        "highlight_active": "Aktiven Client hervorheben",
        "hide_active_preview": "Vorschau des aktiven Clients ausblenden",
        "lock_positions": "Positionen sperren",
        "snap": "An Kanten einrasten",
        "hide_all": "Alle Vorschauen ausblenden",
        "language": "Sprache",
        "language_auto": "Systemsprache",
        "open_config": "Konfigurationsordner öffnen",
        "reload_config": "Konfiguration neu laden",
        "quit": "Beenden",
    },
    "fr": {
        "previews": "Aperçus",
        "no_clients": "Aucun client EVE ouvert",
        "show_names": "Afficher les noms",
        "highlight_active": "Mettre en évidence le client actif",
        "hide_active_preview": "Masquer l'aperçu du client actif",
        "lock_positions": "Verrouiller les positions",
        "snap": "Aimanter aux bords",
        "hide_all": "Masquer tous les aperçus",
        "language": "Langue",
        "language_auto": "Langue du système",
        "open_config": "Ouvrir le dossier de configuration",
        "reload_config": "Recharger la configuration",
        "quit": "Quitter",
    },
    "es": {
        "previews": "Vistas previas",
        "no_clients": "No hay clientes de EVE abiertos",
        "show_names": "Mostrar nombres",
        "highlight_active": "Resaltar cliente activo",
        "hide_active_preview": "Ocultar vista previa del cliente activo",
        "lock_positions": "Bloquear posiciones",
        "snap": "Ajustar a los bordes",
        "hide_all": "Ocultar todas las vistas previas",
        "language": "Idioma",
        "language_auto": "Idioma del sistema",
        "open_config": "Abrir carpeta de configuración",
        "reload_config": "Recargar configuración",
        "quit": "Salir",
    },
    "ru": {
        "previews": "Превью",
        "no_clients": "Нет запущенных клиентов EVE",
        "show_names": "Показывать имена",
        "highlight_active": "Подсвечивать активный клиент",
        "hide_active_preview": "Скрывать превью активного клиента",
        "lock_positions": "Закрепить позиции",
        "snap": "Прилипание к краям",
        "hide_all": "Скрыть все превью",
        "language": "Язык",
        "language_auto": "Язык системы",
        "open_config": "Открыть папку настроек",
        "reload_config": "Перезагрузить настройки",
        "quit": "Выход",
    },
    "ja": {
        "previews": "プレビュー",
        "no_clients": "起動中のEVEクライアントはありません",
        "show_names": "名前を表示",
        "highlight_active": "アクティブなクライアントを強調表示",
        "hide_active_preview": "アクティブなクライアントのプレビューを隠す",
        "lock_positions": "位置をロック",
        "snap": "端にスナップ",
        "hide_all": "すべてのプレビューを隠す",
        "language": "言語",
        "language_auto": "システムの言語",
        "open_config": "設定フォルダを開く",
        "reload_config": "設定を再読み込み",
        "quit": "終了",
    },
    "zh": {
        "previews": "预览",
        "no_clients": "没有运行中的 EVE 客户端",
        "show_names": "显示名称",
        "highlight_active": "高亮当前客户端",
        "hide_active_preview": "隐藏当前客户端的预览",
        "lock_positions": "锁定位置",
        "snap": "边缘吸附",
        "hide_all": "隐藏所有预览",
        "language": "语言",
        "language_auto": "跟随系统",
        "open_config": "打开配置文件夹",
        "reload_config": "重新加载配置",
        "quit": "退出",
    },
    "ko": {
        "previews": "미리보기",
        "no_clients": "실행 중인 EVE 클라이언트 없음",
        "show_names": "이름 표시",
        "highlight_active": "활성 클라이언트 강조",
        "hide_active_preview": "활성 클라이언트 미리보기 숨기기",
        "lock_positions": "위치 잠금",
        "snap": "가장자리에 맞추기",
        "hide_all": "모든 미리보기 숨기기",
        "language": "언어",
        "language_auto": "시스템 언어",
        "open_config": "설정 폴더 열기",
        "reload_config": "설정 다시 불러오기",
        "quit": "종료",
    },
    "it": {
        "previews": "Anteprime",
        "no_clients": "Nessun client EVE aperto",
        "show_names": "Mostra nomi",
        "highlight_active": "Evidenzia client attivo",
        "hide_active_preview": "Nascondi anteprima del client attivo",
        "lock_positions": "Blocca posizioni",
        "snap": "Aggancio automatico",
        "hide_all": "Nascondi tutte le anteprime",
        "language": "Lingua",
        "language_auto": "Lingua di sistema",
        "open_config": "Apri cartella configurazione",
        "reload_config": "Ricarica configurazione",
        "quit": "Esci",
    },
}


def system_language():
    """Return the first macOS preferred language that EVEView supports.

    Falls back to English if none of the user's languages is supported.
    """
    for code in NSLocale.preferredLanguages() or []:
        prefix = str(code).split("-")[0].lower()
        if prefix in STRINGS:
            return prefix
    return DEFAULT_LANGUAGE


class Translator:
    """Callable that returns UI strings in the current language.

    Usage: ``tr("quit")`` or ``tr("fps", fps=15)``.
    """

    def __init__(self, language=AUTO):
        self.language = DEFAULT_LANGUAGE
        self.set_language(language)

    def set_language(self, language):
        """Switch language. ``"auto"`` follows the macOS preferences."""
        if language == AUTO:
            self.language = system_language()
        elif language in STRINGS:
            self.language = language
        else:
            print(f"[i18n] Unknown language '{language}', using English")
            self.language = DEFAULT_LANGUAGE

    def __call__(self, key, **kwargs):
        text = STRINGS[self.language].get(key) or STRINGS[DEFAULT_LANGUAGE][key]
        return text.format(**kwargs) if kwargs else text