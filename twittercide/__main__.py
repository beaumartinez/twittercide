from sys import argv
import logging

from .args import parse_args
from .twittercide import Twittercider, log


def main():
    args = parse_args(argv)

    if args.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.root.handlers[0].formatter = logging.Formatter()

    t = Twittercider(
        archive=args.archive,
        dry_run=args.dry_run,
        force_delete=args.force_delete,
        older_than=args.older_than,
        since_id=args.since_id
    )

    t.twittercide()


if __name__ == '__main__':
    main()
