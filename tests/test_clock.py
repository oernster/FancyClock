import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimeZone, QDateTime
from datetime import date
from main import ClockWindow
from ntp_client import NTPClient
from analog_clock import AnalogClock
from digital_clock import DigitalClock

@pytest.fixture(scope="session")
def app_instance():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_ntp_client_get_time():
    """Test that the NTPClient can successfully fetch time."""
    client = NTPClient()
    ntp_time = client.get_time()
    from datetime import datetime
    assert ntp_time is not None, "Failed to get time from NTP server"
    assert isinstance(ntp_time, datetime), "Time should be a datetime object"

def test_time_synchronization(app_instance):
    """Test that the clock's time is synchronized with NTP time."""
    window = ClockWindow()
    initial_time = window.get_current_time()
    window.synchronize_time()
    synchronized_time = window.get_current_time()
    
    # After synchronization, the time should be different from the initial time
    assert initial_time != synchronized_time, "Time should be synchronized"

def test_change_timezone(app_instance):
    """Test changing the timezone and locale."""
    window = ClockWindow()
    
    # Change to a known timezone
    new_timezone = "America/New_York"
    window._change_timezone(new_timezone)
    
    # Verify that the timezone has been updated
    assert window.time_zone == QTimeZone(new_timezone.encode('utf-8')), "Timezone was not updated correctly"
    
    # Check if the locale was also updated based on the tz_locale_map
    expected_locale = window.tz_locale_map.get(new_timezone)
    assert window.i18n_manager.current_locale == expected_locale, "Locale was not updated correctly"

def test_day_date_translation(app_instance):
    """Test that the day and date are translated correctly."""
    window = ClockWindow()
    
    # Change to German
    window.i18n_manager.set_locale("de_DE")
    
    # Test day translation
    # Monday is at index 0 in the weekday_keys list
    monday_key = "calendar.days.monday"
    translated_day = window.i18n_manager.get_translation(monday_key)
    assert translated_day == "Montag", f"Expected 'Montag', but got '{translated_day}'"
    
    # Test date formatting
    test_date = date(2023, 10, 26)
    formatted_date = window.i18n_manager.format_date_for_locale(test_date)
    expected_date = "26/10/2023"
    assert formatted_date == expected_date, f"Expected '{expected_date}', but got '{formatted_date}'"

def test_analog_clock_starfield(app_instance):
    """Test the starfield animation for the analog clock."""
    clock = AnalogClock()
    assert len(clock.stars) > 0, "Stars should be initialized"
    
    # Get the initial position of the first star
    initial_angle = clock.stars[0].angle
    
    # Update the stars' positions
    clock.update_stars()
    
    # Get the new position of the first star
    new_angle = clock.stars[0].angle
    
    # The angle should have changed after the update
    assert initial_angle != new_angle, "Star positions should be updated"

def test_digital_clock_starfield(app_instance):
    """Test the starfield animation for the digital clock."""
    clock = DigitalClock()
    clock.resize(200, 40)
    # The digital clock stars are created on resizeEvent, which is not called directly.
    # We will manually populate the stars for the test.
    clock.stars = [clock._create_star() for _ in range(100)]
    assert len(clock.stars) > 0, "Stars should be initialized"
    
    # Get the initial position of the first star
    initial_angle = clock.stars[0].angle
    
    # Update the stars' positions
    clock.update_stars()
    
    # Get the new position of the first star
    new_angle = clock.stars[0].angle
    
    # The angle should have changed after the update
    assert initial_angle != new_angle, "Star positions should be updated"
