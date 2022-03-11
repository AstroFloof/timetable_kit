#! /usr/bin/env python3
# wiki_station_cleanup.py
# Part of timetable_kit
# Copyright 2021, 2022 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.

"""
Clean up the wiki-stations.csv file generated by get_wiki_stations.py.

This is not being used but is preserved in case it might come in handy later.
It is therefore full of hardcoded filenames, and probably subject to bitrot.
It is better to get station names from Amtrak's JSON data.
"""

import pandas as pd
import gtfs_kit as gk
#regular expressions
import re

# Cities with multiple stations in the same city, requiring disambiguation
two_station_cities = [ "Buffalo", # There are *three* stations: Depew, unmarked, bus stop
                       "Charleston", # unmarked & bus stop
                       "Hemet", # Two bus stops
                       "Kingston", # Amtrak Station & two misnamed bus stops
                       "Milwaukee", # Two airport, one downtown
                       "Monterey", # FOUR bus stops
                       "Palm Springs" # station, downtown bus, airport bus
                       "Redding", # Station, bus
                       "Santa Fe", # Station, bus... both are bus stops
                       "Stockton", # Amazingly, Amtrak doesn't distinguish!!!
                       "Springfield", # IL v. MA -- same name !!!!
                       "San Pedro", # bus stop vs. cruise terminal
                      ]
# Most city names are a single word: these are the exceptions
two_word_cities = [ "Ann Arbor",
                    "Arcadia Valley"
                    "Burke Centre",
                    "South Beloit",
                    "Bellows Falls",
                    "Bingen-White Salmon",
                    "Battle Creek",
                    "Buffalo Depew", # Note - should have a dash, doesn't
                   ]

# These are the suffixes encountered in Amtrak's data
suffixes = [ "Alvarado Transportation Center", # At ABQ
             "Amtrak Station",
             "Amtrak",
             "Amtrak Bus Stop",
             "Penn Station",
             "Station", # at Buffalo Depew, which should have a dash, and Arcadia Valley
             "Union Station", # Chicago, Little Rock, Meridian
             "Union Terminal", # Cincinnati
             "Vernon J. Ehlers Station", # Grand Rapids
             "Gateway Center", # Joliet
             "Central Station", # Montreal
             "Union Passenger Terminal", # New Orleans
             "Ny Moynihan Train Hall At Penn Station", # New York
             "SporTran Intermodal Terminal", # Shreveport
            ]

# Special cases --
special_cases = [
                  "Buffalo Depew Amtrak Station", # needs hyphen
                  "Bwi Thurgood Marshall Airport Station", # capitalized wrong
                  "DEB", # decommissioned bus station in Denver -- irrelevant
                  "Newark Liberty International Airport", # Too long
                  "Santa Clara Great America", # needs hypen
                  "Kingston Amtrak Bust Stop East", # sic. used for KGE AND KGW, too
                  "General Mitchell Intl. Airport Amtrak Station", # Milwaukee!
                  "Milwaukee Airport Amtrak Bus Stop",
                  "San Diego Old Town Transportation Center",
                  "Sanford Amtrak Auto Train Station", # What about Lorton?
                  "Stateline Amtrak Bus Stop", # Tahoe, Nevada bus
                  "San Pedro Catalina Terminal", # Cruise ship terminal in San Pedro
                 ]


# Testsuite for this
if __name__ == "__main__":
    from pathlib import Path
    path_in = Path('./gtfs-amtrak.zip')
    feed = gk.read_feed(path_in, dist_units='mi')

    # Consider pulling direct from webpage
    # But in the long run we want to put from Amtrak DB
    wiki_stations_csv = Path('./wikipedia/wiki-stations.csv')
    wiki_stations = pd.read_csv(wiki_stations_csv, index_col=False)

    stops_in_feed = feed.stops["stop_id"]
    stops_in_wiki = wiki_stations["stop_id"]
    long_stops_not_in_wiki = stops_in_feed.mask(stops_in_feed.isin(stops_in_wiki.array))
    stops_not_in_wiki = long_stops_not_in_wiki.dropna()
    print("Stops in feed but not in Wikipedia list:")
    print(stops_not_in_wiki)


if False:
    path_out_name = './wikipedia/wiki-stations-revised.csv'
    path_out = Path(path_out_name)

    new_stops = cleanup_station_names(feed.stops)
    feed.stops = new_stops

    feed.write(path_out)
    print ("Revised feed now in " + path_out_name)