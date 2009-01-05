#! /usr/bin/env python
#
# Description
# ===========
#
# This script fetch all geotagged photos from your Flickr account to a
# local directory and writes `exiv2(1)` script for them. You will need
# to have Python 2.5 with Python FlickrAPI installed and `exiv2(1)` to
# run the program.
#
# Usage
# =====
#
# To run the script, type in your console:
#
#     ./ffg.py --photos-directory=~/flickr-photos/ --exiv-script=~/flickr-photos/exif.sh
#
# This will fetch your photos to `~/flicr-photos/` and write necessary
# `exiv2(1)` commands to `exif.sh` in that directory. Make sure the
# directory you specify exists and you have a permission to write in
# it.
#
# By default, the script stores photos in current directory and writes
# commands to `exiv2.sh` file in it.
#
# At the beginning of the process, your browser will pop up with
# Flickr authorization request. You'll have to grant read permissions
# for this script to operate properly.
#
# Then run exiv2.sh with your shell:
#
#     sh ~/flickr-photos/exiv2.sh
#
# This will write GPS EXIF tags to photos.
#
# Problems
# ========
#
# The `--from-date YYYY-MM-DD` command line option is meant to allow
# you fetch only photos taken after that date, but it does not work
# now.
#
# Flickr API keys
# ===============
#
# Please don't use my keys in your applications.
# 
# Author and licensing
# ====================
#
# Copyright (C) 2008 Dmitry Dzhus <dima@sphinx.net.ru>
#
# This code is subject to the Python licence, as can be read on
# http://www.python.org/download/releases/2.5.2/license/

import sys
import getopt
import os
from os import W_OK, X_OK
from urllib import urlretrieve
from string import capitalize

from flickrapi import FlickrAPI

API_KEY="bad7960ebd9a9742de19b51b84f70d4a"
API_SECRET="0755f96015e27777"

def printUsage():
    print 'Usage: ./ffg.py [--from-date YYYY-MM-DD] [--photos-directory=DIR] [--exiv-script=FILE]'

def makeOptions():
    """Read command line options and return options.
    
    Returns directory in which to store photos, name of file to write exiv2(1)
    commands in and minimal photo taken date.
    """
    # defaults
    write_directory = os.getcwd()
    exiv2_script_file = os.path.join(write_directory, 'exiv2.sh')
    # Jesus loves me
    from_date = "0000-00-00"

    # Parse command line options
    try:
        options, arguments = getopt.getopt(sys.argv[1:], [], ['exiv-script=', 
                                                              'from-date=', 
                                                              'write-directory='])
    except getopt.GetoptError, err:
        print str(err)
        printUsage()
        sys.exit(2)

    for o, a in options:
        if o == '--from-date':
            from_date = a
        elif o == '--write-directory':
            if os.access(a, X_OK|W_OK):
                write_directory = a
            else:
                print "%s: bad directory" % a
                printUsage()
                sys.exit(1)
        elif o == '--exiv-script':
            if os.access(a, W_OK) or os.access(os.path.dirname(a), X_OK|W_OK):
                exiv2_script_file = a
        else:
            assert False

    return write_directory, exiv2_script_file, from_date

def main(write_directory, exiv2_script_file, from_date):
    """Fetch all geotagged photos and write exiv2 script for them.

    Retrieve all geotagged photos taken since from_date to
    `write_directory` and write a set of exiv2(1) commands storing
    geotags in EXIF to `exiv2_script_file`.

    `from_date` is a string YYYY-MM-DD, `write_directory` and
    `exiv2_script_file` are valid directory and file names,
    respectively.
    """
    def getPhotoData(photo):
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
    
    def makeExivCommand(key, value, photo_path):
        return 'exiv2 -M"set %s %s" %s' % (key, value, photo_path)
    
    def writeLocationCommands(photo_path, location):
        """
        Given a photo file path and its location information, make exiv2
        commands to set Exif.GPSInfo tags in file.
        """

        def writeLocationCommand(key, value):
            exiv2_script.write(makeExivCommand(key, value, photo_path) + '\n')

        # Flickr stores lat/long up to 6 digits after decimal point
        denominator = 10 ** 6

        print 'Writing exiv2 commands...'
        
        for key, key_ref in zip(['latitude', 'longitude'], [('N', 'S'), ('E', 'W')]):
            # write Latitude/Longitude values
            value = float(location.attrib[key])
            exif_key = 'Exif.GPSInfo.GPS%s' % capitalize(key)
            exif_value = '%d/%d 0/1 0/1' % (int(value * denominator), denominator)
            writeLocationCommand(exif_key, exif_value)

            # write LatitudeRef/LongitudeRef values
            exif_ref_value = value > 0 and key_ref[0] or key_ref[1]
            writeLocationCommand(exif_key + 'Ref', exif_ref_value)
    
    def processPhoto(photo):
        """
        Retrieve photo to `write_directory`, write exiv2 commands to
        scriptfile.
        """
        title, url, location = getPhotoData(photo)
        
        print 'Retrieving photo %s...' % title
        filename, headers = urlretrieve(url, os.path.join(write_directory, \
                                                          os.path.basename(url)))
        writeLocationCommands(os.path.abspath(filename), location)

    exiv2_script = open(exiv2_script_file, 'w')
    
    # Start flickring
    flickr = FlickrAPI(API_KEY, API_SECRET, format='etree')

    # Authorize
    (token, frob) = flickr.get_token_part_one(perms='read')
    if not token: raw_input('Press ENTER after you authorized this program')
    flickr.get_token_part_two((token, frob))

    print 'Retrieving list of geotagged photos taken since %s...' % from_date
    photos = flickr.photos_getWithGeoData(min_date_taken=from_date).getiterator('photo')

    for photo in photos:
        processPhoto(photo)

if __name__ == "__main__":
    main(*makeOptions())
