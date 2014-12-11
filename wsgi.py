#!/usr/bin/env python
import os
import jinja2
import io
import urllib.parse
import json
import subprocess
import glob

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
    tvalues['space_used'] = subprocess.check_output("du --max-depth 0 -h {0} | cut -f1".format('.'), shell=True).decode('utf-8')
    env = jinja2.environment.Environment()
    env.loader = jinja2.FileSystemLoader(get_path(environ, TEMPLATES_DIR))
    template = env.get_template(filename)
    return template.render(tvalues).encode('utf-8')

def report_error(environ, errors):
    tvalues = {'errors': errors}
    return get_template(environ, 'error.html', tvalues)

def report_info(environ, messages):
    tvalues = {'messages': messages}
    return get_template(environ, 'info.html', tvalues)


def get_srpm_url(environ, name):
    return environ['wsgi.url_scheme'] + '://' + environ['HTTP_HOST'] + '/srpm/' + name


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

    final_url = get_srpm_url(environ, output['srpm'])
    tvalues = {'link': final_url}
    return get_template(environ, 'import_done.html', tvalues)


def find(environ):
    data = urllib.parse.parse_qs(environ['QUERY_STRING'])
    try:
        query = data['q'][0]
    except KeyError:
        status = '404 Not found'
        return report_error(environ, ['Missing argument which to search.'])
    try:
        srpms = [ os.path.basename(f) for f in glob.glob("{0}/*{1}*src.rpm".format(get_path(environ, OUTPUT_DIR), query.replace(' ', '*'))) ]
    except FileNotFoundError:
        srpms = []
    tvalues = {'srpms':srpms, 'headline': 'Search for {0}'.format(query)}
    return get_template(environ, 'list.html', tvalues)


def application(environ, start_response):

    ctype = 'text/plain'
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

    elif environ['PATH_INFO'][0:5] == '/list':
        ctype = 'text/html'
        try:
            srpms = [ get_srpm_url(environ, str(file)) for file in os.listdir(get_path(environ, OUTPUT_DIR))]
        except FileNotFoundError:
            srpms = []
        tvalues = {'srpms':srpms, 'headline': 'List of all srpms'}
        response_body = get_template(environ, 'list.html', tvalues)

    elif environ['PATH_INFO'][0:7] == '/search':
        ctype = 'text/html'
        response_body = find(environ)

    elif environ['PATH_INFO'] == '/gen-srpm':
        ctype = 'text/html'
        response_body = gen_srpm(environ)

    elif environ['PATH_INFO'] == '/':
        ctype = 'text/html'
        tvalues = {}
        response_body = get_template(environ, 'homepage.html', tvalues)

    else:
        ctype = 'text/plain'
        fullpath = os.path.join(get_path(environ, '.'), environ['PATH_INFO'][1:])
        try:
            fmode = 'rb'
            if environ['PATH_INFO'][-4:] == '.css':
                ctype = 'text/css'
            elif environ['PATH_INFO'][-3:] == '.js':
                ctype = 'text/javascript'
            else:
                ctype = 'application/x-opentype'
            with open(fullpath, fmode) as f:
                response_body = f.read()
        except (OSError, IOError) as e:
            status = '404 Not found'
            response_body = report_error(environ, ['Given path "{}" has not been found.'.format(fullpath) ])

    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    #
    start_response(status, response_headers)
    return [response_body ]

#
# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()
