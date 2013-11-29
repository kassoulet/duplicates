#!/usr/bin/python3
# -*- coding: utf-8 -*-
#

"""
Duplicates - Fast File-Level Deduplicator
© 2013 Gautier Portet - <kassoulet gmail com>

Duplicates use a fast algorithm, to early reject false positives.

A file is compared to others files, by using, in order:
 - size
 - hash of first KB
 - hash of content

This program uses temporary files and external "sort" to minimise memory
utilization.
"""

__version__ = '0.2'
__author__ = 'Gautier Portet'

print('duplicates %s' % __version__)

import os
import sys
import time
from hashlib import sha1 as Hasher
from os import walk
from datetime import datetime
from tempfile import mkstemp
from optparse import OptionParser

SEPARATOR = '\0'

verbose = False
quiet = False
minimal_size = 0
skip_same_inode = True
deduplicate = False


def expand_size_suffix(size):
    """
    Convert a string containing a size to a number.
    Recognize size suffixes eg. 62 15k 47M 92G.
    """
    intsize = int(''.join(s for s in size if s.isdigit()))
    suffix = size[-1].lower()
    try:
        multiplier = 1024 ** (dict(k=1, m=2, g=3)[suffix])
    except KeyError:
        multiplier = 1
    return intsize * multiplier


def parse_arguments():
    usage = "usage: %prog [options] folders"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--minimal-size", dest="minsize", default='1024',
                      help="Minimal size. Default to 1KB. (You can use size "
                           "suffixes eg. 62 15k 47M 92G).")
    parser.add_option("-f", "--fix",
                      dest="deduplicate",
                      action="store_true",
                      help="Create hardlinks between duplicated files.")
    parser.add_option("-q", "--quiet",
                      dest="quiet",
                      action="store_true",
                      help="Do not display progress info.")
    parser.add_option("-v", "--verbose",
                      dest="verbose",
                      action="store_true",
                      help="More info.")
    global folders
    global quiet
    global verbose
    global deduplicate
    global minimal_size
    (options, folders) = parser.parse_args()
    if len(folders) < 1:
        parser.print_help()
        return
    minimal_size = expand_size_suffix(options.minsize)
    quiet = options.quiet
    verbose = options.verbose
    deduplicate = options.deduplicate


parse_arguments()
if deduplicate:
    skip_same_inode = True

##############################################################################

# counters
selected_files = 0
fasthashed = 0
fullhashed = 0
size_files = 0
size_read = 0
already_linked_files = 0
already_linked_bytes = 0

def log(*args):
    """
    Display message if we are in verbose mode.
    """
    if verbose:
        print(' '.join(args))


def humanize_size(size):
    """
    Return the file size as a nice, readable string.
    """
    for limit, suffix in ((1024 ** 3, 'G'), (1024 ** 2, 'M'), (1024, 'K')):
        hsize = float(size) / limit
        if hsize > 0.5:
            return '%.1f%s' % (hsize, suffix)
    return size


def get_file_hash(filename, limit_size=None):
    """
    Return the md5 hash of given file as an hexadecimal string.
    limit_size can be used to read only the first n bytes of file.
    """
    BUFFER_SIZE = 64 * 1024
    buffer_size = BUFFER_SIZE
    try:
        f = open(filename, "rb")
    except IOError:
        return None

    hasher = Hasher()

    global size_read
    if limit_size:
        # get the md5 of beginning of file
        chunk = f.read(limit_size)
        size_read += len(chunk)
        hasher.update(chunk)
    else:
        # get the md5 of whole file
        chunk = True
        while chunk:
            chunk = f.read(buffer_size)
            size_read += len(chunk)
            hasher.update(chunk)
    f.close()
    return hasher.hexdigest()

blacklist_folders = ('.svn', 'Trash', '.git')
def getfiles(*args):
    global selected_files
    global size_files
    device = None
    visited_inodes = set()
    for folder in folders:
        for root, dirs, files_ in walk(folder):
            for name in files_:
                filename = os.path.join(root, name)
                filesize = size(filename)
                if filesize is None:
                    log('cannot access file:', filename)
                    continue
                stat = os.stat(filename)
                if device is None:
                    device = stat.st_dev
                else:
                    if device != stat.st_dev:
                        log('not the same device:', filename)
                        continue
                if stat.st_ino in visited_inodes:
                    global already_linked_bytes
                    global already_linked_files
                    already_linked_files += 1
                    already_linked_bytes += filesize
                    if skip_same_inode:
                        log('inode already read:', filename)
                        continue
                visited_inodes.add(stat.st_ino)
                if filesize > minimal_size:
                    selected_files += 1
                    size_files += filesize
                    yield '%s%s%s' % (filesize, SEPARATOR, filename)
            for blacklisted in blacklist_folders:
                # skip blacklisted folders.
                if blacklisted in dirs:
                    log('skipping:', os.path.join(root, blacklisted))
                    dirs.remove(blacklisted)


