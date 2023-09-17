# via/vehicle_info.py
# Part of timetable_kit
#
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.

"""
This module includes VIA *data* which can't be found automatically in VIA GTFS.

This includes the list of which stations are major,
which trains carry checked baggage,
which trains have sleeper cars, etc.
"""
from timetable_kit.generic_agency import AgencyVehicleInfo

# Pointy brackets make a set.
sleeper_trains = {
    "1",  # Canadian
    "2",  # Canadian
    "3",  # Truncated Canadian Vancouver - Edmonton
    "4",  # Truncated Canadian
    "14",  # Ocean
    "15",  # Ocean
}

# Trains with checked baggage cars.
# Email dated Jan 26, 2023 at 7:05 AM:
"""
Good morning,

Thank you for contacting Via Rail Canada.

No trains in the Corridor have checked baggage service at this time.

Only Long Haul trains (Toronto to Vancouver, Halifax to Montreal, 
Winnipeg to Churchill, Montreal to Jonquiere/Senneterre, Jasper to 
Prince Rupert and Sudbury to White River) have checked baggage service 
and only at manned stations on these routes.

If you have any further questions, please do not hesitate to contact us.

Sincerely,

Nathalie
Customer Service
Via Rail Canada
"""

other_checked_baggage_day_trains = {
    "600",  # Jonquiere
    "601",
    "602",
    "603",  # Senneterre
    "604",
    "606",
    "185",  # Sudbury - White River
    "186",
    "690",  # Winnipeg - Churchill
    "691",
    "692",
    "693",
    "5",  # Jasper - Prince Rupert
    "6",
}

# Assemble these trains as a set.
checked_baggage_trains = sleeper_trains | other_checked_baggage_day_trains


class VIARailVehicleInfo(AgencyVehicleInfo):
    # Eventually, in a few hundred years when VIA HFR actually opens,
    # is_high_speed_train could be implemented. One can hope.

    # VIA has two non-VIA services in their data, but they *don't have tsns*.
    # This must be addressed by patching the feed. FIXME.

    def is_sleeper_train(self, train_number):
        """Does this train have sleeper cars?"""
        return train_number in sleeper_trains

    def train_has_checked_baggage(self, trip_short_name: str) -> bool:
        """
        Given a trip_short_name (train number), return "True" if it has checked baggage and "False" if not.

        This is based on crowdsourced data since Amtrak doesn't have a machine-readable way to get it.
        """
        return trip_short_name in checked_baggage_trains


# TESTING
if __name__ == "__main__":
    vehicle_info = VIARailVehicleInfo()
    print(vehicle_info.train_has_checked_baggage("1"))
    print(vehicle_info.train_has_checked_baggage("5"))
