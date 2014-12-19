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


class Twittercider(object):

    def __init__(self):
        self.session = Session()
        self.session.mount('https://', Foauth(args.email, args.password))

        self._get_or_create_parent_dir()

    def _prepare_post_multipart_related(self, url, files):
        request = Request('post', url, files=files)
        request = self.session.prepare_request(request)

        # This is a bit ugly (ideally requests would expose a way to set the
        # boundary explictly), but it is the simplest way that doesn't require any
        # external libraries.
        request.headers['Content-Type'] = request.headers['Content-Type'].replace('form-data', 'related')

        return request

    def _prepare_upload(self, title, file_):
        '''Prepares a Request to upload the file <file_>, giving it the title
        <title>.

        '''
        # Google Drive expects multipart/related, and for the fields to be in a
        # particular order. First, the metadata, then the file.
        #
        # It expects the metadata as application/json, and the file as base64 (with
        # Content-Transfer-Encoding: base64).

        metadata = {
            'title': title,
            'parents': (self.parent_dir,)
        }

        files = OrderedDict()
        files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')
        files['file'] = ('file', b64encode(file_.read()), 'image/png', {'Content-Transfer-Encoding': 'base64'})

        request = self._prepare_post_multipart_related('https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart', files)

        return request

    def _get_or_create_parent_dir(self):
        query = 'title = "Twittercide" and mimeType = "application/vnd.google-apps.folder"'

        response = self.session.get('https://www.googleapis.com/drive/v2/files', params={
            'q': query,
        })

        log.debug('Parent dir search response {}'.format(response.text))

        response_data = response.json()
        results = response_data['items']

        try:
            self.parent_dir = results[0]
        except IndexError:
            metadata = {
                'title': 'Twittercide',
                'mimeType': 'application/vnd.google-apps.folder',
            }

            files = OrderedDict()
            files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')

            request = self._prepare_post_multipart_related('https://www.googleapis.com/upload/drive/v2/files', files)
            response = self.session.send(request)

            log.debug('Parent dir create response {}'.format(response.text))

            response_data = response.json()
            self.parent_dir = response_data


if __name__ == '__main__':
    api = Twittercider()

    with open('/Users/beau/Pictures/1418760457552.png', mode='rb') as file_:
        request = api._prepare_upload('lel.png', file_)

    response = api.session.send(request)

    log.debug('Request headers {}'.format(response.request.headers))
    log.debug('Request body {}'.format(response.request.body))
    response.raise_for_status()

    log.debug('Response body {}'.format(response.text))
