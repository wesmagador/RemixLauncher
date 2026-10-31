import sys
from pathlib import Path
vendor = Path(__file__).resolve().parent / 'vendor'
if vendor.exists(): sys.path.insert(0, str(vendor))
import os
import subprocess
import threading
import uuid
import shutil
import webbrowser
import traceback
from datetime import datetime
import launcher_support as support
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox, QInputDialog, QProgressBar, QFrame, QStackedWidget, QListWidget, QListWidgetItem, QLineEdit, QDialog, QDialogButtonBox)
import remix_core as core

class Events(QObject):
    log = Signal(str)
    error = Signal(str)
    done = Signal()

class SearchDialog(QDialog):
    scanning=False
    def reject(self):
        if not self.scanning:super().reject()
    def closeEvent(self,event):
        if self.scanning:event.ignore()
        else:super().closeEvent(event)

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Remix Launcher • 1.2')
        self.logger = support.app_logger()
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parent/'launcher.ico')))
        self.resize(1180, 800)
        self.setMinimumSize(1020, 740)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowOpacity(1.0)
        self.busy = False
        self.events = Events()
        self.events.log.connect(self.log)
        self.events.error.connect(lambda s: (self.log('ERRO: '+s), QMessageBox.critical(self, 'Operação não concluída', s)))
        self.events.done.connect(self.finished)
        self.config = core.DATA / 'jogos.json'
        self.games = core.read_json(self.config, [{'id':'ac1','name':'Assassin’s Creed — Director’s Cut','exe':''}])
        root = QWidget()
        root.setObjectName('root')
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        side = QFrame()
        side.setObjectName('sidebar')
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(24,32,24,24)
        sl.setSpacing(12)
        sl.addWidget(self.label('R /', 'brand'))
        sl.addWidget(self.label('REMIX LAUNCHER', 'brandname'))
        sl.addSpacing(30)
        sl.addWidget(self.label('WORKSPACE', 'eyebrow'))
        sl.addWidget(self.button('▦   Biblioteca', self.open_library, 'nav'))
        sl.addWidget(self.button('+   Adicionar jogo', self.add_game))
        sl.addWidget(self.button('↶   Pasta de backups', self.open_backups))
        sl.addWidget(self.button('☰   Logs da aplicação', self.open_app_logs))
        sl.addStretch()
        sl.addWidget(self.label('SEU JOGO. NOVA LUZ.', 'green'))
        sl.addWidget(self.label('Runtime oficial\nBackups locais e reversíveis', 'muted'))
        sl.addWidget(self.button('NVIDIA App / Toolkit ↗', lambda: webbrowser.open('https://www.nvidia.com/en-us/software/nvidia-app/')))
        layout.addWidget(side)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages,1)
        library = QWidget()
        lib = QVBoxLayout(library)
        lib.setContentsMargins(30,28,30,24)
        lib.addWidget(self.label('Sua biblioteca', 'heading'))
        lib.addWidget(self.label('Escolha um jogo para instalar, jogar ou consultar os logs.', 'muted'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Filtrar jogos da biblioteca...')
        self.search.textChanged.connect(self.refresh_library)
        lib.addWidget(self.search)
        self.library_list = QListWidget()
        self.library_list.setSpacing(8)
        self.library_list.itemClicked.connect(self.enter_game)
        lib.addWidget(self.library_list,1)
        lib.addWidget(self.button('+  Adicionar jogo à biblioteca', self.add_game, 'primary'))
        self.pages.addWidget(library)
        panel = QWidget()
        main = QVBoxLayout(panel)
        main.setContentsMargins(30,28,30,20)
        main.setSpacing(13)
        main.addWidget(self.button('‹  Voltar à biblioteca', self.open_library))
        main.addWidget(self.label('Prepare, experimente e restaure seus jogos em um só lugar.', 'muted'))
        self.combo = QComboBox()
        self.combo.addItems([g['name'] for g in self.games])
        self.combo.hide()
        hero = QFrame()
        hero.setObjectName('hero')
        hero.setMinimumHeight(165)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24,20,24,20)
        hl.addWidget(self.label('BIBLIOTECA  /  DIRECTX 9', 'green'))
        self.title = self.label('Assassin’s Creed', 'title')
        hl.addWidget(self.title)
        self.subtitle = self.label('Director’s Cut • Perfil experimental', 'muted')
        hl.addWidget(self.subtitle)
        hl.addWidget(self.label('Path tracing começa com uma boa captura.', 'muted'))
        main.addWidget(hero)
        self.status = self.label('', 'green')
        self.path = self.label('', 'muted')
        self.path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path.setWordWrap(True)
        main.addWidget(self.status)
        main.addWidget(self.path)
        actions = QHBoxLayout()
        self.actions=[]
        for text, callback, name in [('Selecionar .exe',self.choose_exe,''),('Instalar RTX Remix',lambda:self.install(False),'primary'),('Importar ZIP',lambda:self.install(True),''),('Restaurar',self.restore,''),('▶  Jogar',self.play,'')]:
            b=self.button(text,callback,name)
            self.actions.append(b)
            actions.addWidget(b)
        main.addLayout(actions)
        tools = QHBoxLayout()
        for text, callback in [('Logs e diagnóstico', self.open_game_logs), ('Jogar com log detalhado', lambda:self.play(True))]:
            b=self.button(text,callback)
            self.actions.append(b)
            tools.addWidget(b)
        main.addLayout(tools)
        steps=self.label('01  Selecione o jogo    →    02  Instale com backup    →    03  Abra e teste Alt + X', 'steps')
        main.addWidget(steps)
        logrow=QHBoxLayout()
        logrow.addWidget(self.label('ATIVIDADE', 'eyebrow'))
        logrow.addStretch()
        logrow.addWidget(self.button('Releases oficiais ↗', lambda:webbrowser.open('https://github.com/NVIDIAGameWorks/rtx-remix/releases')))
        main.addLayout(logrow)
        self.progress=QProgressBar()
        self.progress.setRange(0,100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        main.addWidget(self.progress)
        self.output=QTextEdit()
        self.output.setReadOnly(True)
        main.addWidget(self.output,1)
        main.addWidget(self.label('Feche o jogo antes de instalar ou restaurar. AC1: compatibilidade experimental.', 'muted'))
        self.pages.addWidget(panel)
        self.combo.currentIndexChanged.connect(self.show_game)
        self.show_game()
        self.refresh_library()
        self.log('Tudo pronto. Selecione o executável e clique em Instalar RTX Remix.\nO runtime será baixado automaticamente com backup antes da instalação.')

    def open_library(self):
        self.refresh_library()
        self.pages.setCurrentIndex(0)

    def refresh_library(self,*args):
        self.library_list.clear()
        query=self.search.text().casefold()
        for index,g in enumerate(self.games):
            if query not in g['name'].casefold():continue
            state='Backup disponível' if self.backups(g) else 'Pronto para configurar'
            item=QListWidgetItem(f'{g["name"]}    ›\n{state}\n{g["exe"] or "Executável ainda não selecionado"}')
            item.setData(Qt.ItemDataRole.UserRole,index)
            item.setSizeHint(QSize(0,100))
            self.library_list.addItem(item)

    def enter_game(self,item):
        if self.busy:
            QMessageBox.information(self,'Operação em andamento','Aguarde a operação atual antes de trocar de jogo.')
            return
        self.combo.setCurrentIndex(item.data(Qt.ItemDataRole.UserRole))
        self.show_game()
        self.pages.setCurrentIndex(1)

    def open_app_logs(self):
        self.log_viewer('Logs da aplicação', list((core.DATA/'logs').glob('launcher.log*')))

    def open_game_logs(self):
        self.log_viewer('Logs e diagnóstico — '+self.game()['name'],support.runtime_logs(self.game()['exe']),self.game()['exe'])

    def log_viewer(self,title,files,exe=None):
        dialog=QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(950,650)
        box=QVBoxLayout(dialog)
        chooser=QComboBox()
        viewer=QTextEdit()
        viewer.setReadOnly(True)
        box.addWidget(chooser)
        box.addWidget(viewer,1)
        def populate():
            nonlocal files
            files=support.runtime_logs(exe) if exe else list((core.DATA/'logs').glob('launcher.log*'))
            chooser.blockSignals(True)
            chooser.clear()
            chooser.addItem('Diagnóstico / resumo',None)
            for p in files:chooser.addItem(p.name,str(p))
            chooser.blockSignals(False)
            load()
        def load(*args):
            path=chooser.currentData()
            try:viewer.setPlainText(support.read_tail(path) if path else (support.diagnosis(exe) if exe else f'Logs locais: {core.DATA / "logs"}\nEscolha um arquivo acima. Os registros são rotacionados em arquivos de até 2 MB.'))
            except OSError as error:viewer.setPlainText(str(error))
        def export():
            path,_=QFileDialog.getSaveFileName(dialog,'Salvar relatório local','diagnostico-remix.txt','Texto (*.txt)')
            if path:
                Path(path).write_text(viewer.toPlainText(),encoding='utf-8')
                self.log('Relatório exportado: '+path)
        chooser.currentIndexChanged.connect(load)
        row=QHBoxLayout()
        row.addWidget(self.button('Atualizar',populate))
        row.addWidget(self.button('Exportar texto',export))
        row.addWidget(self.button('Abrir pasta',lambda:os.startfile(str(Path(exe).parent/'rtx-remix'/'logs') if exe and (Path(exe).parent/'rtx-remix'/'logs').is_dir() else str(core.DATA/'logs'))))
        row.addWidget(self.button('Fechar',dialog.accept))
        box.addLayout(row)
        populate()
        dialog.exec()

    def label(self,text,name):
        w=QLabel(text)
        w.setObjectName(name)
        return w
    def button(self,text,callback,name=''):
        w=QPushButton(text)
        w.setObjectName(name)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.clicked.connect(callback)
        return w
    def game(self): return self.games[self.combo.currentIndex()]
    def backups(self,game):
        return sorted([p.parent for p in (core.DATA/'backups'/game['id']).glob('*/manifest.json') if core.read_json(p)['status'] in ('installed','installing')],reverse=True)
    def show_game(self,*args):
        g=self.game()
        self.title.setText('Assassin’s Creed' if g['id']=='ac1' else g['name'])
        self.subtitle.setText('Director’s Cut • Perfil experimental' if g['id']=='ac1' else 'Perfil personalizado • Compatibilidade a verificar')
        self.path.setText(g['exe'] or 'Executável ainda não selecionado.')
        self.status.setText('Backup disponível • Instalação ativa ou pendente' if self.backups(g) else 'Pronto para configurar')
    def log(self,text):
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(datetime.now().strftime('[%H:%M:%S] ')+text+'\n')
        self.logger.info(text)
    def run(self,fn):
        if self.busy:return
        self.busy=True
        self.combo.setEnabled(False)
        for b in self.actions:b.setEnabled(False)
        self.progress.setRange(0,0)
        def worker():
            try:fn(self.events.log.emit)
            except Exception as e:
                self.logger.exception('Operação falhou')
                self.events.error.emit(str(e))
            finally:self.events.done.emit()
        threading.Thread(target=worker,daemon=True).start()
    def finished(self):
        self.busy=False
        self.combo.setEnabled(True)
        for b in self.actions:b.setEnabled(True)
        self.progress.setRange(0,100)
        self.progress.setValue(0)
        self.show_game()
        self.refresh_library()
    def choose_exe(self):
        g=self.game()
        if self.backups(g):
            QMessageBox.information(self,'Backup ativo','Restaure antes de mudar o executável deste perfil.')
            return
        path,_=QFileDialog.getOpenFileName(self,'Selecione o executável DX9 do jogo','','Executáveis (*.exe)')
        if not path:return
        try:
            arch=core.architecture(path)
            if g['id']=='ac1' and Path(path).name.lower()!='assassinscreed_dx9.exe':raise ValueError('Para AC1 selecione AssassinsCreed_Dx9.exe.')
            if any(o['id']!=g['id'] and o['exe'] and Path(o['exe']).resolve().parent==Path(path).resolve().parent for o in self.games):raise ValueError('A pasta já pertence a outro perfil.')
            g['exe']=path
            core.save_json(self.config,self.games)
            self.show_game()
            self.log(f'Executável {arch}: {path}')
        except Exception as e:QMessageBox.critical(self,'Executável inválido',str(e))
    def add_game(self):
        if self.busy:return
        dialog=SearchDialog(self)
        dialog.setWindowTitle('Adicionar jogos')
        dialog.resize(640,520)
        box=QVBoxLayout(dialog)
        box.addWidget(self.label('Encontre seus jogos', 'heading'))
        note=self.label('Detectar um executável não confirma compatibilidade com RTX Remix.\nSelecione os jogos que deseja adicionar.', 'muted')
        note.setWordWrap(True)
        box.addWidget(note)
        row=QHBoxLayout()
        results=QListWidget()
        results.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        scan_events=Events(dialog)
        controls=[]
        def scan(folder=False):
            roots=None
            if folder:
                path=QFileDialog.getExistingDirectory(dialog,'Pasta para buscar jogos')
                if not path:return
                roots=[Path(path)]
            results.clear()
            dialog.scanning=True
            note.setText('Buscando jogos instalados... Aguarde.')
            for b in controls:b.setEnabled(False)
            # A busca roda em segundo plano; só sinais atualizam a interface.
            def worker():
                try:
                    candidates=support.scan_games(roots, self.events.log.emit)
                    import json
                    scan_events.log.emit(json.dumps(candidates,ensure_ascii=False))
                except Exception as error:scan_events.error.emit(str(error))
                finally:scan_events.done.emit()
            threading.Thread(target=worker,daemon=True).start()
        def display(payload):
            import json
            for candidate in json.loads(payload):
                item=QListWidgetItem(f'{candidate["name"]} • {candidate["arch"]}\n{candidate["exe"]}')
                item.setData(Qt.ItemDataRole.UserRole,candidate)
                results.addItem(item)
            note.setText(f'{results.count()} executáveis encontrados. Selecione para adicionar. Compatibilidade a verificar.')
        scan_events.log.connect(display)
        scan_events.error.connect(lambda text:note.setText(text))
        def completed():
            dialog.scanning=False
            for b in controls:b.setEnabled(True)
        scan_events.done.connect(completed)
        for title,fn in [('Buscar instalados',lambda:scan(False)),('Buscar em pasta',lambda:scan(True))]:
            b=self.button(title,fn)
            controls.append(b)
            row.addWidget(b)
        box.addLayout(row)
        box.addWidget(results,1)
        def manual():
            path,_=QFileDialog.getOpenFileName(dialog,'Executável do jogo','','Executáveis (*.exe)')
            if path:
                name,ok=QInputDialog.getText(dialog,'Nome do jogo','Nome na biblioteca:',text=Path(path).parent.name)
                if ok and name.strip():
                    try:self.register_game(name.strip(),path);dialog.accept()
                    except Exception as error:QMessageBox.warning(dialog,'Não foi possível adicionar',str(error))
        def add_selected():
            for item in results.selectedItems():
                candidate=item.data(Qt.ItemDataRole.UserRole)
                try:self.register_game(candidate['name'],candidate['exe'])
                except Exception as error:self.log(str(error))
            dialog.accept()
        bottom=QHBoxLayout()
        for title,fn,kind in [('Escolher .exe manualmente',manual,''),('Adicionar selecionados',add_selected,'primary')]:
            b=self.button(title,fn,kind)
            controls.append(b)
            bottom.addWidget(b)
        box.addLayout(bottom)
        dialog.exec()

    def register_game(self,name,path):
        core.architecture(path)
        exe=Path(path).resolve()
        for index,g in enumerate(self.games):
            if g['exe'] and Path(g['exe']).resolve().parent==exe.parent:
                raise ValueError('Essa pasta já está cadastrada: '+g['name'])
        if exe.name.lower()=='assassinscreed_dx9.exe':
            existing=next((g for g in self.games if g['id']=='ac1' and not g['exe']),None)
            if existing:
                existing['exe']=str(exe)
                core.save_json(self.config,self.games)
                self.refresh_library()
                return
        self.games.append({'id':uuid.uuid4().hex,'name':name,'exe':str(exe)})
        core.save_json(self.config,self.games)
        self.combo.addItem(name)
        self.refresh_library()
        self.log('Jogo adicionado: '+name+' — '+str(exe))
    def install(self,local):
        g=dict(self.game())
        if not g['exe'] or not Path(g['exe']).is_file():
            QMessageBox.information(self,'Selecione o jogo','Selecione um executável existente primeiro.')
            return
        if self.backups(g):
            QMessageBox.information(self,'Backup ativo','Restaure a instalação atual antes de instalar outra versão.')
            return
        archive=QFileDialog.getOpenFileName(self,'Runtime oficial','','ZIP (*.zip)')[0] if local else None
        if local and not archive:return
        def operation(log):
            arch=core.architecture(g['exe'])
            package=archive or core.download_runtime(arch,log)
            stage=core.DATA/('runtime-'+uuid.uuid4().hex)
            stage.mkdir(parents=True)
            try:
                log('Validando e extraindo runtime...')
                runtime=core.unpack_runtime(package,stage,arch)
                log('Criando backup e instalando...')
                core.install(g,runtime,core.DATA/'backups'/g['id'],log)
            finally:
                if stage.resolve().parent==core.DATA.resolve():shutil.rmtree(stage)
            log('Instalação concluída. Abra o jogo e teste Alt + X.')
        self.run(operation)
    def restore(self):
        backups=self.backups(self.game())
        if not backups:
            QMessageBox.information(self,'Backups','Nenhum backup ativo deste launcher.')
            return
        self.run(lambda log:core.restore(backups[0],log))
    def play(self,debug=False):
        try:
            exe=Path(self.game()['exe'])
            if not exe.is_file():raise ValueError('Selecione o executável primeiro.')
            env=os.environ.copy()
            if debug:env['DXVK_LOG_LEVEL']='debug'
            process=subprocess.Popen([str(exe)],cwd=exe.parent,env=env)
            self.log(f'Jogo iniciado. PID {process.pid}. Log detalhado: {bool(debug)}. Teste Alt + X.')
            def watch():
                code=process.wait()
                self.events.log.emit(f'Jogo encerrado. PID {process.pid}, código {code}. Consulte Logs e diagnóstico.')
            threading.Thread(target=watch,daemon=True).start()
        except Exception as e:QMessageBox.critical(self,'Não foi possível iniciar',str(e))
    def open_backups(self):
        folder=core.DATA/'backups'
        folder.mkdir(parents=True,exist_ok=True)
        os.startfile(folder)
    def closeEvent(self,event):
        if self.busy:
            QMessageBox.information(self,'Operação em andamento','Aguarde a operação terminar antes de fechar.')
            event.ignore()
        else:event.accept()

STYLE='''
QWidget { background-color: #0c1015; color: #e8edf4; font-family: "Segoe UI"; font-size: 12px; }
QFrame#sidebar { background-color: #121922; border-right: 1px solid #23303c; }
QFrame#sidebar QLabel { background-color: #121922; }
QLabel#brand { color: #b5f36b; font-size: 38px; font-weight: 800; }
QLabel#brandname { font-size: 14px; font-weight: 700; }
QLabel#heading { font-size: 30px; font-weight: 700; }
QLabel#title { font-size: 30px; font-weight: 700; background: #1b2929; }
QLabel#muted { color: #98aabd; }
QLabel#green { color: #b5f36b; font-weight: 600; }
QLabel#eyebrow { color: #8194aa; font-size: 10px; font-weight: 700; }
QFrame#hero { background-color: #1b2929; border: 1px solid #31443c; border-radius: 14px; }
QFrame#hero QLabel { background-color: #1b2929; border: none; }
QPushButton { background-color: #222e3c; border: 1px solid #2c3b4c; border-radius: 7px; padding: 11px 12px; font-weight: 600; }
QPushButton:hover { background-color: #304056; }
QPushButton:disabled { color: #718094; background-color: #18212b; }
QPushButton#primary { background-color: #b5f36b; color: #17210f; border: none; }
QPushButton#primary:hover { background-color: #9edd54; }
QPushButton#nav { background-color: #283a26; color: #b5f36b; border: none; text-align:center; }
QFrame#sidebar QPushButton { text-align:center; }
QListWidget { background:#0c1015; border:none; outline:none; }
QListWidget::item { background:#18232e; border:1px solid #2c3b4c; border-radius:9px; padding:14px; }
QListWidget::item:hover { background:#243545; }
QListWidget::item:selected { background:#2b402c; border-color:#b5f36b; }
QLineEdit { background:#18222e; border:1px solid #2c3b4c; border-radius:7px; padding:12px; }
QComboBox { background-color: #18222e; border: 1px solid #2c3b4c; border-radius: 7px; padding: 11px; }
QComboBox QAbstractItemView { background-color: #18222e; selection-background-color: #344934; }
QLabel#steps { background-color: #151e29; padding: 16px; border-radius: 8px; color: #a7bacd; }
QTextEdit { background-color: #111923; border: 1px solid #202e3f; border-radius: 9px; padding: 10px; color: #b5c6d7; font-family: Consolas; font-size: 11px; }
QProgressBar { background-color: #243343; border: none; }
QProgressBar::chunk { background-color: #b5f36b; }
'''

if __name__=='__main__':
    app=QApplication(sys.argv)
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('RemixLauncher.Desktop.1')
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent/'launcher.ico')))
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window=Launcher()
    def unhandled(kind,value,tb):
        window.logger.error('Erro não tratado',exc_info=(kind,value,tb))
        QMessageBox.critical(window,'Erro na aplicação',str(value)+'\nConsulte Logs da aplicação.')
    sys.excepthook=unhandled
    window.show()
    if '--smoke-test' in sys.argv:
        def finish():
            core.save_json(core.BASE/'smoke-result.json',{'interface':'ok','version':'1.2','engine':'Qt','frozen':bool(getattr(sys,'frozen',False)),'opacity':window.windowOpacity(),'icon_loaded':not window.windowIcon().isNull(),'pages':window.pages.count(),'profiles':len(window.games),'logs':str(core.DATA/'logs')})
            window.close()
        QTimer.singleShot(1500,finish)
    sys.exit(app.exec())
