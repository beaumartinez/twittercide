#!/usr/bin/env python

from argparse import ArgumentParser
from base64 import b64encode
from cStringIO import StringIO
from collections import OrderedDict
from os.path import basename
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

    def _get_or_create_parent_dir(self):
        metadata = {
            'title': 'Twittercide',
            'mimeType': 'application/vnd.google-apps.folder',
        }
        parent_dir = self._get_or_upload(metadata)

        self.parent_dir_id = parent_dir['id']

    def _prepare_upload(self, url, files):
        request = Request('post', url, files=files)
        request = self.session.prepare_request(request)

        # This is a bit ugly (ideally requests would expose a way to set the
        # boundary explictly), but it is the simplest way that doesn't require any
        # external libraries.
        request.headers['Content-Type'] = request.headers['Content-Type'].replace('form-data', 'related')

        return request

    def _prepare_query(self, metadata):
        query = list()

        for key, value in metadata.iteritems():
            if key == 'parents':
                for subvalue in value:
                    # When in the metadata, each parent item is object. To search, we just need the ID
                    subvalue = subvalue['id']

                    query.append('"{}" in {}'.format(subvalue, key))
            else:
                query.append('{} = "{}"'.format(key, value))

        query = ' and '.join(query)

        return query

    def _get_or_upload(self, metadata, file_=None):
        query = self._prepare_query(metadata)
        log.debug('_get_or_upload: query {}'.format(query))

        response = self.session.get('https://www.googleapis.com/drive/v2/files', params={
            'q': query,
        })
        log.debug('_get_or_upload: get response {}'.format(response.text))

        response_data = response.json()
        results = response_data['items']

        try:
            result = results[0]
        except IndexError:
            log.debug('_get_or_upload: get not found. Uploading.'.format(response.text))

            # Google Drive expects multipart/related, and for the fields to be in a
            # particular order. First, the metadata, then the file.
            #
            # It expects the metadata as application/json, and the file as base64 (with
            # Content-Transfer-Encoding: base64).

            url = 'https://www.googleapis.com/upload/drive/v2/files'

            files = OrderedDict()
            files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')

            if file_:
                url = 'https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart'
                files['file'] = ('file', b64encode(file_.read()), 'image/png', {'Content-Transfer-Encoding': 'base64'})

            request = self._prepare_upload(url, files)
            response = self.session.send(request)

            log.debug('_get_or_upload: upload response {}'.format(response.text))

            response_data = response.json()
            result = response_data

        return result

    def _backup_twitter_media(self, url):
        title = basename(url)
        metadata = {
            'title': title,
            'parents': ({
                'kind': 'drive#file',
                'id': self.parent_dir_id,
            },)
        }

        file_response = self.session.get(url)
        file_ = file_response.content
        file_ = StringIO(file_)

        self._get_or_upload(metadata, file_)

    def _get_tweets(self):
        response = self.session.get('https://api.twitter.com/1.1/statuses/user_timeline.json', params={
            'count': 200,
            'include_rts': False,
        })

        results = response.json()

        for tweet in results:
            if 'extended_entities' in tweet:
                if 'media' in tweet['extended_entities']:
                    for media in tweet['extended_entities']['media']:
                        self._backup_twitter_media(media['media_url'])


if __name__ == '__main__':
    api = Twittercider()
    api._get_tweets()
