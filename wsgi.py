#!/usr/bin/env python
import os
from jinja2 import Template
from io import StringIO
import urllib.parse
import json
import subprocess

def run_sh(cmd, args):
    """
    Runs command in default shell with specified arguments.
    Results are returned as (exit_code, stdout, stderr)
    """

def gen_srpm(query):
    response_body = "parsing data..."

    #POST:
    #length = int(environ.get('CONTENT_LENGTH', '0'))
    #body = environ['wsgi.input'].read(length).decode('utf-8')
    #data = urllib.parse.parse_qs(body)
    data = urllib.parse.parse_qs(query)
    try:
        args = ['echo', '===', './git2srpm.sh', '--git', data['giturl'][0]]
    except KeyError:
        response_body = 'Missing argument "giturl".'
        return response_body

    if 'githash' in data:
        args.extend(data['githash'])
    out_json = subprocess.check_output(args).decode('utf-8')
    response_body += 'raw output: ' + out_json
    try:
        output = json.loads(out_json)
        response_body += output['srpm']
    except (KeyError, ValueError):
        response_body += 'error parsing json output of git2srpm.sh'
    return response_body

def application(environ, start_response):

    ctype = 'text/plain'
    if environ['PATH_INFO'] == '/health':
        response_body = "1"
    elif environ['PATH_INFO'] == '/env':
        response_body = ['%s: %s' % (key, value)
                    for key, value in sorted(environ.items())]
        response_body = '\n'.join(response_body)
    elif environ['PATH_INFO'][0:6] == '/srpm/':
        srpm = environ['PATH_INFO'][6:]
        response_body = "Returning srpm {}".format(srpm)
    elif environ['PATH_INFO'] == '/gen-srpm':
        response_body = gen_srpm(environ['QUERY_STRING'])
    else:
        ctype = 'text/html'
        tvalues = {}
        tvalues['name'] = 'Doe'
        tfile = 'templates/homepage.html'
        try:
            with open(tfile, 'r') as t:
                template = Template(t.read())
            response_body = template.render(tvalues)
        except (OSError, IOError) as e:
            response_body = 'Could not open template file {}'.format(tformat)

    status = '200 OK'
    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    #
    start_response(status, response_headers)
    return [response_body.encode('utf-8') ]

#
# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()
