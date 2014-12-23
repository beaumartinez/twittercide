# Twittercide

Delete your tweets and backup tweeted photos to [Google Drive](https://www.google.com/drive/).

## Installation

    pip install http://github.com/beaumartinez/twittercide/

Didn't work?

    easy_install pip

And try again. Still no joy? Install [Python](https://www.python.org/downloads/) and try again.

## About

Twittercide deletes your tweets and backs-up tweeted photos to a folder in Google Drive called Twittercide (surprise!).

It uses [foauth.org](http://foauth.org/) to authenticate with Twitter and Google's APIs. In order to use it, you'll
need to sign up with foauth.org, and [authorize both those services](https://foauth.org/services/).

For Twitter, you need to check the option to "read and send tweets". For Google, you need "access your documents".

Because of limitations to Twitter's API, Twittercide can only delete your last 3200 tweets (if you're someone like me,
that's a drop in the ocean compared to how much I've tweeted over the years), but you can use a
[Twitter archive zip file](https://support.twitter.com/articles/20170160-downloading-your-twitter-archive) with the
`--nuclear` option to delete all your tweets, from all time, forever.

Twittercide checks the MD5 checksums of backed-up photos, and it won't delete tweets with photos if it can't back them
up. You can delete them anyway with the `--force-delete` option. It's also very conservative when it comes to errors.
Anything other than an HTTP 200 and it'll raise an exception, stopping any potential global catastrophe. 

## Usage

For full usage—

    twittercide --help

To delete your tweets—

    twittercide <foauth.org email> <foauth.org password>

To delete only tweets that are 7 days old and older—

    twittercide <foauth.org email> <foauth.org password> --older-than 7

To delete only tweets that are older than a tweet with ID 123—

    twittercide <foauth.org email> <foauth.org password> --since-id 123

To run a dry run, without deleting any tweets but still backing up photos—

    twittercide <foauth.org email> <foauth.org password> --dry-run

To run a dry run with additional debug information—

    twittercide <foauth.org email> <foauth.org password> --dry-run --verbose

To delete the tweets in a Twitter archive zip file—

    twittercide <foauth.org email> <foauth.org password> --archive <path to Twitter archive zip file>

## Development

Create a virtualenv and install the requirements in `requirements.txt`.

To run tests—

    invoke test

I use [Invoke](https://github.com/pyinvoke/invoke), which is the successor to the venerable Fabric.

## Disclaimer

I wrote Twittercide for myself, and although it worked for me, there is a small chance that aliens will abduct you. Use
at your own risk!
