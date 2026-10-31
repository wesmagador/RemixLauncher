import unittest
import uuid
import shutil
import struct
from pathlib import Path
from unittest.mock import patch
import qt_launcher as ui
import launcher_support as support
import remix_core as core
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton, QDialog

class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder=Path(__file__).resolve().parent/('ui-test-'+uuid.uuid4().hex)
        self.folder.mkdir()
        self.patch=patch.object(core,'DATA',self.folder/'dados')
        self.patch.start()
        self.window=ui.Launcher()
    def tearDown(self):
        self.window.close()
        for handler in list(self.window.logger.handlers):
            handler.close()
            self.window.logger.removeHandler(handler)
        self.patch.stop()
        if self.folder.resolve().parent==Path(__file__).resolve().parent:shutil.rmtree(self.folder)

    def make_exe(self):
        folder=self.folder/'Example Game'
        folder.mkdir()
        exe=folder/'game.exe'
        data=bytearray(128)
        data[:2]=b'MZ'
        struct.pack_into('<I',data,0x3c,64)
        data[64:68]=b'PE\0\0'
        struct.pack_into('<H',data,68,0x14c)
        exe.write_bytes(data)
        return exe

    def test_library_navigation_and_registration(self):
        self.assertEqual(self.window.pages.currentIndex(),0)
        self.window.enter_game(self.window.library_list.item(0))
        self.assertEqual(self.window.pages.currentIndex(),1)
        exe=self.make_exe()
        self.window.register_game('Example',str(exe))
        self.window.open_library()
        self.assertEqual(self.window.library_list.count(),2)
        self.window.search.setText('Example')
        self.assertEqual(self.window.library_list.count(),1)
        with self.assertRaises(ValueError):self.window.register_game('Duplicate',str(exe))

    def test_add_menu_and_log_dialog(self):
        observed=[]
        def inspect():
            dialog=next(w for w in QApplication.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible())
            observed.extend(b.text() for b in dialog.findChildren(QPushButton))
            dialog.reject()
        QTimer.singleShot(50,inspect)
        self.window.add_game()
        self.assertIn('Buscar instalados',observed)
        self.assertIn('Buscar em pasta',observed)
        self.assertIn('Escolher .exe manualmente',observed)
        self.window.log('Persistência de teste')
        self.assertIn('Persistência de teste',(core.DATA/'logs'/'launcher.log').read_text(encoding='utf-8'))
        QTimer.singleShot(50,inspect)
        self.window.open_app_logs()

    def test_discovery_and_runtime_diagnosis(self):
        exe=self.make_exe()
        candidates=support.scan_games([self.folder])
        self.assertEqual([c['exe'] for c in candidates],[str(exe.resolve())])
        logs=exe.parent/'rtx-remix'/'logs'
        logs.mkdir(parents=True)
        (logs/'remix-dxvk.log').write_text('Trying to raytrace but not detecting a valid camera.\nFailed to recreate swap chain',encoding='utf-8')
        report=support.diagnosis(str(exe))
        self.assertIn('CÂMERA:',report)
        self.assertIn('APRESENTAÇÃO:',report)

if __name__=='__main__':unittest.main()
