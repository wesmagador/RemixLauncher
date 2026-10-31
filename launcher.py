import os
import queue
import subprocess
import tempfile
import threading
import uuid
import shutil
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
import remix_core as core

class Launcher:
    def __init__(self, window):
        self.window = window
        self.events = queue.Queue()
        self.busy = False
        self.config = core.DATA / 'jogos.json'
        self.games = core.read_json(self.config, [{'id': 'ac1', 'name': "Assassin’s Creed — Director’s Cut", 'exe': ''}])
        window.title('RTX Remix Launcher')
        window.geometry('960x700')
        window.minsize(820, 620)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=9)
        style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'))
        main = ttk.Frame(window, padding=24)
        main.pack(fill='both', expand=True)
        ttk.Label(main, text='RTX Remix Launcher', style='Title.TLabel').pack(anchor='w')
        ttk.Label(main, text='Biblioteca de jogos • Runtime oficial • Instalação reversível').pack(anchor='w', pady=(4, 18))
        row = ttk.Frame(main)
        row.pack(fill='x')
        self.selection = tk.StringVar()
        self.combo = ttk.Combobox(row, textvariable=self.selection, state='readonly', width=58)
        self.combo.pack(side='left', fill='x', expand=True)
        self.combo.bind('<<ComboboxSelected>>', lambda e: self.show_game())
        ttk.Button(row, text='+ Adicionar jogo', command=self.add_game).pack(side='left', padx=(10, 0))
        self.path = tk.StringVar()
        ttk.Label(main, textvariable=self.path, wraplength=870).pack(anchor='w', pady=12)
        self.status = tk.StringVar()
        ttk.Label(main, textvariable=self.status, wraplength=870).pack(anchor='w')
        buttons = ttk.Frame(main)
        buttons.pack(fill='x', pady=14)
        self.actions = []
        for text, action in [('Selecionar executável', self.choose_exe), ('Baixar e instalar', lambda: self.install(False)), ('Importar ZIP', lambda: self.install(True)), ('Restaurar backup', self.restore), ('Jogar', self.play)]:
            button = ttk.Button(buttons, text=text, command=action)
            button.pack(side='left', padx=(0, 6))
            self.actions.append(button)
        ttk.Label(main, text='AC1: use AssassinsCreed_Dx9.exe. Compatibilidade experimental: o menu abrir não garante uma captura válida.', wraplength=870).pack(anchor='w', pady=(0, 10))
        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.pack(fill='x')
        self.output = tk.Text(main, bg='#151c24', fg='#dce8f4', insertbackground='white', font=('Consolas', 10), wrap='word', state='disabled')
        self.output.pack(fill='both', expand=True, pady=12)
        footer = ttk.Frame(main)
        footer.pack(fill='x')
        ttk.Button(footer, text='Abrir backups', command=self.open_backups).pack(side='left')
        ttk.Button(footer, text='Releases oficiais', command=lambda: webbrowser.open('https://github.com/NVIDIAGameWorks/rtx-remix/releases')).pack(side='left', padx=8)
        ttk.Button(footer, text='Instalar Toolkit / NVIDIA App', command=lambda: webbrowser.open('https://www.nvidia.com/en-us/software/nvidia-app/')).pack(side='left')
        self.refresh()
        self.log('Selecione o executável do AC1 para começar. Feche o jogo antes de instalar ou restaurar.\nO launcher instala o runtime; o editor Toolkit é instalado pela NVIDIA App.')
        window.after(100, self.poll)
        window.protocol('WM_DELETE_WINDOW', self.close)

    def game(self):
        index = self.combo.current()
        if index < 0:
            raise ValueError('Selecione um jogo.')
        return self.games[index]

    def refresh(self):
        index = max(0, self.combo.current())
        self.combo['values'] = [g['name'] for g in self.games]
        self.combo.current(min(index, len(self.games)-1))
        self.show_game()

    def backups(self, game):
        folder = core.DATA / 'backups' / game['id']
        return sorted([p.parent for p in folder.glob('*/manifest.json') if core.read_json(p)['status'] in ('installed', 'installing')], reverse=True)

    def show_game(self):
        game = self.game()
        self.path.set(game['exe'] or 'Executável ainda não selecionado.')
        self.status.set('Runtime instalado ou operação pendente — backup disponível.' if self.backups(game) else 'Pronto para configurar. Instalações externas não são identificadas automaticamente.')

    def log(self, message):
        self.output.configure(state='normal')
        self.output.insert('end', message + '\n')
        self.output.see('end')
        self.output.configure(state='disabled')

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == 'log': self.log(value)
            elif kind == 'error':
                self.log('ERRO: ' + value)
                messagebox.showerror('Operação não concluída', value)
            elif kind == 'done':
                self.busy = False
                self.progress.stop()
                self.combo.configure(state='readonly')
                for button in self.actions: button.configure(state='normal')
                self.show_game()
        self.window.after(100, self.poll)

    def run(self, operation):
        if self.busy: return
        self.busy = True
        self.combo.configure(state='disabled')
        for button in self.actions: button.configure(state='disabled')
        self.progress.start()
        def worker():
            try: operation(lambda text: self.events.put(('log', text)))
            except Exception as exc: self.events.put(('error', str(exc)))
            finally: self.events.put(('done', None))
        threading.Thread(target=worker, daemon=True).start()

    def add_game(self):
        if self.busy: return
        name = simpledialog.askstring('Novo jogo', 'Nome do jogo:')
        if not name: return
        import uuid
        self.games.append({'id': uuid.uuid4().hex, 'name': name, 'exe': ''})
        core.save_json(self.config, self.games)
        self.refresh()
        self.combo.current(len(self.games)-1)
        self.show_game()
        self.choose_exe()

    def choose_exe(self):
        game = self.game()
        if self.backups(game):
            messagebox.showinfo('Backup ativo', 'Restaure o backup antes de mudar o executável deste perfil.')
            return
        path = filedialog.askopenfilename(title='AC1: selecione AssassinsCreed_Dx9.exe' if game['id'] == 'ac1' else 'Executável DirectX 9 do jogo', filetypes=[('Executável Windows', '*.exe')])
        if not path: return
        try:
            arch = core.architecture(path)
            if game['id'] == 'ac1' and Path(path).name.lower() != 'assassinscreed_dx9.exe':
                raise ValueError('Para o perfil AC1, selecione AssassinsCreed_Dx9.exe.')
            if any(g['id'] != game['id'] and g['exe'] and Path(g['exe']).resolve().parent == Path(path).resolve().parent for g in self.games):
                raise ValueError('Essa pasta já pertence a outro perfil. Use o perfil existente.')
            game['exe'] = path
            core.save_json(self.config, self.games)
            self.log(f'Executável {arch}: {path}')
            self.show_game()
        except Exception as exc: messagebox.showerror('Executável inválido', str(exc))

    def install(self, local):
        game = dict(self.game())
        if not game['exe'] or not Path(game['exe']).is_file():
            messagebox.showinfo('Selecione o jogo', 'Selecione um executável existente primeiro.')
            return
        if self.backups(game):
            messagebox.showinfo('Backup ativo', 'Restaure a instalação atual antes de instalar outra versão.')
            return
        archive = filedialog.askopenfilename(filetypes=[('Runtime oficial ZIP', '*.zip')]) if local else None
        if local and not archive: return
        def operation(log):
            arch = core.architecture(game['exe'])
            package = archive or core.download_runtime(arch, log)
            core.DATA.mkdir(parents=True, exist_ok=True)
            stage = core.DATA / ('runtime-' + uuid.uuid4().hex)
            stage.mkdir()
            try:
                log('Validando e extraindo runtime...')
                runtime = core.unpack_runtime(package, stage, arch)
                log('Criando backup antes de alterar o jogo...')
                core.install(game, runtime, core.DATA / 'backups' / game['id'], log)
            finally:
                if stage.resolve().parent == core.DATA.resolve():
                    shutil.rmtree(stage)
            log('Pronto. Inicie o jogo e teste Alt + X. O runtime não garante compatibilidade do jogo.')
        self.run(operation)

    def restore(self):
        backups = self.backups(self.game())
        if not backups:
            messagebox.showinfo('Backups', 'Nenhuma instalação ativa deste launcher.')
            return
        self.run(lambda log: core.restore(backups[0], log))

    def play(self):
        game = self.game()
        try:
            exe = Path(game['exe'])
            if not exe.is_file(): raise ValueError('Selecione o executável primeiro.')
            subprocess.Popen([str(exe)], cwd=exe.parent)
            self.log('Jogo iniciado. Teste Alt + X e uma captura da cena.')
        except Exception as exc: messagebox.showerror('Não foi possível iniciar', str(exc))

    def open_backups(self):
        folder = core.DATA / 'backups'
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def close(self):
        if self.busy:
            messagebox.showinfo('Operação em andamento', 'Aguarde a instalação ou restauração terminar antes de fechar.')
        else: self.window.destroy()

if __name__ == '__main__':
    Launcher(tk.Tk()).window.mainloop()
