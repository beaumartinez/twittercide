#!/usr/bin/env python

from argparse import ArgumentParser
from base64 import b64encode
from cStringIO import StringIO
from collections import OrderedDict
from datetime import datetime
from hashlib import md5
from pprint import pformat
from os.path import basename
from zipfile import ZipFile
import json
import logging
import re

from arrow import utcnow
from requests import Request, Session
from requests.exceptions import HTTPError
from requests_foauth import Foauth
import dateutil.parser


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


parser = ArgumentParser(
    description='Delete your tweets and backup tweeted photos to Google Drive',
    epilog='''Twittercide uses foauth.org <http://foauth.org/> to authenticate with Twitter and Google's APIs.

    In order to use it, you'll need to sign up with foauth.org, and authorize both those services <https://foauth.org/services/>.

    For Twitter, you need to check the option to "read and send tweets". For Google, you need "access your documents".

    We can only delete your last 3200 tweets using the Twitter API, but you can use a Twitter archive zip file with the --nuclear argument to delete all your tweets.

    We check the MD5 checksums of backed-up photos, and we won't delete tweets with photos if we couldn't back them up. You can delete them anyway with the --force-delete argument.
    '''
)
parser.add_argument('email', help='foauth.org email')
parser.add_argument('password', help='foauth.org password')
parser.add_argument('--days_ago', '-d', help="Only delete tweets older than DAYS_AGO days. (A value of 0 will delete all tweets)", type=int)
parser.add_argument('--dry-run', action='store_true', help="Don't delete any tweets, but backup tweeted photos")
parser.add_argument('--nuclear', '-n', help="GO NUCLEAR. Delete using a Twitter archive zip file", type=file)
parser.add_argument('--force-delete', '-f', action='store_true', help="Delete tweets even if the media couldn't be backed up")
parser.add_argument('--debug', '-v', action='store_true', help='Show debug logging')


