"""Interface desktop do Remix Launcher."""
import queue
import sys
import tkinter as tk
import webbrowser
import customtkinter as ctk
from customtkinter.windows.widgets.core_rendering import DrawEngine
import remix_core as core
from launcher import Launcher

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')
# Desenho vetorial: não depende da fonte privada de formas no Windows.
DrawEngine.preferred_drawing_method = 'polygon_shapes'

def force_opaque(window):
    """Desativa backdrop/acrylic no HWND desta janela, sem mudar configurações do sistema."""
    window.attributes('-alpha', 1.0)
    window.attributes('-transparentcolor', '')
    if sys.platform != 'win32':
        return
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
    class Accent(ctypes.Structure):
        _fields_ = [('state', ctypes.c_int), ('flags', ctypes.c_int), ('color', ctypes.c_uint), ('animation', ctypes.c_int)]
    class Composition(ctypes.Structure):
        _fields_ = [('attribute', ctypes.c_int), ('data', ctypes.c_void_p), ('size', ctypes.c_size_t)]
    accent = Accent(0, 0, 0, 0)
    data = Composition(19, ctypes.addressof(accent), ctypes.sizeof(accent))
    try:
        user32.SetWindowCompositionAttribute(wintypes.HWND(hwnd), ctypes.byref(data))
        for attribute, value in [(38, 1), (1029, 0), (20, 1), (2, 1)]:
            setting = ctypes.c_int(value)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), attribute, ctypes.byref(setting), ctypes.sizeof(setting))
        class Margins(ctypes.Structure):
            _fields_ = [(name, ctypes.c_int) for name in ('left', 'right', 'top', 'bottom')]
        margins = Margins(0, 0, 0, 0)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd), ctypes.byref(margins))
        class BlurBehind(ctypes.Structure):
            _fields_ = [('flags', wintypes.DWORD), ('enable', wintypes.BOOL), ('region', wintypes.HRGN), ('transition', wintypes.BOOL)]
        blur = BlurBehind(1, False, None, False)
        ctypes.windll.dwmapi.DwmEnableBlurBehindWindow(wintypes.HWND(hwnd), ctypes.byref(blur))
        # Limpar color-key/alpha que podem ser aplicados por personalizadores de janelas.
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        style = user32.GetWindowLongW(wintypes.HWND(hwnd), -20)
        user32.SetWindowLongW(wintypes.HWND(hwnd), -20, (style | 0x80000) & ~0x20)
        user32.SetLayeredWindowAttributes(wintypes.HWND(hwnd), 0, 255, 2)
        user32.RedrawWindow(wintypes.HWND(hwnd), None, None, 0x185)
    except (AttributeError, OSError):
        pass
BG = '#0c1015'
PANEL = '#141a22'
MUTED = '#91a0b2'
GREEN = '#b5f36b'

class GamePicker(ctk.CTkOptionMenu):
    def current(self, index=None):
        if index is not None:
            self.set(self.cget('values')[index])
            return index
        try: return self.cget('values').index(self.get())
        except ValueError: return -1

    def __setitem__(self, key, value):
        self.configure(**{key: value})

    def configure(self, **kwargs):
        if kwargs.get('state') == 'readonly': kwargs['state'] = 'normal'
        super().configure(**kwargs)

