#! /usr/bin/env python3
# check_ghost_trains.py
# Part of timetable_kit
# Copyright 2021, 2022 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
# Initial version started by Christopher Juckins

import sys

"""
This essentially compares two lists:

a) The list of trains in a .csv spec file that we think are running
b) The list of trains from an external .txt file that are actually running

It will print differences so manual tweaks to the .csv can be done.
"""

# TO DO:
#
# Add in NN's csv-checker code provided via email
"""
Now, leaning on the code I've already written, this code should import a list 
of train numbers from a single .csv file...
...I should probably refactor this a little and move some of these subroutines
into different files, but anyway this should work.  Assuming you have your 
venv set up with timetable_kit and pandas.

from timetable_kit.timetable import (
    load_ttspec_csv,
    train_specs_list_from_tt_spec,
    flatten_train_specs_list,
)
from timetable_kit.tsn import (
    train_spec_to_tsn,
)

# Get the CSV as a Pandas DataFrame
tt_spec_csv = load_ttspec_csv(filename)
# Extract the train specs from the top row as a list
train_specs_list = train_specs_list_from_tt_spec(tt_spec)
# Flatten 48/448 notations, eliminate "noheader" suffixes
flattened_train_specs_set = flatten_train_specs_list(train_specs_list)
# Eliminate "monday", "tuesday" etc suffixes
flattened_tsn_list = [
    train_spec_to_tsn(train_spec) for train_spec in flattened_train_specs_set
]

This leaves only the process of reading the arguments list to get the filenames,
the process of importing the list of trains_running (which is probably 
newline-separated? space-separated?), and the process of looping over 
multiple CSV files and merging the lists from different CSV files.
"""
#
# Add in method to download the actual running files from the following URL:
# https://juckins.net/timetable_kit/trains_running/

if __name__ == "__main__":
    
    # Quick framework test
    csv_input = ["20", "66", "174"]
    trains_running = ["20", "80", "174"]
    
    print('csv_input:')
    print(csv_input)
    
    print('')
    
    print('trains_running:')
    print(trains_running)
    
    print('')
    
    missing_from_csv_input = list(set(trains_running).difference(csv_input))
    print('missing_from_csv_input:')
    print(missing_from_csv_input)
    
    print('')
    
    csv_ghost_train = list(set(csv_input).difference(trains_running))
    print('csv_ghost_train:')
    print(csv_ghost_train)