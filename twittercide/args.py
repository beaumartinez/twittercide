from argparse import ArgumentParser, RawTextHelpFormatter


def parse_args(args):
    with open('README.md') as readme_file:
        readme = readme_file.read()

    parser = ArgumentParser(
        description='Delete your tweets and backup tweeted photos to Google Drive',
        epilog=readme,
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument('email', help='foauth.org email')
    parser.add_argument('password', help='foauth.org password')
    parser.add_argument('--archive', '-a', help="GO NUCLEAR. Delete using a Twitter archive zip file", type=file)
    parser.add_argument('--dry-run', action='store_true', help="Don't delete any tweets, but backup tweeted photos")
    parser.add_argument('--force-delete', '-f', action='store_true', help="Delete tweets even if the photos couldn't be backed up")
    parser.add_argument('--older-than', '-o', help="Only delete tweets as old and older than OLDER_THAN days (0 will still delete all tweets)", type=int)
    parser.add_argument('--since-id', '-s', help="Only delete tweets once we find this ID. If it's not found, no tweets will be deleted")
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose debug logging')

    args = parser.parse_args(args)

    return args
