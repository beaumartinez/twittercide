# Twittercide

Delete your tweets and backup tweeted photos to [Google Drive](https://www.google.com/drive/).

> Twittercide (noun)
>
> 1. To delete/wipe everything on your Twitter page, effectively committing social networking suicide on Twitter.

## Installation

    pip install git+https://github.com/beaumartinez/twittercide

## About

Twittercide deletes your tweets and backs-up tweeted photos to Google Drive, in a folder called Twittercide. The
backed-up photos have the modified date set to when you tweeted them, and the description set to the tweet text.

Because of limitations to Twitter's API, Twittercide can only delete your last 3200 tweets (if you're someone like me,
that's a drop in the ocean), but you can use a
[Twitter archive zip file](https://support.twitter.com/articles/20170160-downloading-your-twitter-archive) with the
`--archive` option to delete all your tweets, from all time, *forever*.

You can selectively delete tweets as old and older than a few days using the `--older-than` option, and older than a
specific ID using the `--since-id` option. Easy way to wipe any old, irrelevant tweets.

Don't want to delete tweets? You can use the `--dry-run` to see what tweets would have been deleted, but still back-up
photos.

Twittercide checks the MD5 checksums of backed-up photos, and it won't delete tweets with photos if it can't back them
up. You can delete them anyway with the `--force-delete` option. It's also very conservative when it comes to errors.
Any non-kosher HTTP status codes and it'll raise an exception, stopping any potential global catastrophe. 

## Usage

Twittercide uses [foauth.org](http://foauth.org/) to authenticate with Twitter and Google's APIs. **In order to use it,
you'll need to sign up with foauth.org**, and [authorize both those services](https://foauth.org/services/).

For Twitter, you need to check the option to "read and send tweets". For Google, you need "access your documents".

For full usage—

    twittercide --help

### Example usage

To delete all your tweets—

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

    inv test

I use [Invoke](https://github.com/pyinvoke/invoke), which is the successor to the venerable Fabric.

## Disclaimer

I wrote Twittercide for myself, and although it worked for me, there is a small chance that aliens will abduct you. Use
at your own risk! (I'd add some warning emojis here but Vim's formatting doesn't like them.)

## License

I struggle enough writing code to deal with chosing a license, so I just slapped the good old Do What The Fuck You Want
Public License on this. [In the words of The Hodgetwins](https://www.youtube.com/watch?v=rWv9fZokqaU), you can do
whatever the fuck you wanna do.
