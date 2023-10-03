# amtrak/agency.py
# Part of timetable_kit
# Copyright 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.amtrak.agency module

This holds a class for "AgencyAmtrak" intended to be used as a singleton.
"""
from __future__ import annotations

from timetable_kit.generic_agency import Agency

# for patch_feed
import timetable_kit.amtrak.gtfs_patches as gtfs_patches

# for patch_add_wheelchair_boarding
import timetable_kit.amtrak.access as access

# for sleeper trains, which trains have checked baggage, etc
import timetable_kit.amtrak.special_data as special_data

# for whether stations have checked baggage
import timetable_kit.amtrak.baggage as baggage


class AgencyAmtrak(Agency):
    """Amtrak-specific code for interpreting specs and GTFS feeds"""

    _agency_names = ["Amtrak"]
    _agency_published_gtfs_urls = [
        "https://www.transit.land/feeds/f-9-amtrak~amtrakcalifornia~amtrakcharteredvehicle"
    ]

    def __init__(
        self: AgencyAmtrak,
    ) -> None:
        super().__init__()

    def stop_code_to_stop_id(self, stop_code: str) -> str:
        # Identity function for Amtrak
        return stop_code

    def stop_id_to_stop_code(self, stop_id: str) -> str:
        # Identity function for Amtrak
        return stop_id

    def patch_feed(self, feed: FeedEnhanced) -> FeedEnhanced:
        """
        Apply Amtrak-specific patches to a feed.
        Returns the patched feed.
        Does not alter data in the Agency object.
        Do this before init_from_feed.
        """
        # This is defined in its own file in the Amtrak subpackage.
        return gtfs_patches.patch_feed(feed)

    def patch_feed_wheelchair_access_only(self, feed: FeedEnhanced) -> FeedEnhanced:
        """
        Apply only the patches to add wheelchair boarding information for Amtrak;
        return a patched feed.

        Does not alter the data in the agency object.
        Do this before init_from_feed.
        """
        new_feed = feed.copy()
        access.patch_add_wheelchair_boarding(new_feed)  # Alters in place
        return new_feed

    def station_has_checked_baggage(self, station_code: str) -> bool:
        """
        Does this station have checked baggage service?
        """
        return baggage.station_has_checked_baggage(station_code)

    def train_has_checked_baggage(self, tsn: str) -> bool:
        """
        Does this train have checked baggage service?
        """
        return special_data.train_has_checked_baggage(tsn)

    def is_sleeper_train(self, tsn: str) -> bool:
        """
        Does this train have sleeper cars?
        """
        return special_data.is_sleeper_train(tsn)

    def is_high_speed_train(self, tsn: str) -> bool:
        """
        Should this train be marked as high-speed in the timetable?
        """
        return special_data.is_high_speed_train(tsn)

    def is_connecting_service(self, tsn: str) -> bool:
        """
        Should this be marked as a connecting service in the timetable?
        """
        # This is not the ideal implementation.
        # This should be implemented by checking the agency.txt file,
        # and seeing which trains are run by different agencies.
        # However, we have a working implementation based on tsns.
        return special_data.is_connecting_service(tsn)

    def connecting_bus_key_sentence(self, doing_html=True) -> str:
        """
        Sentence to put in the symbol key for connecting bus services
        """
        return "Connecting Bus Service (can be booked through Amtrak)"

    def agency_css_class(self) -> str:
        """
        Name of a CSS class for agency-specific styling
        """
        return "amtrak-special-css"


# Establish the singleton
_singleton = AgencyAmtrak()


def get_singleton():
    """Get singleton for Amtrak"""
    global _singleton
    return _singleton
