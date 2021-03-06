from mock import patch

from django.test import TransactionTestCase as TestCase
from django.core.management import execute_from_command_line

from dbbackup.tests.utils import (TEST_DATABASE, HANDLED_FILES,
                                  clean_gpg_keys, add_public_gpg,
                                  add_private_gpg, get_dump,
                                  get_dump_name)

from dbbackup.tests.testapp import models


@patch('django.conf.settings.DATABASES', {'default': TEST_DATABASE})
@patch('dbbackup.settings.STORAGE', 'dbbackup.tests.utils')
class DbBackupCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        open(TEST_DATABASE['NAME'], 'a').close()
        self.instance = models.CharModel.objects.create(field='foo')

    def tearDown(self):
        clean_gpg_keys()

    def test_encrypt(self):
        argv = ['', 'dbbackup', '--encrypt']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertTrue(filename.endswith('.gpg'))
        # Test file content
        outputfile = HANDLED_FILES['written_files'][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b'-----BEGIN PGP MESSAGE-----'))

    def test_compress(self):
        argv = ['', 'dbbackup', '--compress']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertTrue(filename.endswith('.gz'))

    def test_compress_and_encrypt(self):
        argv = ['', 'dbbackup', '--compress', '--encrypt']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertTrue(filename.endswith('.gz.gpg'))
        # Test file content
        outputfile = HANDLED_FILES['written_files'][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b'-----BEGIN PGP MESSAGE-----'))


@patch('django.conf.settings.DATABASES', {'default': TEST_DATABASE})
@patch('dbbackup.settings.STORAGE', 'dbbackup.tests.utils')
@patch('dbbackup.management.commands.dbrestore.input', return_value='y')
class DbRestoreCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        add_private_gpg()
        open(TEST_DATABASE['NAME'], 'a').close()
        self.instance = models.CharModel.objects.create(field='foo')

    def tearDown(self):
        clean_gpg_keys()

    def test_restore(self, *args):
        # Create backup
        execute_from_command_line(['', 'dbbackup'])
        self.instance.delete()
        # Restore
        execute_from_command_line(['', 'dbrestore'])
        restored = models.CharModel.objects.all().exists()
        self.assertTrue(restored)

    @patch('dbbackup.utils.getpass', return_value=None)
    def test_encrypted(self, *args):
        # Create backup
        execute_from_command_line(['', 'dbbackup', '--encrypt'])
        self.instance.delete()
        # Restore
        execute_from_command_line(['', 'dbrestore', '--decrypt'])
        restored = models.CharModel.objects.all().exists()
        self.assertTrue(restored)

    def test_compressed(self, *args):
        # Create backup
        execute_from_command_line(['', 'dbbackup', '--compress'])
        self.instance.delete()
        # Restore
        execute_from_command_line(['', 'dbrestore', '--uncompress'])

    def test_no_backup_available(self, *args):
        with self.assertRaises(SystemExit):
            execute_from_command_line(['', 'dbrestore'])

    @patch('dbbackup.utils.getpass', return_value=None)
    def test_available_but_not_encrypted(self, *args):
        # Create backup
        execute_from_command_line(['', 'dbbackup'])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(['', 'dbrestore', '--decrypt'])

    def test_available_but_not_compressed(self, *args):
        # Create backup
        execute_from_command_line(['', 'dbbackup'])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(['', 'dbrestore', '--uncompress'])


@patch('dbbackup.settings.STORAGE', 'dbbackup.tests.utils')
class MediaBackupCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()

    def tearDown(self):
        clean_gpg_keys()

    def test_encrypt(self):
        argv = ['', 'mediabackup', '--encrypt']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertTrue('.gpg' in filename)
        # Test file content
        outputfile = HANDLED_FILES['written_files'][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b'-----BEGIN PGP MESSAGE-----'))

    def test_no_compress(self):
        argv = ['', 'mediabackup', '--no-compress']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertFalse('.gz' in filename)

    @patch('dbbackup.utils.getpass', return_value=None)
    @patch('dbbackup.management.commands.dbrestore.input', return_value='y')
    def test_no_compress_and_encrypted(self, getpass_mock, confirm_mock):
        argv = ['', 'mediabackup', '--no-compress', '--encrypt']
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES['written_files']))
        filename, outputfile = HANDLED_FILES['written_files'][0]
        self.assertTrue('.gpg' in filename)
        self.assertFalse('.gz' in filename)
        # Test file content
        outputfile = HANDLED_FILES['written_files'][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b'-----BEGIN PGP MESSAGE-----'))

    # def test_available_but_not_compressed(self, *args):
    #     # Create backup
    #     execute_from_command_line(['', 'dbbackup'])
    #     # Restore
    #     with self.assertRaises(Exception):
    #         execute_from_command_line(['', 'dbrestore', '--uncompress'])
