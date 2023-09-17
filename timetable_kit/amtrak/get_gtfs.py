#! /usr/bin/env python3
# amtrak/get_gtfs.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
Retrieve Amtrak's static GTFS data from the canonical location.
"""

if __name__ == "__main__":
    from timetable_kit.amtrak import Amtrak

    gtfs_handler = Amtrak.gtfs_handler()
    gtfs_handler.save_gtfs(gtfs_handler.download_gtfs())
    print("Amtrak GTFS saved at " + str(Amtrak.gtfs_zip_local_path))
    gtfs_handler.unzip_gtfs()
