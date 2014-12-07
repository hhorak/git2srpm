#!/usr/bin/env python
# Simple tool to download package from lookaside cache
#
# Borrowed from pyrpkg, python library for RPM Packagers
#
# Copyright (C) 2011 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# Author(s): Honza Horak <hhorak@redhat.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.
 
import os
import subprocess
import hashlib

DEFAULT_URL = 'http://pkgs.fedoraproject.org/repo/pkgs'

def _hash_file(file, hashtype):
    """Return the hash of a file given a hash type"""

    try:
        sum = hashlib.new(hashtype)
    except ValueError:
        raise rpkgError('Invalid hash type: %s' % hashtype)

    input = open(file, 'rb')
    # Loop through the file reading chunks at a time as to not
    # put the entire file in memory.  That would suck for DVDs
    while True:
        chunk = input.read(8192) # magic number!  Taking suggestions
        if not chunk:
            break # we're done with the file
        sum.update(chunk)
    input.close()
    return sum.hexdigest()


def _verify_file(file, hash, hashtype):
    """Given a file, a hash of that file, and a hashtype, verify.

    Returns True if the file verifies, False otherwise

    """

    # get the hash
    sum = _hash_file(file, hashtype)
    # now do the comparison
    if sum == hash:
        return True
    return False


def download_sources(outdir=None, cache_url=DEFAULT_URL, component=None):
    """Download source files"""

    try:
        archives = open(os.path.join('.', 'sources'),
                        'r').readlines()
    except IOError, e:
        raise Exception('This is not a valid repo: %s' % (e,))
    # Default to putting the files where the module is
    if not outdir:
        outdir = '.'
    # Some guessing of what component name could be if not specified,
    # simply the first spec file without extension
    if not component:
        try:
            component = [ f[:-5] for f in os.listdir('.') if f[-5:] == '.spec' ][0]
        except ValueError:
            raise Exception('Could not guess component name.')
    for archive in archives:
        try:
            # This strip / split is kind a ugly, but checksums shouldn't have
            # two spaces in them.  sources file might need more structure in the
            # future
            csum, file = archive.strip().split('  ', 1)
        except ValueError:
            raise Exception('Malformed sources file.')
        # See if we already have a valid copy downloaded
        outfile = os.path.join(outdir, file)
        if os.path.exists(outfile):
            if _verify_file(outfile, csum, 'md5'):
                continue
        url = '%s/%s/%s/%s/%s' % (cache_url, component,
                                  file.replace(' ', '%20'),
                                  csum, file.replace(' ', '%20'))
        command = ['curl', '-H', 'Pragma:', '-o', outfile, '-R', '-S', '--fail']
        command.append(url)
        print(subprocess.check_output(command).decode('utf-8'))


if __name__ == "__main__":
    download_sources()

