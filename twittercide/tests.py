from unittest import TestCase

from .args import parse_args
from .twittercide import _QUERY_BLACKLIST, _prepare_query


class TwittercideTest(TestCase):

    def test_args(self):
        email = 'email'
        password = 'password'

        args = parse_args((email, password))

        self.assertEquals(args.email, email)
        self.assertEquals(args.password, password)

        # Defaults

        self.assertEquals(args.archive, None)
        self.assertFalse(args.dry_run, False)
        self.assertFalse(args.force_delete, False)
        self.assertEquals(args.older_than, None)
        self.assertEquals(args.since_id, None)
        self.assertFalse(args.verbose, False)

        # --archive

        archive = 'README.md'
        args = parse_args((email, password, '--archive', archive))

        self.assertEquals(args.archive.name, archive)

        archive = 'README.md'
        args = parse_args((email, password, '-a', archive))

        self.assertEquals(args.archive.name, archive)

        # --dry-run

        args = parse_args((email, password, '--dry-run'))

        self.assertTrue(args.dry_run)

        # --force-delete

        args = parse_args((email, password, '--force-delete'))
        self.assertTrue(args.force_delete)

        args = parse_args((email, password, '-f'))
        self.assertTrue(args.force_delete)

        # --older-than

        older_than = 0

        args = parse_args((email, password, '--older-than', older_than))
        self.assertEquals(args.older_than, older_than)

        args = parse_args((email, password, '-o', older_than))
        self.assertEquals(args.older_than, older_than)

        # --since-id

        since_id = 0

        args = parse_args((email, password, '--since-id', since_id))
        self.assertEquals(args.since_id, since_id)

        args = parse_args((email, password, '-s', since_id))
        self.assertEquals(args.since_id, since_id)

        # --verbose

        args = parse_args((email, password, '--verbose'))
        self.assertTrue(args.verbose)

        args = parse_args((email, password, '-v'))
        self.assertTrue(args.verbose)

    def test_prepare_query(self):
        # Empty

        query = {

        }
        prepared_query = _prepare_query(query)

        self.assertEquals(prepared_query, '')

        # Whitelisted, also ordering

        query = {
            'a': 'value',
            'b': 'value'
        }
        prepared_query = _prepare_query(query)

        for key in query:
            self.assertTrue(key not in _QUERY_BLACKLIST)

        self.assertEquals(prepared_query, 'a = "value" and b = "value"')

        # Blacklisted

        query = {
            _QUERY_BLACKLIST[0]: 'value',
        }
        prepared_query = _prepare_query(query)

        for key in query:
            self.assertTrue(key in _QUERY_BLACKLIST)

        self.assertEquals(prepared_query, '')

        # Parents, the one special case

        query = {
            'parents': ({
                'kind': 'drive#folder',
                'id': 'id',
            },)
        }
        prepared_query = _prepare_query(query)

        self.assertEquals(prepared_query, '"id" in parents')
