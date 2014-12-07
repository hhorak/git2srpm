#!/usr/bin/env python
import os
import jinja2
from io import StringIO
import urllib.parse
import json
import subprocess

WORKING_DIR='./working'
OUTPUT_DIR='./srpms'
TEMPLATES_DIR='./templates'

def run_sh(cmd, args):
    """
    Runs command in default shell with specified arguments.
    Results are returned as (exit_code, stdout, stderr)
    """
    pass

def get_path(environ, path):
    return os.path.join(environ.get('DOCUMENT_ROOT', ''), path)

def get_template(environ, filename, tvalues):

    env = jinja2.environment.Environment()
    env.loader = jinja2.FileSystemLoader(get_path(environ, TEMPLATES_DIR))
    template = env.get_template(filename)
    return template.render(tvalues)

def report_error(environ, errors):
    tvalues = {'errors': errors}
    return get_template(environ, 'error.html', tvalues)

def report_info(environ, messages):
    tvalues = {'messages': messages}
    return get_template(environ, 'info.html', tvalues)


def gen_srpm(environ):
    data = urllib.parse.parse_qs(environ['QUERY_STRING'])
    try:
        args = [os.path.join(get_path(environ, '.'), 'git2srpm.sh'),
                '--result-filename', '--git', data['giturl'][0],
                '--wd', get_path(environ, WORKING_DIR),
                '--od', get_path(environ, OUTPUT_DIR)]
    except KeyError:
        status = '404 Not found'
        return report_error(environ, ['Missing argument "giturl".'])

    if 'githash' in data:
        args.extend(data['githash'])
    out_json = subprocess.check_output(args).decode('utf-8')
    response_body = 'raw output: ' + out_json
    try:
        output = json.loads(out_json)
        response_body += output['srpm']
    except (KeyError, ValueError):
        return response_body + 'error parsing json output of git2srpm.sh'

    final_url = environ['wsgi.url_scheme'] + '://' + environ['HTTP_HOST'] + '/srpm/' + output['srpm']
    tvalues = {'link': final_url}
    return get_template(environ, 'import_done.html', tvalues)


def application(environ, start_response):

    ctype = 'text/html'
    status = '200 OK'

    if environ['PATH_INFO'] == '/health':
        response_body = "1"
    elif environ['PATH_INFO'] == '/env':
        response_body = ['%s: %s' % (key, value)
                    for key, value in sorted(environ.items())]
        response_body = '\n'.join(response_body)
    elif environ['PATH_INFO'][0:6] == '/srpm/':
        srpm = environ['PATH_INFO'][6:]
        srpm_file = os.path.join(get_path(environ, OUTPUT_DIR), srpm)
        try:
            with open(srpm_file, 'rb') as f:
                response_body = f.read()
            ctype = 'application/octet-stream'
        except (OSError, IOError) as e:
            status = '404 Not found'
            response_body = report_error(environ, ['Given source RPM "{}" has not been found.'.format(srpm) ])

    elif environ['PATH_INFO'] == '/gen-srpm':
        response_body = gen_srpm(environ)
    else:
        ctype = 'text/html'
        tvalues = {}
        response_body = get_template(environ, 'homepage.html', tvalues)

    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    #
    start_response(status, response_headers)
    if ctype[0:4] == 'text':
        return [response_body.encode('utf-8') ]
    else:
        return [response_body ]

#
# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()
