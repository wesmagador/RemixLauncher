import tempfile
import unittest
import zipfile
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch
import remix_core as core

class BackupTests(unittest.TestCase):
    def test_select_only_release_without_symbols(self):
        names = ['rtx-remix-for-x86-games-debug-remix-1.6.1.zip', 'rtx-remix-for-x86-games-debugoptimized-remix-1.6.1.zip', 'rtx-remix-for-x86-games-release-remix-1.6.1-symbols.zip', 'rtx-remix-for-x86-games-release-remix-1.6.1.zip', 'rtx-remix-for-x64-games-release-remix-1.6.1.zip']
        release = {'assets': [{'name': n} for n in names]}
        self.assertEqual(core.select_asset(release, 'x86')['name'], names[3])
        self.assertEqual(core.select_asset(release, 'x64')['name'], names[4])
    def setUp(self):
        self.root = Path(__file__).resolve().parent / ('test-work-' + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(lambda: shutil.rmtree(self.root) if self.root.resolve().parent == Path(__file__).resolve().parent else None)
        self.game = self.root / 'game'
        self.runtime = self.root / 'runtime'
        self.game.mkdir()
        (self.runtime / '.trex').mkdir(parents=True)
        (self.game / 'game.exe').write_bytes(b'game')
        (self.game / 'd3d9.dll').write_bytes(b'old runtime')
        (self.runtime / 'd3d9.dll').write_bytes(b'new runtime')
        (self.runtime / '.trex' / 'engine.dll').write_bytes(b'engine')
        self.profile = {'id': 'test', 'exe': str(self.game / 'game.exe')}

    def test_restore_existing_and_new_preserves_captures(self):
        backup = core.install(self.profile, self.runtime, self.root / 'backups', lambda x: None)
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'new runtime')
        (self.game / 'capture.usd').write_bytes(b'capture')
        (self.game / 'd3d9.dll').write_bytes(b'user edit')
        core.restore(backup, lambda x: None)
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'old runtime')
        self.assertFalse((self.game / '.trex').exists())
        self.assertTrue((self.game / 'capture.usd').exists())
        self.assertTrue(any(p.read_bytes() == b'user edit' for p in (backup / 'antes-de-restaurar').rglob('d3d9.dll')))

    def test_failed_install_rolls_back(self):
        original = core.shutil.copy2
        def fail(source, target, *args, **kwargs):
            if Path(source) == self.runtime / 'd3d9.dll':
                raise OSError('simulated failure')
            return original(source, target, *args, **kwargs)
        with patch.object(core.shutil, 'copy2', side_effect=fail):
            with self.assertRaises(OSError):
                core.install(self.profile, self.runtime, self.root / 'backups', lambda x: None)
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'old runtime')
        self.assertFalse((self.game / '.trex').exists())

    def test_corrupt_backup_does_not_modify_game(self):
        backup = core.install(self.profile, self.runtime, self.root / 'backups', lambda x: None)
        (backup / 'original' / 'd3d9.dll').write_bytes(b'corrupted')
        with self.assertRaises(ValueError): core.restore(backup)
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'new runtime')

    def test_zip_traversal_rejected(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z: z.writestr('../escape.dll', b'bad')
        with self.assertRaises(ValueError): core.unpack_runtime(archive, self.root / 'stage', 'x86')
        self.assertFalse((self.root / 'escape.dll').exists())

if __name__ == '__main__': unittest.main()
