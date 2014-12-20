#!/usr/bin/env python

from argparse import ArgumentParser
from base64 import b64encode
from cStringIO import StringIO
from collections import OrderedDict
from hashlib import md5
from os.path import basename
import json
import logging

from arrow import utcnow
from requests import Request, Session
from requests_foauth import Foauth
import dateutil.parser


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


parser = ArgumentParser(
    description='Delete your last 3200 tweets and backup tweeted photos to Google Drive',
    epilog='''Twittercide uses foauth.org <http://foauth.org/> to authenticate with Twitter and Google's APIs.
    
    In order to use it, you'll need to sign up with foauth.org, and authorize both those services <https://foauth.org/services/>.
    
    For Twitter, you need to check the option to "read and send tweets". For Google, you need "access your documents".
    '''
)
parser.add_argument('email', help='foauth.org email')
parser.add_argument('password', help='foauth.org password')
parser.add_argument('--days_ago', '-d', default=0, help="only delete tweets older than DAYS_AGO days. (A value of 0 will delete all tweets)", type=int)
parser.add_argument('--dry-run', action='store_true', help="don't delete any tweets, but backup tweeted photos")
parser.add_argument('--debug', '-v', action='store_true', help='show debug logging')

args = parser.parse_args()


if args.debug:
    log.setLevel(logging.DEBUG)


class Twittercider(object):

    def __init__(self, args):
        self.days_ago = args.days_ago
        self.dry_run = args.dry_run

        self.session = Session()
        self.session.mount('https://', Foauth(args.email, args.password))

        self.now = utcnow()

    def _get_or_create_parent_dir(self):
        metadata = {
            'title': 'Twittercide',
            'mimeType': 'application/vnd.google-apps.folder',
        }
        parent_dir = self._get_or_upload(metadata)

        self.parent_dir_id = parent_dir['id']

    def _prepare_upload(self, method, url, params, files):
        request = Request(method, url, params=params, files=files)
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
        log.debug('Query {}'.format(query))

        response = self.session.get('https://www.googleapis.com/drive/v2/files', params={
            'q': query,
        })

        log.debug('Query response {}'.format(response.text))

        response.raise_for_status()

        response_data = response.json()
        results = response_data['items']

        insert = False
        update = False

        try:
            result = results[0]
        except IndexError:
            insert = True

            log.debug('File not found in Google Drive. Uploading')
        else:
            if len(results) > 1:
                raise ValueError('More than 1 matching file {}'.format(len(results)))

            if file_:
                checksum = md5(file_.getvalue())
                checksum = checksum.hexdigest()

                if result['md5Checksum'] != checksum:
                    update = True

                    log.debug('MD5 checksums differ. File: {}, Google Drive: {}. Re-uploading'.format(checksum, result['md5Checksum']))

        if insert or update:
            # Google Drive expects multipart/related, and for the fields to be in a
            # particular order. First, the metadata, then the file.
            #
            # It expects the metadata as application/json, and the file as base64 (with
            # Content-Transfer-Encoding: base64).

            if insert:
                method = 'post'
                url = 'https://www.googleapis.com/upload/drive/v2/files'
            else:
                assert update

                method = 'put'
                url = 'https://www.googleapis.com/upload/drive/v2/files/{}'.format(result['id'])

            files = OrderedDict()
            files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')

            if file_:
                params = {
                    'uploadType': 'multipart',
                }
                
                # TODO: Determine mimetype
                files['file'] = ('file', b64encode(file_.read()), 'image/png', {'Content-Transfer-Encoding': 'base64'})
            else:
                params = {}

            request = self._prepare_upload(method, url, params, files)
            response = self.session.send(request)

            log.debug('Upload response {}'.format(response.text))

            response.raise_for_status()

            response_data = response.json()
            result = response_data

            if update:
                if result['md5Checksum'] != checksum:
                    raise ValueError('MD5 checksums still differ after re-upload. File: {}, Google Drive: {}'.format(checksum, result['md5Checksum']))

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

        orig_url = url + ':orig'  # Get the original, highest-quality version of the media

        file_response = self.session.get(orig_url)
        file_response.raise_for_status()

        file_ = file_response.content
        file_ = StringIO(file_)

        self._get_or_upload(metadata, file_)

        log.info('Backed up {}'.format(url))

    def _backup_tweets(self):
        finished = False

        max_id = None
        while not finished:
            response = self.session.get('https://api.twitter.com/1.1/statuses/user_timeline.json', params={
                'count': 200,
                'include_rts': False,
                'max_id': max_id,
            })
            response.raise_for_status()

            log.debug('Loaded next 200 tweets')

            results = response.json()

            for tweet in results:
                created_at = tweet['created_at']
                created_at = dateutil.parser.parse(created_at)

                delta = self.now - created_at

                if delta.days >= self.days_ago:
                    if 'extended_entities' in tweet:
                        if 'media' in tweet['extended_entities']:
                            for media in tweet['extended_entities']['media']:
                                self._backup_twitter_media(media['media_url'])

                    if not self.dry_run:
                        log.info('Pretending to delete {}'.format(tweet['id_str']))

                        # self.post('https://api.twitter.com/1.1/statuses/destroy/{}.json'.format(tweet['id_str'])
                else:
                    log.debug('{} not old enough ({} days old, must be at least {}). Skipping'.format(tweet['id_str'], delta.days, self.days_ago))

            old_max_id = max_id
            max_id = tweet['id_str']

            finished = max_id == old_max_id

    def twittercide(self):
        self._get_or_create_parent_dir()
        self._backup_tweets()


if __name__ == '__main__':
    t = Twittercider(args)
    t.twittercide()
