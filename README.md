git2srpm
========

Simple tool to generate SRPM from git repository and using lookaside
cache from Fedora.

The project runs on public free instance of Open Shift at:
http://git2srpm-honzahorak.rhcloud.com

This project is open-source and available under GPLv2+ license.


Main purpose
------------

This service is designed to be used by RPM maintainers that keep sources
to their RPMs somewhere in a public git repository. For tarballs and other
big sources that do not fit to the git repository they use lookaside cache,
while the most tarballs are uploaded to the Fedora's lookaside cache and
thus this service is tight to that one.

Then, maintainers want to build binary RPMs in
[http://copr.fedoraproject.org](copr build system) which however consumes
only URLs to the SRPM.

Well, generating a SRPM locally and uploading it to some public place sucks,
this service should be handy.


Usual workflow
--------------

Go to http://git2srpm-honzahorak.rhcloud.com and enter link to any
public git repository that includes one SPEC file and other SRPM sources
except those that are stored in Fodora's lookaside cache.

This application then generates a SRPM using lookaside cache from Fedora
and gives you a link to the generated SRPM.

The provided link can then be used in
[http://copr.fedoraproject.org](copr build system) project to build your
ad-hoc package or for whatever you want.

Please, be aware that the SRPM is available for some unknown reasonable
time only, so if you want to keep it long tome, you need to copy it
somewhere else.


REST Api
--------

REST api uses the same URLs as web UI, just add 'v1' after the hostname.

For submitting a new SRPM generation, use:

    curl "http://git2srpm-honzahorak.rhcloud.com//v1/gen-srpm?giturl=http%3A%2F%2Fgithub.com%2Fuser%2Fproject.git"

For listing all SRPMs, use:

    curl "http://git2srpm-honzahorak.rhcloud.com//v1/list

And so on.

