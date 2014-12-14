git2srpm
========

Simple tool to generate SRPM from git repository and using lookaside
cache from Fedora.

The project runs on public free instance of Open Shift at:
http://git2srpm-honzahorak.rhcloud.com


REST Api
--------

REST api uses the same URLs as web UI, just add 'v1' after the hostname.

For submitting a new SRPM generation, use:

   curl "http://git2srpm-honzahorak.rhcloud.com//v1/gen-srpm?giturl=http%3A%2F%2Fgithub.com%2Fuser%2Fproject.git"

For listing all SRPMs, use:

   curl "http://git2srpm-honzahorak.rhcloud.com//v1/list

And so on.