class ModernLauncher(Launcher):
    def __init__(self, window):
        self.window = window
        self.events = queue.Queue()
        self.busy = False
        self.config = core.DATA / 'jogos.json'
        self.games = core.read_json(self.config, [{'id': 'ac1', 'name': 'Assassin’s Creed — Director’s Cut', 'exe': ''}])
        window.title('Remix Launcher')
        window.geometry('1180x820')
        window.minsize(1080, 780)
        window.configure(fg_color=BG)
        window.grid_columnconfigure(1, weight=1)
        window.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(window, width=230, corner_radius=0, fg_color='#10151c')
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_propagate(False)
        self.label(sidebar, 'R /', size=34, color=GREEN, bold=True).pack(anchor='w', padx=26, pady=(32, 0))
        self.label(sidebar, 'REMIX LAUNCHER', size=16, bold=True).pack(anchor='w', padx=26, pady=(0, 36))
        self.label(sidebar, 'WORKSPACE', size=10, color=MUTED, bold=True).pack(anchor='w', padx=26, pady=(0, 12))
        ctk.CTkButton(sidebar, text='▦   Biblioteca', anchor='w', height=44, fg_color='#253222', text_color=GREEN, hover_color='#2d4027').pack(fill='x', padx=18)
        ctk.CTkButton(sidebar, text='+   Adicionar jogo', anchor='w', height=44, fg_color='transparent', hover_color=PANEL, command=self.add_game).pack(fill='x', padx=18, pady=8)
        ctk.CTkButton(sidebar, text='↶   Pasta de backups', anchor='w', height=44, fg_color='transparent', hover_color=PANEL, command=self.open_backups).pack(fill='x', padx=18)
        bottom = ctk.CTkFrame(sidebar, fg_color='transparent')
        bottom.pack(side='bottom', fill='x', padx=22, pady=28)
        self.label(bottom, 'SEU JOGO. NOVA LUZ.', size=11, color=GREEN, bold=True).pack(anchor='w')
        self.label(bottom, 'Runtime RTX Remix\nBackups locais e reversíveis', size=11, color=MUTED).pack(anchor='w', pady=8)
        ctk.CTkButton(bottom, text='NVIDIA App / Toolkit ↗', fg_color='transparent', border_width=1, border_color='#303b48', height=34, command=lambda: webbrowser.open('https://www.nvidia.com/en-us/software/nvidia-app/')).pack(fill='x', pady=(8, 0))
        main = ctk.CTkFrame(window, fg_color='transparent')
        main.grid(row=0, column=1, sticky='nsew', padx=32, pady=28)
        self.label(main, 'Biblioteca', size=28, bold=True).pack(anchor='w')
        self.label(main, 'Prepare, experimente e restaure seus jogos em um só lugar.', size=13, color=MUTED).pack(anchor='w', pady=(2, 20))
        picker_row = ctk.CTkFrame(main, fg_color='transparent')
        picker_row.pack(fill='x', pady=(0, 16))
        self.combo = GamePicker(picker_row, values=['Carregando...'], height=38, corner_radius=8, fg_color=PANEL, button_color='#273240', button_hover_color='#354354', font=('Segoe UI', 13), command=lambda _: self.show_game())
        self.combo.pack(side='left', fill='x', expand=True)
        hero = ctk.CTkFrame(main, fg_color='#1a2526', corner_radius=16, height=180)
        hero.pack(fill='x')
        hero.pack_propagate(False)
        art = tk.Canvas(hero, width=270, height=180, bg='#1a2526', highlightthickness=0)
        art.place(relx=1, x=-280, y=0)
        for x in range(0, 280, 28): art.create_line(x, 0, x, 180, fill='#223332')
        for y in range(0, 190, 28): art.create_line(0, y, 280, y, fill='#223332')
        art.create_oval(110, 15, 250, 155, outline='#547248', width=1)
        art.create_oval(130, 35, 230, 135, outline='#7d9d57', width=1)
        for x, h in [(12, 45), (42, 73), (75, 55), (105, 93), (145, 65), (180, 110), (220, 64)]:
            art.create_rectangle(x, 180-h, x+25, 180, fill='#2d4036', outline='#668852')
            art.create_polygon(x-3, 180-h, x+12, 162-h, x+28, 180-h, fill='#3d5540', outline='#668852')
        info = ctk.CTkFrame(hero, fg_color='transparent')
        info.pack(side='left', fill='both', expand=True, padx=24, pady=20)
        self.badge = self.label(info, 'PRIMEIRO TESTE  /  DIRECTX 9', size=10, color=GREEN, bold=True)
        self.badge.pack(anchor='w')
        self.game_title = self.label(info, 'Assassin’s Creed', size=30, bold=True)
        self.game_title.pack(anchor='w', pady=(8, 0))
        self.subtitle = self.label(info, 'Director’s Cut • Perfil experimental', size=13, color='#b0c0bd')
        self.subtitle.pack(anchor='w', pady=(2, 14))
        self.label(info, 'Path tracing começa com uma boa captura.', size=12, color='#b0c0bd').pack(anchor='w')
        self.status = tk.StringVar()
        self.path = tk.StringVar()
        self.label(main, textvariable=self.status, size=12, color=GREEN, wraplength=820).pack(anchor='w', pady=(16, 6))
        self.label(main, textvariable=self.path, size=11, color=MUTED, wraplength=820).pack(anchor='w')
        controls = ctk.CTkFrame(main, fg_color='transparent')
        controls.pack(fill='x', pady=16)
        self.actions = []
        items = [('Selecionar .exe', self.choose_exe, False), ('Instalar RTX Remix', lambda: self.install(False), True), ('Importar ZIP', lambda: self.install(True), False), ('Restaurar', self.restore, False), ('▶  Jogar', self.play, False)]
        for i, (title, action, primary) in enumerate(items):
            controls.grid_columnconfigure(i, weight=1)
            button = ctk.CTkButton(controls, text=title, command=action, height=42, width=120, corner_radius=8, fg_color=GREEN if primary else '#202a36', hover_color='#97d34c' if primary else '#303d4c', text_color='#15200e' if primary else '#e4eaf1', font=('Segoe UI', 12, 'bold'))
            button.grid(row=0, column=i, sticky='ew', padx=(0, 7 if i < 4 else 0))
            self.actions.append(button)
        tips = ctk.CTkFrame(main, fg_color=PANEL, corner_radius=10)
        tips.pack(fill='x', pady=(0, 15))
        self.label(tips, '01  Selecione o jogo       →       02  Instale com backup       →       03  Abra e teste Alt + X', size=12, color='#c6d1de').pack(anchor='w', padx=16, pady=13)
        log_header = ctk.CTkFrame(main, fg_color='transparent')
        log_header.pack(fill='x')
        self.label(log_header, 'ATIVIDADE', size=10, color=MUTED, bold=True).pack(side='left')
        ctk.CTkButton(log_header, text='Releases oficiais ↗', width=130, height=24, fg_color='transparent', text_color=MUTED, hover_color=PANEL, command=lambda: webbrowser.open('https://github.com/NVIDIAGameWorks/rtx-remix/releases')).pack(side='right')
        self.progress = ctk.CTkProgressBar(main, height=3, progress_color=GREEN, fg_color='#27303c', mode='indeterminate')
        self.progress.pack(fill='x', pady=(6, 10))
        self.progress.set(0)
        self.output = ctk.CTkTextbox(main, fg_color='#10161e', text_color='#b6c4d3', corner_radius=10, font=('Consolas', 11), wrap='word', height=120, state='disabled')
        self.output.pack(fill='both', expand=True)
        self.label(main, 'Feche o jogo para instalar ou restaurar. AC1: compatibilidade experimental.', size=11, color=MUTED).pack(anchor='w', pady=(10, 0))
        self.refresh()
        self.log('Tudo pronto. Selecione o executável do jogo para começar.\nOs arquivos afetados serão salvos antes da instalação do runtime.')
        window.after(100, self.poll)
        window.protocol('WM_DELETE_WINDOW', self.close)
        window.after(100, lambda: force_opaque(window))
        window.after(1200, lambda: force_opaque(window))
        window.bind('<FocusIn>', lambda event: window.after(200, lambda: force_opaque(window)) if event.widget == window else None, add='+')

    def label(self, parent, text=None, size=13, color='#eef2f6', bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=text or '', text_color=color, font=('Segoe UI', size, 'bold' if bold else 'normal'), justify='left', **kwargs)

    def show_game(self):
        super().show_game()
        game = self.game()
        ac1 = game['id'] == 'ac1'
        self.game_title.configure(text='Assassin’s Creed' if ac1 else game['name'][:32])
        self.subtitle.configure(text='Director’s Cut • Perfil experimental' if ac1 else 'Perfil personalizado • Compatibilidade a verificar')
        self.badge.configure(text='PRIMEIRO TESTE  /  DIRECTX 9' if ac1 else 'BIBLIOTECA  /  RUNTIME RTX REMIX')

if __name__ == '__main__':
    root = ctk.CTk()
    app = ModernLauncher(root)
    if '--smoke-test' in sys.argv:
        def finish():
            core.save_json(core.BASE / 'smoke-result.json', {'interface': 'ok', 'profiles': len(app.games), 'frozen': bool(getattr(sys, 'frozen', False))})
            root.destroy()
        root.after(1500, finish)
    root.mainloop()
