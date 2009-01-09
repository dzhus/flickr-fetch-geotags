#! /usr/bin/env python
"""
Description
===========

This script fetches all geotagged photos from your Flickr account to
a local directory and writes `exiv2(1)` script for them. You will
need to have Python 2.5 with Python FlickrAPI installed and
`exiv2(1)` to run the program.

Usage
=====

To run the script, type in your console:

    ./ffg.py --photos-directory=~/flickr-photos/ --exiv-script=~/flickr-photos/exif.sh

This will fetch your photos to `~/flicr-photos/` and write necessary
`exiv2(1)` commands to `exif.sh` in that directory. Make sure the
directory you specify exists and you have a permission to write in
it.

By default, the script stores photos in current directory and writes
commands to `exiv2.sh` file in it.

At the beginning of the process, your browser will pop up with
Flickr authorization request. You'll have to grant read permissions
for this script to operate properly.

Then run exiv2.sh with your shell:

    sh ~/flickr-photos/exiv2.sh

This will write GPS EXIF tags to photos.

Problems
========

The `--from-date YYYY-MM-DD` command line option is meant to allow
you fetch only photos taken after that date, but it does not work
now.

Flickr API keys
===============

Please don't use my keys in your applications.

Author and licensing
====================

Copyright (C) 2008 Dmitry Dzhus <dima@sphinx.net.ru>

This code is subject to the Python licence, as can be read on
http://www.python.org/download/releases/2.5.2/license/
"""

import sys
import getopt
import os
from os import W_OK, X_OK
from urllib import urlretrieve
from string import capitalize

from flickrapi import FlickrAPI

API_KEY="bad7960ebd9a9742de19b51b84f70d4a"
API_SECRET="0755f96015e27777"

def print_usage():
    print 'Usage: ./ffg.py [--from-date YYYY-MM-DD] [--photos-directory=DIR] [--exiv-script=FILE]'

def make_options():
    """
    Read command line options and return `write_directory`,
    `exiv2_file_path`, `from_date` settings.
    """
    # Default settings
    write_directory = os.getcwd()
    exiv2_file_path = os.path.join(write_directory, 'exiv2.sh')
    # Jesus loves me
    from_date = "0000-00-00"

    # Parse command line options
    try:
        options, arguments = getopt.getopt(sys.argv[1:], [],
                                           ['exiv-script=', 
                                            'from-date=', 
                                            'write-directory='])
    except getopt.GetoptError, err:
        print str(err)
        print_usage()
        sys.exit(2)

    # Parse options, checking write permissions where necessary
    for o, a in options:
        if o == '--from-date':
            from_date = a
        elif o == '--write-directory':
            if os.access(a, X_OK|W_OK):
                write_directory = a
            else:
                print "%s: bad directory" % a
                print_usage()
                sys.exit(1)
        elif o == '--exiv-script':
            if os.access(a, W_OK) or os.access(os.path.dirname(a), X_OK|W_OK):
                exiv2_file_path = a
        else:
            assert False

    return write_directory, exiv2_file_path, from_date

def make_exiv_command(key, value, photo_path):
    return 'exiv2 -M"set %s %s" %s' % (key, value, photo_path)
    
def write_location_commands(photo_path, location, exiv2_file):
    """
    Given a photo file path and its location information, write to
    `exiv2_file` a bunch of exiv2 commands which set Exif.GPSInfo tags
    in file.

    `exiv2_file` is a file object.
    """
    def write_command(key, value):
        exiv2_file.write(make_exiv_command(key, value, photo_path) + '\n')

    # Flickr stores lat/long with up to 6 digits after decimal point,
    # but in EXIV rationals are used
    denominator = 10 ** 6

    print 'Writing exiv2 commands...'
        
    for key, key_ref in zip(['latitude', 'longitude'], [('N', 'S'), ('E', 'W')]):
        # write Latitude/Longitude values
        value = float(location.attrib[key])
        exif_key = 'Exif.GPSInfo.GPS%s' % capitalize(key)
        exif_value = '%d/%d 0/1 0/1' % (int(value * denominator), denominator)
        write_command(exif_key, exif_value)

        # write LatitudeRef/LongitudeRef values
        exif_ref_value = value > 0 and key_ref[0] or key_ref[1]
        write_command(exif_key + 'Ref', exif_ref_value)

def get_photo_data(flickr, photo):
    """Return title, url, location of photo."""
    pid = photo.attrib['id']

    # no pattern expressions in etree, thus asserting last size to
    # be the biggest
    lsize = flickr.photos_getSizes(photo_id=pid).getiterator('size')[-1]
    assert lsize.attrib['label'] == 'Large'

    loc = flickr.photos_geo_getLocation(photo_id=pid).getiterator('location')[0]
    title = photo.attrib['title']
    url = lsize.attrib['source']

    return title, url, loc
    
def run(write_directory, exiv2_file_path, from_date):
    """Fetch all geotagged photos and write exiv2 script for them.

    Retrieve all geotagged photos taken since `from_date` to
    `write_directory` and write a set of exiv2(1) commands storing
    geotags in EXIF to `exiv2_file_path`.

    `from_date` is a string YYYY-MM-DD, `write_directory` and
    `exiv2_file_path` are valid directory and file names,
    respectively.
    """
    exiv2_file = open(exiv2_file_path, 'w')
    
    # Start flickring
    flickr = FlickrAPI(API_KEY, API_SECRET, format='etree')

    # Authorize
    (token, frob) = flickr.get_token_part_one(perms='read')
    if not token: raw_input('Press ENTER after you authorized this program')
    flickr.get_token_part_two((token, frob))

    print 'Retrieving list of geotagged photos taken since %s...' % from_date
    photos = flickr.photos_getWithGeoData(min_date_taken=from_date).getiterator('photo')

    # Retrieve photo to `write_directory`, write exiv2 commands to
    # scriptfile.
    for photo in photos:
        title, url, location = get_photo_data(flickr, photo)
        
        print 'Retrieving photo %s...' % title
        filename, headers = urlretrieve(url, os.path.join(write_directory, \
                                                          os.path.basename(url)))
        write_location_commands(os.path.abspath(filename), location, exiv2_file)

if __name__ == "__main__":
    run(*make_options())
