#!/usr/bin/env python
# -*- mode: Python; indent-tabs-mode: nil; -*-

import json
import argparse
import urllib.request
import urllib.parse
import subprocess

CLIENT_VERSION='0.1'
GIT2SRPM_URL='http://git2srpm-honzahorak.rhcloud.com'


def main():
    parser = argparse.ArgumentParser(description='Client for git2srpm.',
                                 epilog="This is an open-source project by Honza Horak.")
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(CLIENT_VERSION))

    parser.add_argument('--copr', metavar='name', required=True,
                   help='Name of the copr project')
    parser.add_argument('--giturl', metavar='url', required=True,
                   help='Public git repository to build from')
    parser.add_argument('--githash', metavar='hash',
                   default='master',
                   help='Git hash to build from')
    args = parser.parse_args()

    data = {}
    data['giturl'] = args.giturl
    data['githash'] = args.githash
    url_values = urllib.parse.urlencode(data)
    response = urllib.request.urlopen('{0}/v1/gen-srpm?{1}'.format(GIT2SRPM_URL, url_values))
    html = response.read().decode('utf-8')
    
    try:
        output = json.loads(html)
        if output['data']['result'] != 1:
            raise Exception('Result code was not 1, it was {0}.'.format(output['data']['result']))
        cmd = '/usr/bin/copr-cli build {0} {1}'.format(args.copr, output['data']['srpm'])
        print('SRPM is generated, running:')
        print(cmd)
        print(subprocess.check_output(['/usr/bin/copr-cli', 'build', args.copr, output['data']['srpm']]).decode('utf-8'))
    except (KeyError, ValueError) as e:
        print('Something wrong happened: error({0}): {1}'.format(e.errno, e.strerror))

if __name__ == '__main__':
    main()

# Local variables:
# c-indentation-style: bsd
# c-basic-offset: 4
# indent-tabs-mode: nil
# End:
# vim: expandtab shiftwidth=4
