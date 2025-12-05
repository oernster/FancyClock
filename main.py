import sys
import os
import ctypes
import pytz
import re
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox, QSizePolicy, QScrollArea, QDialog, QLineEdit, QListWidget
from PySide6.QtCore import QTimer, QTime, QDateTime, Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimeZone
from PySide6.QtGui import QIcon, QAction
from analog_clock import AnalogClock
from digital_clock import DigitalClock
from ntp_client import NTPClient
from datetime import datetime, timezone
from localization.i18n_manager import I18nManager

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ClockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fancy Clock")
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resource_path("clock.ico")))
        self.resize(400, 440)

        self.i18n_manager = I18nManager()
        self.i18n_manager = I18nManager()
        self.i18n_manager.set_locale(self.i18n_manager.detect_system_locale())
        self._create_menu_bar()
        self.ntp_client = NTPClient()
        self.time_offset = 0
        self.time_zone = QTimeZone.systemTimeZone()
        self.synchronize_time()
        self.old_pos = None
        self.tz_locale_map = {
    "Europe/Andorra": "ca_AD",
    "Asia/Dubai": "ar_AE",
    "Asia/Kabul": "fa_AF",
    "America/Antigua": "en_AG",
    "America/Anguilla": "en_AI",
    "Europe/Tirane": "sq_AL",
    "Asia/Yerevan": "hy_AM",
    "America/Curacao": "nl_AN",
    "Africa/Luanda": "pt_AO",
    "Antarctica/McMurdo": "en_US",
    "Antarctica/Casey": "en_US",
    "Antarctica/Davis": "en_US",
    "Antarctica/DumontDUrville": "fr_FR",
    "Antarctica/Mawson": "en_US",
    "Antarctica/Palmer": "en_US",
    "Antarctica/Rothera": "en_US",
    "Antarctica/Syowa": "ja_JP",
    "Antarctica/Troll": "nb_NO",
    "Antarctica/Vostok": "en_US",
    "America/Argentina/Buenos_Aires": "es_AR",
    "America/Argentina/Cordoba": "es_AR",
    "America/Argentina/Salta": "es_AR",
    "America/Argentina/Jujuy": "es_AR",
    "America/Argentina/Tucuman": "es_AR",
    "America/Argentina/Catamarca": "es_AR",
    "America/Argentina/La_Rioja": "es_AR",
    "America/Argentina/San_Juan": "es_AR",
    "America/Argentina/Mendoza": "es_AR",
    "America/Argentina/San_Luis": "es_AR",
    "America/Argentina/Rio_Gallegos": "es_AR",
    "America/Argentina/Ushuaia": "es_AR",
    "Pacific/Pago_Pago": "en_AS",
    "Europe/Vienna": "de_AT",
    "Australia/Lord_Howe": "en_AU",
    "Antarctica/Macquarie": "en_AU",
    "Australia/Hobart": "en_AU",
    "Australia/Currie": "en_AU",
    "Australia/Melbourne": "en_AU",
    "Australia/Sydney": "en_AU",
    "Australia/Broken_Hill": "en_AU",
    "Australia/Brisbane": "en_AU",
    "Australia/Lindeman": "en_AU",
    "Australia/Adelaide": "en_AU",
    "Australia/Darwin": "en_AU",
    "Australia/Perth": "en_AU",
    "Australia/Eucla": "en_AU",
    "America/Aruba": "nl_AW",
    "Europe/Mariehamn": "sv_AX",
    "Asia/Baku": "az_AZ",
    "Europe/Sarajevo": "bs_BA",
    "America/Barbados": "en_BB",
    "Asia/Dhaka": "bn_BD",
    "Europe/Brussels": "nl_BE",
    "Africa/Ouagadougou": "fr_BF",
    "Europe/Sofia": "bg_BG",
    "Asia/Bahrain": "ar_BH",
    "Africa/Bujumbura": "fr_BI",
    "Africa/Porto-Novo": "fr_BJ",
    "America/St_Barthelemy": "fr_BL",
    "Atlantic/Bermuda": "en_BM",
    "Asia/Brunei": "ms_BN",
    "America/La_Paz": "es_BO",
    "America/Kralendijk": "nl_BQ",
    "America/Noronha": "pt_BR",
    "America/Belem": "pt_BR",
    "America/Fortaleza": "pt_BR",
    "America/Recife": "pt_BR",
    "America/Araguaina": "pt_BR",
    "America/Maceio": "pt_BR",
    "America/Bahia": "pt_BR",
    "America/Sao_Paulo": "pt_BR",
    "America/Campo_Grande": "pt_BR",
    "America/Cuiaba": "pt_BR",
    "America/Santarem": "pt_BR",
    "America/Porto_Velho": "pt_BR",
    "America/Boa_Vista": "pt_BR",
    "America/Manaus": "pt_BR",
    "America/Eirunepe": "pt_BR",
    "America/Rio_Branco": "pt_BR",
    "America/Nassau": "en_BS",
    "Asia/Thimphu": "dz_BT",
    "Africa/Gaborone": "en_BW",
    "Europe/Minsk": "be_BY",
    "America/Belize": "en_BZ",
    "America/St_Johns": "en_CA",
    "America/Halifax": "en_CA",
    "America/Glace_Bay": "en_CA",
    "America/Moncton": "en_CA",
    "America/Goose_Bay": "en_CA",
    "America/Blanc-Sablon": "fr_CA",
    "America/Toronto": "en_CA",
    "America/Nipigon": "en_CA",
    "America/Thunder_Bay": "en_CA",
    "America/Iqaluit": "iu_CA",
    "America/Pangnirtung": "iu_CA",
    "America/Atikokan": "en_CA",
    "America/Winnipeg": "en_CA",
    "America/Rainy_River": "en_CA",
    "America/Resolute": "en_CA",
    "America/Rankin_Inlet": "iu_CA",
    "America/Regina": "en_CA",
    "America/Swift_Current": "en_CA",
    "America/Edmonton": "en_CA",
    "America/Cambridge_Bay": "en_CA",
    "America/Yellowknife": "en_CA",
    "America/Inuvik": "en_CA",
    "America/Creston": "en_CA",
    "America/Dawson_Creek": "en_CA",
    "America/Fort_Nelson": "en_CA",
    "America/Vancouver": "en_CA",
    "America/Whitehorse": "en_CA",
    "America/Dawson": "en_CA",
    "Indian/Cocos": "en_CC",
    "Africa/Kinshasa": "fr_CD",
    "Africa/Lubumbashi": "fr_CD",
    "Africa/Bangui": "fr_CF",
    "Africa/Brazzaville": "fr_CG",
    "Europe/Zurich": "de_CH",
    "Africa/Abidjan": "fr_CI",
    "Pacific/Rarotonga": "en_CK",
    "America/Santiago": "es_CL",
    "America/Punta_Arenas": "es_CL",
    "Pacific/Easter": "es_CL",
    "Africa/Douala": "fr_CM",
    "Asia/Shanghai": "zh_CN",
    "Asia/Urumqi": "zh_CN",
    "America/Bogota": "es_CO",
    "America/Costa_Rica": "es_CR",
    "America/Havana": "es_CU",
    "Atlantic/Cape_Verde": "pt_CV",
    "Indian/Christmas": "en_CX",
    "Asia/Nicosia": "el_CY",
    "Asia/Famagusta": "tr_CY",
    "Europe/Prague": "cs_CZ",
    "Europe/Berlin": "de_DE",
    "Europe/Busingen": "de_DE",
    "Africa/Djibouti": "fr_DJ",
    "Europe/Copenhagen": "da_DK",
    "America/Dominica": "en_DM",
    "America/Santo_Domingo": "es_DO",
    "Africa/Algiers": "ar_DZ",
    "America/Guayaquil": "es_EC",
    "Pacific/Galapagos": "es_EC",
    "Europe/Tallinn": "et_EE",
    "Africa/Cairo": "ar_EG",
    "Africa/El_Aaiun": "ar_EH",
    "Africa/Asmara": "ti_ER",
    "Europe/Madrid": "es_ES",
    "Africa/Ceuta": "es_ES",
    "Atlantic/Canary": "es_ES",
    "Africa/Addis_Ababa": "am_ET",
    "Europe/Helsinki": "fi_FI",
    "Pacific/Fiji": "en_FJ",
    "Atlantic/Stanley": "en_FK",
    "Pacific/Chuuk": "en_FM",
    "Pacific/Pohnpei": "en_FM",
    "Pacific/Kosrae": "en_FM",
    "Atlantic/Faroe": "fo_FO",
    "Europe/Paris": "fr_FR",
    "Africa/Libreville": "fr_GA",
    "Europe/London": "en_GB",
    "America/Grenada": "en_GD",
    "Asia/Tbilisi": "ka_GE",
    "America/Cayenne": "fr_GF",
    "Europe/Guernsey": "en_GG",
    "Africa/Accra": "en_GH",
    "Europe/Gibraltar": "en_GI",
    "America/Godthab": "kl_GL",
    "America/Danmarkshavn": "da_GL",
    "America/Scoresbysund": "da_GL",
    "America/Thule": "da_GL",
    "Africa/Banjul": "en_GM",
    "Africa/Conakry": "fr_GN",
    "America/Guadeloupe": "fr_GP",
    "Africa/Malabo": "es_GQ",
    "Europe/Athens": "el_GR",
    "Atlantic/South_Georgia": "en_GB",
    "America/Guatemala": "es_GT",
    "Pacific/Guam": "en_GU",
    "Africa/Bissau": "pt_GW",
    "America/Guyana": "en_GY",
    "Asia/Hong_Kong": "zh_HK",
    "America/Tegucigalpa": "es_HN",
    "Europe/Zagreb": "hr_HR",
    "America/Port-au-Prince": "fr_HT",
    "Europe/Budapest": "hu_HU",
    "Asia/Jakarta": "id_ID",
    "Asia/Pontianak": "id_ID",
    "Asia/Makassar": "id_ID",
    "Asia/Jayapura": "id_ID",
    "Europe/Dublin": "en_IE",
    "Asia/Jerusalem": "he_IL",
    "Europe/Isle_of_Man": "en_IM",
    "Asia/Kolkata": "hi_IN",
    "Indian/Chagos": "en_GB",
    "Asia/Baghdad": "ar_IQ",
    "Asia/Tehran": "fa_IR",
    "Atlantic/Reykjavik": "is_IS",
    "Europe/Rome": "it_IT",
    "Europe/Jersey": "en_JE",
    "America/Jamaica": "en_JM",
    "Asia/Amman": "ar_JO",
    "Asia/Tokyo": "ja_JP",
    "Africa/Nairobi": "en_KE",
    "Asia/Bishkek": "ky_KG",
    "Asia/Phnom_Penh": "km_KH",
    "Pacific/Tarawa": "en_KI",
    "Pacific/Enderbury": "en_KI",
    "Pacific/Kiritimati": "en_KI",
    "Indian/Comoro": "fr_KM",
    "America/St_Kitts": "en_KN",
    "Asia/Pyongyang": "ko_KP",
    "Asia/Seoul": "ko_KR",
    "Asia/Kuwait": "ar_KW",
    "America/Cayman": "en_KY",
    "Asia/Almaty": "kk_KZ",
    "Asia/Qyzylorda": "kk_KZ",
    "Asia/Qostanay": "kk_KZ",
    "Asia/Aqtobe": "kk_KZ",
    "Asia/Aqtau": "kk_KZ",
    "Asia/Atyrau": "kk_KZ",
    "Asia/Oral": "kk_KZ",
    "Asia/Vientiane": "lo_LA",
    "Asia/Beirut": "ar_LB",
    "America/St_Lucia": "en_LC",
    "Europe/Vaduz": "de_LI",
    "Asia/Colombo": "si_LK",
    "Africa/Monrovia": "en_LR",
    "Africa/Maseru": "en_LS",
    "Europe/Vilnius": "lt_LT",
    "Europe/Luxembourg": "fr_LU",
    "Europe/Riga": "lv_LV",
    "Africa/Tripoli": "ar_LY",
    "Africa/Casablanca": "ar_MA",
    "Europe/Monaco": "fr_MC",
    "Europe/Chisinau": "ro_MD",
    "Europe/Podgorica": "sr_ME",
    "America/Marigot": "fr_MF",
    "Indian/Antananarivo": "mg_MG",
    "Pacific/Majuro": "en_MH",
    "Pacific/Kwajalein": "en_MH",
    "Europe/Skopje": "mk_MK",
    "Africa/Bamako": "fr_ML",
    "Asia/Yangon": "my_MM",
    "Asia/Ulaanbaatar": "mn_MN",
    "Asia/Hovd": "mn_MN",
    "Asia/Choibalsan": "mn_MN",
    "Asia/Macau": "zh_MO",
    "Pacific/Saipan": "en_MP",
    "America/Martinique": "fr_MQ",
    "Africa/Nouakchott": "fr_MR",
    "America/Montserrat": "en_MS",
    "Europe/Malta": "mt_MT",
    "Indian/Mauritius": "en_MU",
    "Indian/Maldives": "dv_MV",
    "Africa/Blantyre": "en_MW",
    "America/Mexico_City": "es_MX",
    "America/Cancun": "es_MX",
    "America/Merida": "es_MX",
    "America/Monterrey": "es_MX",
    "America/Matamoros": "es_MX",
    "America/Mazatlan": "es_MX",
    "America/Chihuahua": "es_MX",
    "America/Ojinaga": "es_MX",
    "America/Hermosillo": "es_MX",
    "America/Tijuana": "es_MX",
    "America/Bahia_Banderas": "es_MX",
    "Asia/Kuala_Lumpur": "ms_MY",
    "Asia/Kuching": "ms_MY",
    "Africa/Maputo": "pt_MZ",
    "Africa/Windhoek": "en_NA",
    "Pacific/Noumea": "fr_NC",
    "Africa/Niamey": "fr_NE",
    "Pacific/Norfolk": "en_NF",
    "Africa/Lagos": "en_NG",
    "America/Managua": "es_NI",
    "Europe/Amsterdam": "nl_NL",
    "Europe/Oslo": "nb_NO",
    "Asia/Kathmandu": "ne_NP",
    "Pacific/Nauru": "en_NR",
    "Pacific/Niue": "en_NU",
    "Pacific/Auckland": "en_NZ",
    "Pacific/Chatham": "en_NZ",
    "Asia/Muscat": "ar_OM",
    "America/Panama": "es_PA",
    "America/Lima": "es_PE",
    "Pacific/Tahiti": "fr_PF",
    "Pacific/Marquesas": "fr_PF",
    "Pacific/Gambier": "fr_PF",
    "Pacific/Port_Moresby": "en_PG",
    "Pacific/Bougainville": "en_PG",
    "Asia/Manila": "en_PH",
    "Asia/Karachi": "ur_PK",
    "Europe/Warsaw": "pl_PL",
    "America/Miquelon": "fr_PM",
    "Pacific/Pitcairn": "en_GB",
    "America/Puerto_Rico": "es_PR",
    "Asia/Gaza": "ar_PS",
    "Asia/Hebron": "ar_PS",
    "Europe/Lisbon": "pt_PT",
    "Atlantic/Madeira": "pt_PT",
    "Atlantic/Azores": "pt_PT",
    "Pacific/Palau": "en_PW",
    "America/Asuncion": "es_PY",
    "Asia/Qatar": "ar_QA",
    "Indian/Reunion": "fr_RE",
    "Europe/Bucharest": "ro_RO",
    "Europe/Belgrade": "sr_RS",
    "Europe/Kaliningrad": "ru_RU",
    "Europe/Moscow": "ru_RU",
    "Europe/Kirov": "ru_RU",
    "Europe/Volgograd": "ru_RU",
    "Europe/Saratov": "ru_RU",
    "Europe/Ulyanovsk": "ru_RU",
    "Europe/Astrakhan": "ru_RU",
    "Europe/Samara": "ru_RU",
    "Asia/Yekaterinburg": "ru_RU",
    "Asia/Omsk": "ru_RU",
    "Asia/Novosibirsk": "ru_RU",
    "Asia/Barnaul": "ru_RU",
    "Asia/Tomsk": "ru_RU",
    "Asia/Novokuznetsk": "ru_RU",
    "Asia/Krasnoyarsk": "ru_RU",
    "Asia/Irkutsk": "ru_RU",
    "Asia/Chita": "ru_RU",
    "Asia/Yakutsk": "ru_RU",
    "Asia/Khandyga": "ru_RU",
    "Asia/Vladivostok": "ru_RU",
    "Asia/Ust-Nera": "ru_RU",
    "Asia/Magadan": "ru_RU",
    "Asia/Sakhalin": "ru_RU",
    "Asia/Srednekolymsk": "ru_RU",
    "Asia/Kamchatka": "ru_RU",
    "Asia/Anadyr": "ru_RU",
    "Africa/Kigali": "rw_RW",
    "Asia/Riyadh": "ar_SA",
    "Pacific/Guadalcanal": "en_SB",
    "Indian/Mahe": "fr_SC",
    "Africa/Khartoum": "ar_SD",
    "Europe/Stockholm": "sv_SE",
    "Asia/Singapore": "en_SG",
    "Atlantic/St_Helena": "en_GB",
    "Europe/Ljubljana": "sl_SI",
    "Arctic/Longyearbyen": "nb_NO",
    "Europe/Bratislava": "sk_SK",
    "Africa/Freetown": "en_SL",
    "Europe/San_Marino": "it_SM",
    "Africa/Dakar": "fr_SN",
    "Africa/Mogadishu": "so_SO",
    "America/Paramaribo": "nl_SR",
    "Africa/Juba": "en_SS",
    "Africa/Sao_Tome": "pt_ST",
    "America/El_Salvador": "es_SV",
    "America/Lower_Princes": "nl_SX",
    "Asia/Damascus": "ar_SY",
    "Africa/Mbabane": "en_SZ",
    "America/Grand_Turk": "en_GB",
    "Africa/Ndjamena": "fr_TD",
    "Indian/Kerguelen": "fr_FR",
    "Africa/Lome": "fr_TG",
    "Asia/Bangkok": "th_TH",
    "Asia/Dushanbe": "tg_TJ",
    "Pacific/Fakaofo": "en_TK",
    "Asia/Dili": "pt_TL",
    "Asia/Ashgabat": "tk_TM",
    "Africa/Tunis": "ar_TN",
    "Pacific/Tongatapu": "to_TO",
    "Europe/Istanbul": "tr_TR",
    "America/Port_of_Spain": "en_TT",
    "Pacific/Funafuti": "en_TV",
    "Asia/Taipei": "zh_TW",
    "Africa/Dar_es_Salaam": "sw_TZ",
    "Europe/Simferopol": "ru_UA",
    "Europe/Kiev": "uk_UA",
    "Europe/Uzhgorod": "uk_UA",
    "Europe/Zaporozhye": "uk_UA",
    "Africa/Kampala": "en_UG",
    "Pacific/Midway": "en_US",
    "Pacific/Wake": "en_US",
    "America/New_York": "en_US",
    "America/Detroit": "en_US",
    "America/Kentucky/Louisville": "en_US",
    "America/Kentucky/Monticello": "en_US",
    "America/Indiana/Indianapolis": "en_US",
    "America/Indiana/Vincennes": "en_US",
    "America/Indiana/Winamac": "en_US",
    "America/Indiana/Marengo": "en_US",
    "America/Indiana/Petersburg": "en_US",
    "America/Indiana/Vevay": "en_US",
    "America/Chicago": "en_US",
    "America/Indiana/Tell_City": "en_US",
    "America/Indiana/Knox": "en_US",
    "America/Menominee": "en_US",
    "America/North_Dakota/Center": "en_US",
    "America/North_Dakota/New_Salem": "en_US",
    "America/North_Dakota/Beulah": "en_US",
    "America/Denver": "en_US",
    "America/Boise": "en_US",
    "America/Phoenix": "en_US",
    "America/Los_Angeles": "en_US",
    "America/Anchorage": "en_US",
    "America/Juneau": "en_US",
    "America/Sitka": "en_US",
    "America/Metlakatla": "en_US",
    "America/Yakutat": "en_US",
    "America/Nome": "en_US",
    "America/Adak": "en_US",
    "Pacific/Honolulu": "en_US",
    "America/Montevideo": "es_UY",
    "Asia/Samarkand": "uz_UZ",
    "Asia/Tashkent": "uz_UZ",
    "Europe/Vatican": "it_VA",
    "America/St_Vincent": "en_VC",
    "America/Caracas": "es_VE",
    "America/Tortola": "en_VG",
    "America/St_Thomas": "en_VI",
    "Asia/Ho_Chi_Minh": "vi_VN",
    "Pacific/Efate": "fr_VU",
    "Pacific/Wallis": "fr_WF",
    "Pacific/Apia": "en_US",
    "Asia/Aden": "ar_YE",
    "Indian/Mayotte": "fr_YT",
    "Africa/Johannesburg": "en_ZA",
    "Africa/Lusaka": "en_ZM",
    "Africa/Harare": "en_ZW",
}

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.analog_clock = AnalogClock(self, i18n_manager=self.i18n_manager)
        self.layout.addWidget(self.analog_clock)
        self.layout.addSpacing(10)
        self.digital_clock = DigitalClock(self)
        self.digital_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.addWidget(self.digital_clock)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(16) # ~60 FPS

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def show(self):
        super().show()
        self.animation.start()

    def synchronize_time(self):
        ntp_time = self.ntp_client.get_time()
        local_time = datetime.now(timezone.utc)
        self.time_offset = (ntp_time - local_time).total_seconds()

    def get_current_time(self):
        current_time = QDateTime.currentDateTimeUtc().addSecs(int(self.time_offset))
        return current_time.toTimeZone(self.time_zone)

    def update_time(self):
        current_date_time = self.get_current_time()
        self.analog_clock.time = current_date_time
        self.digital_clock.time = current_date_time
        self.analog_clock.repaint()
        self.digital_clock.show_time()

    def update_animation(self):
        self.analog_clock.update_stars()
        self.digital_clock.update_stars()
        self.analog_clock.repaint()
        self.digital_clock.repaint()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        menu_bar.addMenu("").addAction(QAction("", self)) # This is a dummy menu
        menu_bar.setCornerWidget(spacer)

        self.timezone_action = QAction(self.i18n_manager.get_translation("timezone", default="&Timezone"), self)
        self.timezone_action.triggered.connect(self._show_timezone_dialog)
        menu_bar.addAction(self.timezone_action)

        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help", default="&Help"))
        self.about_action = QAction(self.i18n_manager.get_translation("about", default="&About"), self)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(self.i18n_manager.get_translation("license", default="&License"), self)
        self.license_action.triggered.connect(self._show_license_dialog)
        self.help_menu.addAction(self.license_action)

    def _show_license_dialog(self):
        try:
            with open(resource_path("LICENSE"), "r", encoding="utf-8") as f:
                license_text = f.read()

            dialog = QDialog(self)
            dialog.setWindowTitle("License")
            dialog.resize(600, 600)

            layout = QVBoxLayout(dialog)
            scroll_area = QScrollArea(dialog)
            scroll_area.setWidgetResizable(True)
            
            label = QLabel(license_text, dialog)
            label.setWordWrap(True)
            
            scroll_area.setWidget(label)
            layout.addWidget(scroll_area)
            dialog.setLayout(layout)
            
            dialog.exec()

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "LICENSE file not found.")

    def _show_about_dialog(self):
        about_text = """
        <b>Simple Clock</b>
        <p>Version 1.0</p>
        <p>A beautiful but simple clock application.</p>
        <p><b>Author:</b> Oliver Ernster</p>
        <p><b>Modules Used:</b></p>
        <ul>
            <li>PySide6</li>
            <li>ntplib</li>
        </ul>
        """
        QMessageBox.about(self, "About Simple Clock", about_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None and event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def _get_locale_for_timezone(self, tz_id):
        """Get the most appropriate locale for a given timezone."""
        return self.tz_locale_map.get(tz_id, "en_US") # Default to en_US for unknown
    
    def _show_timezone_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Timezone")
        dialog.setMinimumSize(300, 400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        search_box = QLineEdit(dialog)
        search_box.setPlaceholderText("Search for a timezone...")
        layout.addWidget(search_box)

        list_widget = QListWidget(dialog)
        all_timezones = sorted(pytz.common_timezones)
        
        # Generate the list of timezones with localized names each time the dialog is opened
        timezone_items = []
        now = datetime.now()
        original_locale = self.i18n_manager.current_locale
        for tz in all_timezones:
            locale = self._get_locale_for_timezone(tz)
            self.i18n_manager.timezone_translator.locale = locale
            display_name = self.i18n_manager.timezone_translator.get_display_name(tz, now)
            timezone_items.append((f"{display_name} ({tz})", tz))
        self.i18n_manager.timezone_translator.locale = original_locale
        
        for display_text, _ in timezone_items:
            list_widget.addItem(display_text)
            
        layout.addWidget(list_widget)

        def filter_timezones(text):
            list_widget.clear()
            search_text = text.lower()
            if not text:
                for display_text, _ in timezone_items:
                    list_widget.addItem(display_text)
            else:
                for display_text, tz_id in timezone_items:
                    if search_text in display_text.lower() or search_text in tz_id.lower():
                        list_widget.addItem(display_text)

        search_box.textChanged.connect(filter_timezones)

        def on_item_selected(item):
            # Find the original tz_id from the selected item's text
            selected_text = item.text()
            for display_text, tz_id in timezone_items:
                if selected_text == display_text:
                    self._change_timezone(tz_id)
                    break
            dialog.accept()

        list_widget.itemClicked.connect(on_item_selected)

        dialog.exec()


    def _change_timezone(self, tz):
        self.time_zone = QTimeZone(tz.encode('utf-8'))
        # Auto-detect and set locale based on timezone if a mapping exists
        if tz in self.tz_locale_map:
            locale = self.tz_locale_map.get(tz)
            if locale:
                self.i18n_manager.set_locale(locale)
        
        self.update_time()
        self.update_menu_text()

    def update_menu_text(self):
        self.timezone_action.setText(self.i18n_manager.get_translation("timezone", default="&Timezone"))
        self.help_menu.setTitle(self.i18n_manager.get_translation("help", default="&Help"))
        self.about_action.setText(self.i18n_manager.get_translation("about", default="&About"))
        self.license_action.setText(self.i18n_manager.get_translation("license", default="&License"))

if __name__ == "__main__":
    # This Windows-specific call is essential for the taskbar icon to work correctly.
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    window = ClockWindow()
    window.show()
    sys.exit(app.exec())
