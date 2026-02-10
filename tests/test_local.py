import sys
import os
import logging

# Add custom_components/jdm_holiday to path to import holiday_engine directly
# This avoids triggering __init__.py which depends on homeassistant
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../custom_components/jdm_holiday")
    )
)

from holiday_engine import Holiday


# Configure logging
logging.basicConfig(level=logging.DEBUG)


def test_holiday_engine():
    print("Initializing Holiday Engine...")
    engine = Holiday()

    print("\n--- Testing Today ---")
    today_status = engine.is_holiday_today()
    print(f"Is today holiday? {today_status}")

    print("\n--- Testing Tomorrow ---")
    tomorrow_status = engine.is_holiday_tomorrow()
    print(f"Is tomorrow holiday? {tomorrow_status}")

    print("\n--- Testing Nearest Holiday Info ---")
    # Expanding range to ensure we find something if possible
    info = engine.nearest_holiday_info(min_days=0, max_days=90)
    print(f"Nearest Holiday Info:\n{info}")


if __name__ == "__main__":
    test_holiday_engine()
