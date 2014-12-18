#!/usr/bin/env python

from argparse import ArgumentParser
from email.encoders import encode_noop
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import json

from requests import Request, Session
from requests_foauth import Foauth


parser = ArgumentParser(description='Delete your last 3200 tweets and backup tweeted photos to Google Drive')
parser.add_argument('email', help='foauth.org email')
parser.add_argument('password', help='foauth.org password')
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()


session = Session()
session.mount('https://', Foauth(args.email, args.password))


def _prepare_upload(title, file_):
    '''Prepares a Request to upload the file <file_>, giving it the title <title>.'''
    # http://stackoverflow.com/questions/15746558/how-to-send-a-multipart-related-with-requests-in-python

    message = MIMEMultipart('related')

    image = MIMEImage(file_.read())

    metadata = {
        'title': title,
    }
    metadata = json.dumps(metadata)
    metadata = MIMEApplication(metadata, 'json', encode_noop)

    message.attach(metadata)
    message.attach(image)

    body = message.as_string()
    headers = dict(message.items())

    request = Request(
        'post',
        'https://www.googleapis.com/upload/drive/v2/files?uploadType=multipart',
        data=body,
        headers=headers
    )

    return request


if __name__ == '__main__':
    # TODO: Search first

    with open('/Users/beau/Pictures/1418760457552.png', mode='rb') as file_:
        request = _prepare_upload('lel.png', file_)

    request = session.prepare_request(request)
    response = session.send(request)

    response.raise_for_status()
