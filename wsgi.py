#!/usr/bin/env python
# -*- mode: Python; indent-tabs-mode: nil; -*-

import glob
import io
import jinja2
import json
import os
import urllib.parse
import subprocess

WORKING_DIR='./working'
OUTPUT_DIR='../data/srpms'
TEMPLATES_DIR='./templates'

class myapp(object):

    def __init__(self, environ):
        self.environ = environ
        self.ctype = 'text/plain'
        self.status = '200 OK'
        self.response_body = ''
        self.cache = False

    def run_sh(cmd, args):
        """
        Runs command in default shell with specified arguments.
        Results are returned as (exit_code, stdout, stderr)
        """
        pass

    def _get_path(self, path):
        return os.path.join(self.environ.get('DOCUMENT_ROOT', ''), path)

    def _get_du(self, path):
        out = subprocess.check_output("du --max-depth 0 -h {0} | cut -f1".format(path),
                                       shell=True).decode('utf-8')
        if not out:
            out = '0B'

        return out


    def _get_all_pages_values(self, tvalues={}):
        tvalues['space_used_wd'] = self._get_du(self._get_path(WORKING_DIR))
        tvalues['space_used_od'] = self._get_du(self._get_path(OUTPUT_DIR))
        return tvalues

    def _get_template(self, filename, tvalues):
        self.ctype = 'text/html'
        tvalues = self._get_all_pages_values(tvalues)
        env = jinja2.environment.Environment()
        env.loader = jinja2.FileSystemLoader(self._get_path(TEMPLATES_DIR))
        template = env.get_template(filename)
        return template.render(tvalues).encode('utf-8')

    def _report_error(self, errors=['Some unspecified error.']):
        tvalues = {'errors': errors}
        return self._get_template('error.html', tvalues)

    def _report_info(self, messages=['Some unspecified info.']):
        tvalues = {'messages': messages}
        return self._get_template('info.html', tvalues)


    def _get_srpm_url(self, name):
        return self.environ['wsgi.url_scheme'] + '://' + self.environ['HTTP_HOST'] + '/srpm/' + name


    def action_gen_srpm(self):
        data = urllib.parse.parse_qs(self.environ['QUERY_STRING'])
        try:
            args = [os.path.join(self._get_path('.'), 'git2srpm.sh'),
                    '--result-filename', '--git', data['giturl'][0],
                    '--wd', self._get_path(WORKING_DIR),
                    '--od', self._get_path(OUTPUT_DIR)]
        except KeyError:
            status = '404 Not found'
            self.response_body = self._report_error(['Missing argument "giturl".'])
            return

        if 'githash' in data:
            args.extend(['--hash', data['githash'][0]])
        try:
            out_json = subprocess.check_output(args).decode('utf-8')
        except subprocess.CalledProcessError:
            self.response_body = self._report_error(['Could not create SRPM from given git repository.',
                                       'Check the link, content of the repository and if '
                                     + 'sources are available in Fedora\'s lookaside cache.',
                                       'Only if everything looks fine, contact author.'])
            return
        response_body = 'raw output: ' + out_json
        try:
            output = json.loads(out_json)
            response_body += output['srpm']
        except (KeyError, ValueError):
             self.response_body = response_body + 'error parsing json output of git2srpm.sh'

        final_url = self._get_srpm_url(output['srpm'])
        tvalues = {'link': final_url}
        self.response_body = self._get_template('import_done.html', tvalues)


    def action_find(self):
        data = urllib.parse.parse_qs(self.environ['QUERY_STRING'])
        try:
            query = data['q'][0]
        except KeyError:
            self.status = '404 Not found'
            self.response_body = self._report_error(['Missing argument which to search.'])
            return 
        try:
            srpms = [ self._get_srpm_url(os.path.basename(f)) 
                      for f in glob.glob("{0}/*{1}*src.rpm".format(self._get_path(OUTPUT_DIR),
                                                                   query.replace(' ', '*'))) ]
        except FileNotFoundError:
            srpms = []
        tvalues = {'srpms':srpms, 'headline': 'Search for {0}'.format(query)}
        self.response_body = self._get_template('list.html', tvalues)


    def action_health(self):
        self.response_body = "1"


    def action_env(self):
        self.response_body = ['%s: %s' % (key, value)
                             for key, value in sorted(environ.items())]
        self.response_body = '\n'.join(response_body)


    def action_get_srpm(self, srpm):
        srpm_file = os.path.join(self._get_path(OUTPUT_DIR), srpm)
        try:
            with open(srpm_file, 'rb') as f:
                self.response_body = f.read()
            self.ctype = 'application/octet-stream'
        except (OSError, IOError) as e:
            self.status = '404 Not found'
            self.response_body = self.report_error(['Given source RPM "{}" has not been found.'.format(srpm) ])


    def action_list(self):
        try:
            srpms = [ self._get_srpm_url(str(file)) for file in os.listdir(self._get_path(OUTPUT_DIR))]
        except FileNotFoundError:
            srpms = []
        tvalues = {'srpms':srpms, 'headline': 'List of all srpms'}
        self.response_body = self._get_template('list.html', tvalues)


    def action_homepage(self):
        self.response_body = self._get_template('homepage.html', {})


    def action_file(self):
        self.ctype = 'text/plain'
        fullpath = os.path.join(self._get_path('.'), self.environ['PATH_INFO'][1:])
        try:
            fmode = 'rb'
            if self.environ['PATH_INFO'][-4:] == '.css':
                self.ctype = 'text/css'
            elif self.environ['PATH_INFO'][-3:] == '.js':
                self.ctype = 'text/javascript'
            else:
                self.ctype = 'application/x-opentype'
            with open(fullpath, fmode) as f:
                self.response_body = f.read()
            self.cache = True
        except (OSError, IOError) as e:
            self.status = '404 Not found'
            self.response_body = self._report_error(['Given path "{}" has not been found.'.format(fullpath) ])
            return


def application(environ, start_response):

    app = myapp(environ)

    if environ['PATH_INFO'] == '/health':
        app.action_health()

    elif environ['PATH_INFO'] == '/env':
        app.action_env()

    elif environ['PATH_INFO'][0:6] == '/srpm/':
        app.action_get_srpm(environ['PATH_INFO'][6:])

    elif environ['PATH_INFO'][0:5] == '/list':
        app.action_list()

    elif environ['PATH_INFO'][0:7] == '/search':
        app.action_find()

    elif environ['PATH_INFO'] == '/gen-srpm':
        app.action_gen_srpm()

    elif environ['PATH_INFO'] == '/':
        app.action_homepage()

    else:
        app.action_file()

    response_headers = [('Content-Type', app.ctype), ('Content-Length', str(len(app.response_body)))]

    if app.cache:
        response_headers.append(('Cache-Control', 'public, max-age=86400'))

    start_response(app.status, response_headers)
    return [ app.response_body ]

#
# Below for testing only
#
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()

# Local variables:
# c-indentation-style: bsd
# c-basic-offset: 4
# indent-tabs-mode: nil
# End:
# vim: expandtab shiftwidth=4

