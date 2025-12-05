import pytz
from babel.dates import get_timezone_name
from datetime import datetime

class TimezoneTranslator:
    def __init__(self, locale):
        self.locale = locale

    def get_display_name(self, tz_id, dt=None):
        """
        Get the localized display name for a given timezone ID.
        :param tz_id: The timezone ID (e.g., 'America/New_York').
        :param dt: A datetime object to get the current name (DST or standard).
                   If None, the standard name is returned.
        :return: The localized timezone name.
        """
        # For an accurate name (standard or DST), we need an aware datetime object.
        aware_dt = datetime.now(pytz.timezone(tz_id))
        return get_timezone_name(aware_dt, locale=self.locale, width='long')

# Example usage:
if __name__ == '__main__':
    # Define the target time zone ID and a few locales
    tz_id = 'America/New_York'
    locales = ['en_US', 'fr_FR', 'de_DE', 'es_ES']

    for locale in locales:
        translator = TimezoneTranslator(locale)
        
        # Get the standard name
        standard_name = translator.get_display_name(tz_id)
        
        # Get the current name (which may be DST)
        now = datetime.now()
        current_name = translator.get_display_name(tz_id, now)
        
        print(f"--- Locale: {locale} ---")
        print(f"Timezone ID: {tz_id}")
        print(f"Standard Name: {standard_name}")
        print(f"Current Name: {current_name}")
        print("-" * 20)

    # Example for a different timezone
    tz_id_paris = 'Europe/Paris'
    translator_fr = TimezoneTranslator('fr_FR')
    now_paris = datetime.now()
    current_name_paris = translator_fr.get_display_name(tz_id_paris, now_paris)
    print(f"--- Locale: fr_FR ---")
    print(f"Timezone ID: {tz_id_paris}")
    print(f"Current Name: {current_name_paris}")
    print("-" * 20)