def size(filename):
    try:
        filesize = os.path.getsize(filename)
    except OSError: # invalids files, links, etc...
        filesize = None
    return filesize


def fasthash(filename):
    global fasthashed
    fasthashed += 1
    return get_file_hash(filename, 1024)


def fullhash(filename):
    global fullhashed
    fullhashed += 1
    if size(filename) <= 1024:
        return 'skipped'
    return get_file_hash(filename)


########################################################

tmppath = '/tmp/duplicates-%s' % Hasher(str(datetime.now()).encode()).hexdigest()[:6]

walked_files = 0
last_progress = 0

def update_progress(message, force_progress=False):
    if quiet:
        return
    global last_progress
    now = time.time()
    if now > last_progress + 0.2 or force_progress:
        d = globals()
        d['indeterminate'] = ['-', '\\', '|', '/'][int(now * 5) % 4]
        sys.stdout.write(message % d)
        sys.stdout.flush()
        last_progress = now

def process_matches(func, output_type='fullhash'):
    with open('%s.%s.sorted' % (tmppath, output_type)) as files:
        old = None
        group = []
        group_number = 1
        sid = None
        for line in files:
            line = line.strip()
            sid, filename = line.split(SEPARATOR)
            if old and sid != old:
                func(group, group_number, sid)
                group = []
                group_number += 1
            group.append(filename)
            old = sid
        if group:
            func(group, group_number, sid)

def dedup(fin, fout, func):
    global walked_files
    walked_files = 0

    def output(same, sid):
        if len(same) > 1:
            d = {}
            for s in same:
                d.setdefault(func(s), []).append(s)
            for k, v in d.items():
                if len(v) > 1:
                    sout.write(''.join('%s-%s%s%s\n' % (sid, k, SEPARATOR, s) for s in v))

    def output_match(group, group_number, sid):
        output(group, sid)
        global walked_files
        walked_files += 1
        update_progress('Applying %s... %%(indeterminate)s (%%(walked_files)s matches)     \r' % fout)
        
    with open('%s.%s' % (tmppath, fout), 'w') as sout:
        process_matches(output_match, fin)
    update_progress('Applied %s to %%(walked_files)s matches.            \n' % fout, force_progress=True)
    os.system('sort -n %s.%s > %s.%s.sorted' % (tmppath, fout, tmppath, fout))
    os.unlink('%s.%s.sorted' % (tmppath, fin))
    os.unlink('%s.%s' % (tmppath, fout))

wasted_bytes = 0
def print_match(group, group_number, sid):
    global wasted_bytes
    wasted_bytes += size(group[0]) * (len(group) - 1)
    print('group #%d (%s)' % (group_number, humanize_size(size(group[0]) * len(group))))
    print('\n'.join('  %s %s' % (humanize_size(size(s)), s) for s in group))

saved_bytes = 0
def dedup_match(group, group_number, sid):
    for f in group[1:]:
        log('%s -> %s' % (group[0], f))
        tmp = f + '~D~'
        try:
            os.rename(f, tmp)
            os.link(group[0], f)
            os.unlink(tmp)
            global saved_bytes
            saved_bytes += size(f)
        except OSError:
            print('Cannot create link: "%s"' % f)
            os.rename(tmp, f)

# read files
with open('%s.sizes' % tmppath, 'w') as tmpfiles:
    for f in getfiles():
        tmpfiles.write(f + '\n')
        walked_files += 1
        update_progress('Scanning... %(indeterminate)s (%(walked_files)s files)\r')
    update_progress('Found %(walked_files)s files.           \n', force_progress=True)
os.system('sort %s.sizes > %s.sizes.sorted' % (tmppath, tmppath))
os.unlink('%s.sizes' % tmppath)

# do the magic
dedup('sizes', 'fasthash', fasthash)
dedup('fasthash', 'fullhash', fullhash)

if deduplicate:
    process_matches(dedup_match)
    if saved_bytes:
        print('Deduplication saved %sB.' % humanize_size(saved_bytes))
    else:
        print('Nothing duplicated.')
else:
    if not quiet:
        process_matches(print_match)
        print('Duplicated size: %sB.' % humanize_size(wasted_bytes))
if not quiet:
    speedup = 1
    if size_read:
        speedup = size_files / size_read
    size_read = humanize_size(size_read)
    size_files = humanize_size(size_files)
    if already_linked_files:
        print('Already deduplicated: %d files, %sB.' % (already_linked_files, humanize_size(already_linked_bytes)))
    print(
    'total files: %(selected_files)s, files read: %(fullhashed)s, total size: %(size_files)s, size read: %('
    'size_read)s, speedup: %(speedup).1fx.' % locals())

os.unlink('%s.fullhash.sorted' % tmppath)


