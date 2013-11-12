#!/usr/bin/python3
# -*- coding: utf-8 -*-
#

"""
Duplicates
© 2013 Gautier Portet - <kassoulet gmail com>
"""
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function

NAME = 'Duplicates'
VERSION = '0.1'
CONFIG_FILE = 'duplicates.conf'

print('%s (%s)' % (NAME, VERSION))

import os
import sys
import time
from optparse import OptionParser

import finder
from finder import scan, current_file

quiet = False
verbose = False


def expand_size_suffix(size):
    """
    Convert a string containing a size to an int.
    Recognize size suffixes eg. 62 15k 47M 92G.
    """
    intsize = int(''.join(s for s in size if s.isdigit()))
    suffix = size[-1].lower()
    try:
        multiplier = 1024 ** (dict(k=1,m=2,g=3)[suffix])
    except KeyError:
        multiplier = 1
    return intsize * multiplier 


def humanize_size(size):
    """
    Return the file size as a nice, readable string.
    """
    for limit, suffix in ((1024**3, 'G'), (1024**2, 'M'), (1024, 'K')):
        hsize = float(size) / limit
        if hsize > 0.5:
            return '%.1f%s' % (hsize, suffix)
    return size


next_progress = 0
added_files = 0
scanned_size = 0
def added_file(filename):
    """Called when a file is added in matcher."""
    global next_progress
    global added_files
    global scanned_size
    added_files += 1
    scanned_size += os.path.getsize(filename)
    if not quiet:
        t = (time.time() * 10)
        if t < next_progress:
            return
        c = ['-','\\','|','/'][int(t)%4]
        sys.stdout.write('Scanning... %s (%d files)\r' % (c, added_files))
        sys.stdout.flush()
        next_progress = t + 1


def scanned_file(scanned, to_scan, match=None):
    """Called when a file is hashed by matcher."""
    global next_progress
    if not quiet:
        t = (time.time() * 10)
        if t < next_progress:
            return
        sys.stdout.write('Scanning... %d/%d            \r' % (scanned, to_scan))
        sys.stdout.flush()
        next_progress = t + 1


def stats_matches(matches):
    """."""
    useless_size = 0
    useless_files = 0
    for i, group in enumerate(matches):
        useless_size += sum(x[1] for x in group[1:])
        useless_files += len(group)-1
    return useless_files, useless_size


def print_matches(matches):
    """Print the final result list."""

    for i, group in enumerate(matches):
        print('Group #%d (%s)' % (i, humanize_size(sum(x[1] for x in group))))
        for match in group:
            filename, size, md5 = match
            size = humanize_size(size)
            #print '%7s %s %s' % (size, md5[:6], filename)
            print('%7s %s' % (size, filename))
            
    useless_files, useless_size = stats_matches(matches)
    print("Total: %d duplicate files, %s." % (useless_files, humanize_size(useless_size)))


import shutil



def deduplicate(matches):
    origin = (x[0][0] for x in matches)
    links = (x[1:] for x in matches)
    linked_size = 0
    linked_files = 0
    if verbose: print('linking:')
    for o,l in zip(origin, links):
        so = os.stat(o)
        if verbose: print('**', o, so.st_ino, so.st_nlink)
        for x in l:
            d = x[0]
            tmp = d+'~'
            sd = os.stat(d)
            if verbose:  print('->', d, sd.st_ino, sd.st_nlink)
            if so.st_dev != sd.st_dev:
                # we can't link files if they aren't in the same filesystem.
                if verbose:
                    print('    not on the same filesystem')
                continue
            if (sd.st_mode != so.st_mode or 
                sd.st_uid != so.st_uid or
                sd.st_gid != so.st_gid):
                if verbose:
                    print('    not the same mode/owner!')
                continue
            try:
                #os.rename(d, tmp)
                try:
                    #os.link(o, d)

                    # en mode dedup, pas besoin de scanner si les modes sont differents

                    # inode contains the ownership and times.
                    #so we can't save them at all.
                    #creating softlinks is far more dangerous
                    #maybe we can just verify that modes are the same before linking. Else this is an obvious security breach.
                       
                    #shutil.copystat(tmp, d) #XXX
                    #stat = os.stat(d) #XXX
                    #os.chown(d, stat.st_uid, stat.st_gid)
                    #os.remove(tmp)
                    linked_size += x[1]
                    linked_files += 1
                except OSError:
                    print('cannot link:', o , '->', d)
                    #os.rename(tmp, d)
            except OSError:
                print('cannot rename:', d , '->', tmp)
        
    print("Deduplicated %d files, %sB." % (linked_files, humanize_size(linked_size)))


def main(*args):
    # parse arguments
    usage = "usage: %prog [options] folders"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--minimal-size", dest="minsize", default='1M',
                      help="Minimal size. Default 1M. (You can use size suffixes"
                      " eg. 62 15k 47M 92G).")
    parser.add_option("-L", "--follow-links",
                      dest="follow_links",
                      action="store_true",
                      help="Follow symbolic links.")
    parser.add_option("", "--deduplicate",
                      dest="deduplicate", 
                      action="store_true",
                      help="Create hardlinks between duplicate files.")
    parser.add_option("-q", "--quiet",
                      dest="quiet", 
                      action="store_true",
                      help="Do not display progress info.")
    parser.add_option("-v", "--verbose",
                      dest="verbose", 
                      action="store_true",
                      help="More info.")

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return
        
    folders = args
    minimal_size = expand_size_suffix(options.minsize)
    follow_links = options.follow_links
    global quiet
    quiet = options.quiet
    global verbose
    verbose = options.verbose
    deduplicate_ = options.deduplicate

    # scan folder
    start = time.time()
    matches = scan(folders, minimal_size, follow_links,
        add_file_callback=added_file,
        add_match_callback=scanned_file,
    )
    duration = time.time()-start
    if not quiet:
        print()
        print('Found %d matche(s) in %.3fs. Scanned %s, %s/s. %.1fx speedup' % (
            len(matches), 
            duration, 
            humanize_size(scanned_size), 
            humanize_size(scanned_size/duration),
            scanned_size/finder.really_hashed,
            ))

    if deduplicate_:
        deduplicate(matches)
    else:
        print_matches(matches)

main(NAME, VERSION)


