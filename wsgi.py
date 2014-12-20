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
        self.api = False
        self.headers = []


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
        if self.api:
            return self._get_json_output(tvalues)
        self.ctype = 'text/html'
        tvalues = self._get_all_pages_values(tvalues)
        env = jinja2.environment.Environment()
        env.loader = jinja2.FileSystemLoader(self._get_path(TEMPLATES_DIR))
        template = env.get_template(filename)
        return template.render(tvalues).encode('utf-8')


    def _report_error(self, errors=['Some unspecified error.']):
        tvalues = {'errors': errors}
        if self.api:
            return self._get_json_output(tvalues)
        return self._get_template('error.html', tvalues)


    def _report_info(self, messages=['Some unspecified info.']):
        tvalues = {'messages': messages}
        if self.api:
            return self._get_json_output(messages)
        return self._get_template('info.html', tvalues)


    def _get_srpm_url(self, name):
        return self.environ['wsgi.url_scheme'] + '://' + self.environ['HTTP_HOST'] + '/srpm/' + name


    def _get_json_output(self, data):
        self.ctype = 'text/plain'
        return json.dumps({'data': data}).encode('utf-8')


    def _action_gen_srpm(self, getfile=False):
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
             self.response_body = self._report_error([response_body + 'error parsing json output of git2srpm.sh'])

        # if we want to return the bits as well, do it and end
        if getfile:
            self.action_get_srpm(output['srpm'])
            self.headers.append(('Content-Disposition', 'attachment; filename="{0}"'.format(output['srpm'])))
            return

        # otherwise return some nice output, depending on if we are
        # asked for JSON or HTML
        final_url = self._get_srpm_url(output['srpm'])
        if self.api:
            self.response_body = self._get_json_output({'result': 1, 'srpm': final_url})
        else:
            self.response_body = self._report_info(['Source RPM generated successfully.', 'Use: <a href="{0}">{0}</a>'.format(final_url)])


    def get_headers(self):
        ret = [('Content-Type', self.ctype), ('Content-Length', str(len(self.response_body)))]
        if self.cache:
            ret.append(('Cache-Control', 'public, max-age=86400'))
        ret.extend(self.headers)
        return ret


    def action_gen_srpm(self):
        self._action_gen_srpm(getfile=False)


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
        if self.api:
            self.response_body = self._get_json_output("1")
        else:
            self.response_body = "1"


    def action_env(self):
        self.response_body = ['%s: %s' % (key, value)
                             for key, value in sorted(environ.items())]
        if self.api:
            self.response_body = self._get_json_output(response_body)
        else:
            self.response_body = '\n'.join(response_body)


    def action_get_srpm(self, srpm):
        srpm_file = os.path.join(self._get_path(OUTPUT_DIR), srpm)
        try:
            with open(srpm_file, 'rb') as f:
                self.response_body = f.read()
            self.ctype = 'application/octet-stream'
        except (OSError, IOError) as e:
            self.status = '404 Not found'
            self.response_body = self._report_error(['Given source RPM "{}" has not been found.'.format(srpm) ])


    def action_gen_and_get(self):
        self._action_gen_srpm(getfile=True)


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


    def handle_request(self):
        if self.environ['PATH_INFO'][0:4] == '/v1/':
            self.api = True
            self.handle_action(self.environ['PATH_INFO'][3:])
        else:
            self.handle_action(self.environ['PATH_INFO'])


    def handle_action(self, path_info):
        if path_info == '/health':
            self.action_health()

        elif path_info == '/env':
            self.action_env()

        elif path_info.startswith('/srpm/'):
            self.action_get_srpm(path_info[6:])

        elif path_info.startswith('/list'):
            self.action_list()

        elif path_info.startswith('/search'):
            self.action_find()

        elif path_info == '/gen-srpm':
            self.action_gen_srpm()

        elif path_info.startswith('/gen-and-get'):
            self.action_gen_and_get()

        elif path_info == '/':
            self.action_homepage()

        else:
            self.action_file()


def application(environ, start_response):

    app = myapp(environ)
    app.handle_request()

    start_response(app.status, app.get_headers())
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