class Twittercider(object):

    def __init__(self, days_ago=0, dry_run=False, nuke=None, force_delete=False):
        self.days_ago = days_ago
        self.dry_run = dry_run
        self.nuke = nuke
        self.force_delete = force_delete

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
            elif key in ('description', 'modifiedDate'):
                pass
            else:
                query.append('{} = "{}"'.format(key, value))

        query = ' and '.join(query)

        return query

    def _get_or_upload(self, metadata, file_=None, skip_update=False):
        query = self._prepare_query(metadata)
        log.debug('Query {}'.format(query))

        response = self.session.get('https://www.googleapis.com/drive/v2/files', params={
            'q': query,
        })

        log.debug('Query response {}'.format(response.text.encode('utf-8')))

        response.raise_for_status()

        response_data = response.json()
        results = response_data['items']

        if file_:
            checksum = md5(file_.getvalue())
            checksum = checksum.hexdigest()

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
                if result['md5Checksum'] != checksum:
                    update = True

                    log.debug('MD5 checksums differ. File: {}, Google Drive: {}. Re-uploading'.format(checksum, result['md5Checksum']))

        if insert or update:
            if update and skip_update:
                log.debug('Skipping update')

                return result

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

            params = {
                'setModifiedDate': True,
                'newRevision': False,
            }

            if file_:
                params['uploadType'] = 'multipart',

                # TODO: Determine mimetype
                files['file'] = ('file', b64encode(file_.read()), 'image/png', {'Content-Transfer-Encoding': 'base64'})

            request = self._prepare_upload(method, url, params, files)
            response = self.session.send(request)

            log.debug('Upload response {}'.format(response.text.encode('utf-8')))

            response.raise_for_status()

            response_data = response.json()
            result = response_data

        if file_:
            if result['md5Checksum'] != checksum:
                raise ValueError('MD5 checksums differ after upload. File: {}, Google Drive: {}'.format(checksum, result['md5Checksum']))

        return result

    def _backup_twitter_media(self, url, tweet):
        title = basename(url)

        date = dateutil.parser.parse(tweet['created_at'])
        date = date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')  # Explicitly encoding the time. isoformat doesn't work; Google Drive expects microseconds separated by a .

        metadata = {
            'title': title,
            'description': tweet['text'],
            'modifiedDate': date,
            'parents': ({
                'kind': 'drive#file',
                'id': self.parent_dir_id,
            },)
        }

        orig_url = url + ':orig'  # Get the original, highest-quality version of the media

        file_response = self.session.get(orig_url)

        skip_update = False
        failed_to_backup = False

        try:
            file_response.raise_for_status()
        except HTTPError:
            if file_response.status_code == 404:  # We can't get the original media for some reason (already deleted?). Try with large
                log.warning("Couldn't get original media for {}. Trying with large".format(url))

                large_url = url + ':large'

                file_response = self.session.get(large_url)

                try:
                    file_response.raise_for_status()
                except HTTPError:
                    if file_response.status_code == 404:
                        log.warning("Couldn't get large media for {}. Trying with normal".format(url))

                        file_response = self.session.get(url)

                        try:
                            file_response.raise_for_status()
                        except HTTPError:
                            if file_response.status_code == 404:
                                log.warning("Couldn't get normal media for {}".format(url))

                                failed_to_backup = True
                            else:
                                raise
                    else:
                        raise

                skip_update = True  # We don't want to risk overriding the file on Drive in case it's higher-quality
            else:
                raise

        if failed_to_backup:
            log.info("Skipping backing up {}. Couldn't get media. Won't delete either".format(url))
        else:
            file_ = file_response.content
            file_ = StringIO(file_)

            upload = self._get_or_upload(metadata, file_, skip_update=skip_update)

            log.info('Backed up {} to {}'.format(url, upload['alternateLink']))

        return failed_to_backup

    def _backup_media_and_delete(self, tweet, skip_deletion_error=False):
        created_at = tweet['created_at']
        created_at = dateutil.parser.parse(created_at)

        delta = self.now - created_at

        permalink = 'https://twitter.com/{}/status/{}'.format(tweet['user']['screen_name'], tweet['id_str'])

        delete = True

        if delta.days >= self.days_ago:
            if 'retweeted_status' not in tweet:  # Sometimes tweet['retweeted'] lies, this is a better check
                entities_field = 'extended_entities'

                if entities_field not in tweet:  # Try and see if the tweet is from an archive. (They're in an older format, and don't have the extended_entities field)
                    entities_field = 'entities'

                if entities_field in tweet:
                    if 'media' in tweet[entities_field]:
                        if tweet[entities_field]['media']:
                            log.debug('Tweet with media {}'.format(pformat(tweet)))

                            for media in tweet[entities_field]['media']:
                                delete = self._backup_twitter_media(media['media_url'], tweet)  # Only false if we failed to backup media

            if delete or self.force_delete:
                if not self.dry_run:
                    response = self.session.post('https://api.twitter.com/1.1/statuses/destroy/{}.json'.format(tweet['id_str']))
                    response.raise_for_status()

                    log.info('Deleted {}'.format(permalink))
                else:
                    log.info('Pretending to delete {}'.format(permalink))
        else:
            log.debug('{} not old enough ({} days old, must be at least {}). Skipping'.format(permalink, delta.days, self.days_ago))

    def _backup_media_and_delete_tweets(self):
        finished = False

        max_id = None
        while not finished:
            response = self.session.get('https://api.twitter.com/1.1/statuses/user_timeline.json', params={
                'count': 200,
                'max_id': max_id,
            })
            response.raise_for_status()

            log.debug('Loaded next 200 tweets')

            results = response.json()

            for tweet in results:
                self._backup_media_and_delete(tweet)

            old_max_id = max_id
            max_id = tweet['id_str']

            finished = max_id == old_max_id

    def _nuclear(self):
        archive = ZipFile(self.nuke)
        files = archive.namelist()

        filtering_date = self.now.replace(days=-self.days_ago)
        filtering_date = filtering_date.date()

        def _get_tweet_file_date(filename):
            date = re.search('(\d{4})_(\d{2}).js', filename)

            if date:
                year, month = date.groups()
                year, month = int(year), int(month)

                date = datetime(year, month, 1)
                date = date.date()

                return date

        def _filter_tweet_files_with_valid_date(filename):
            '''Return <filename> if it's a data file and if it's also within our date range, or None if it isn't.'''
            date = _get_tweet_file_date(filename)

            if date:
                if date <= filtering_date:
                    return filename

        data_files = filter(_filter_tweet_files_with_valid_date, files)
        data_files = sorted(data_files, key=_get_tweet_file_date, reverse=True)

        for data_file in data_files:
            raw_data = archive.read(data_file)

            # Data files are in the format:
            #
            #     Grailbird.data.tweets_2014_12 =
            #     <Valid JSON object>
            #
            # We want to get to <Valid JSON object>, so we find the first carraige return and json.loads that.
            cr_index = raw_data.find('\n')
            raw_data = raw_data[cr_index:]

            tweets = json.loads(raw_data)

            for tweet in tweets:
                self._backup_media_and_delete(tweet, skip_deletion_error=True)

    def twittercide(self):
        self._get_or_create_parent_dir()

        if self.nuke:
            self._nuclear()

            log.info("Finished!")
        else:
            self._backup_media_and_delete_tweets()

            log.info("Finished! (Due to limits to Twitter's API, there still might be older tweets we can't access and delete yet.)")


if __name__ == '__main__':
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.root.handlers[0].formatter = logging.Formatter()

    t = Twittercider(days_ago=args.days_ago, dry_run=args.dry_run, nuke=args.nuclear, force_delete=args.force_delete)
    t.twittercide()
