#!/usr/bin/env python

from argparse import ArgumentParser
from base64 import b64encode
from collections import OrderedDict
import json
import logging

from requests import Request, Session
from requests_foauth import Foauth


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


parser = ArgumentParser(description='Delete your last 3200 tweets and backup tweeted photos to Google Drive')
parser.add_argument('email', help='foauth.org email')
parser.add_argument('password', help='foauth.org password')
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()


session = Session()
session.mount('https://', Foauth(args.email, args.password))


def _prepare_upload(session, title, file_):
    '''Prepares a Request to upload the file <file_>, giving it the title
    <title>, using an existing session <session>.

    '''
    # Google Drive expects multipart/related, and for the fields to be in a
    # particular order. First, the metadata, then the file.
    #
    # It expects the metadata as application/json, and the file as base64 (with
    # Content-Transfer-Encoding: base64).

    metadata = {
        'title': title,
    }

    files = OrderedDict()
    files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')
    files['file'] = ('file', b64encode(file_.read()), 'image/png', {'Content-Transfer-Encoding': 'base64'})

    request = Request('post', 'https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart', files=files)
    request = session.prepare_request(request)

    # This is a bit ugly (ideally requests would expose a way to set the
    # boundary explictly), but it is the simplest way that doesn't require any
    # external libraries.
    request.headers['Content-Type'] = request.headers['Content-Type'].replace('form-data', 'related')

    return request


if __name__ == '__main__':
    # TODO: Search first

    with open('/Users/beau/Pictures/1418760457552.png', mode='rb') as file_:
        request = _prepare_upload(session, 'lel.png', file_)

    response = session.send(request)

    log.debug('Request headers {}'.format(response.request.headers))
    log.debug('Request body {}'.format(response.request.body))
    response.raise_for_status()

    log.debug('Response body {}'.format(response.text))
