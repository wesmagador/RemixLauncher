"""Descoberta local de jogos e diagnóstico, sem alterar instalações."""
import os
import re
import json
from pathlib import Path
from datetime import datetime
import logging
import struct
from logging.handlers import RotatingFileHandler
import remix_core as core

def app_logger():
    log = logging.getLogger('remix-launcher')
    if not log.handlers:
        folder = core.DATA / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'launcher.log', maxBytes=2*1024*1024, backupCount=4, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log

def installed_roots():
    roots = set()
    def add(path):
        if path and Path(path).is_dir(): roots.add(Path(path).resolve())
    for drive in 'CDEFGHIJ':
        for name in ('Games', 'Jogos', 'Jogos Alternativos', 'SteamLibrary/steamapps/common', 'Program Files (x86)/Steam/steamapps/common', 'Program Files/Epic Games', 'XboxGames', 'GOG Games', 'Program Files (x86)/Ubisoft/Ubisoft Game Launcher/games'):
            add(f'{drive}:/{name}')
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for branch in (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                try:
                    with winreg.OpenKey(hive, branch) as key:
                        for index in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                with winreg.OpenKey(key, winreg.EnumKey(key,index)) as sub:
                                    add(winreg.QueryValueEx(sub,'InstallLocation')[0])
                            except OSError: pass
                except OSError: pass
        steam_paths=[]
        for branch, value in [(r'Software\Valve\Steam','SteamPath'), (r'SOFTWARE\WOW6432Node\Valve\Steam','InstallPath')]:
            for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive,branch) as key: steam_paths.append(Path(winreg.QueryValueEx(key,value)[0]))
                except OSError:pass
        for steam in steam_paths:
            add(steam/'steamapps/common')
            vdf=steam/'steamapps/libraryfolders.vdf'
            if vdf.is_file():
                for path in re.findall(r'"path"\s+"([^"]+)"',vdf.read_text(encoding='utf-8',errors='replace')):
                    add(Path(path.replace('\\\\','\\'))/'steamapps/common')
    except ImportError:pass
    epic=Path(os.environ.get('PROGRAMDATA','C:/ProgramData'))/'Epic/EpicGamesLauncher/Data/Manifests'
    if epic.is_dir():
        for item in epic.glob('*.item'):
            try:add(json.loads(item.read_text(encoding='utf-8')).get('InstallLocation'))
            except (OSError,ValueError):pass
    return sorted(roots)

def scan_games(roots=None, log=lambda s:None):
    results={}
    skip={'windows','node_modules','.git','vendor','redist','_commonredist','support','uninstall','installer','detection','register','readme','.trex','.trex_arm64','rtx-remix'}
    for root in roots if roots is not None else installed_roots():
        root=Path(root).resolve()
        log(f'Buscando executáveis em {root}')
        visited=0
        for current, dirs, files in os.walk(root,followlinks=False):
            visited+=1
            depth=len(Path(current).relative_to(root).parts)
            dirs[:]=[d for d in dirs if d.lower() not in skip and not (Path(current)/d).is_symlink() and not (hasattr(Path,'is_junction') and (Path(current)/d).is_junction())] if depth<4 and visited<8000 else []
            if visited>8000:break
            ac1=any(n.lower()=='assassinscreed_dx9.exe' for n in files)
            if ac1:dirs[:]=[]
            for name in files:
                lower=name.lower()
                if ac1 and lower!='assassinscreed_dx9.exe':continue
                if not lower.endswith('.exe') or any(s in lower for s in ('unins','setup','crash','report','helper','redist','install','remix','update','benchmark','testapp','registration','detection')):continue
                exe=Path(current)/name
                try:
                    arch=core.architecture(exe)
                    label='Assassin’s Creed — Director’s Cut' if ac1 else exe.parent.name
                    results[str(exe.resolve()).casefold()]={'name':label,'exe':str(exe.resolve()),'arch':arch}
                except (OSError,ValueError,struct.error):
                    # Executáveis truncados/não PE não são candidatos.
                    continue
    return sorted(results.values(),key=lambda g:(g['name'].lower(),g['exe'].lower()))

def runtime_logs(exe):
    if not exe or not Path(exe).is_file():return []
    root=Path(exe).parent
    files=set(root.glob('*.log'))
    for relative in ('rtx-remix/logs','.trex','.trex/logs'):
        folder=root/relative
        if folder.is_dir():
            files.update(folder.glob('*.log'))
    return sorted(files,key=lambda p:p.stat().st_mtime,reverse=True)

def read_tail(path, limit=160000):
    with open(path,'rb') as stream:
        stream.seek(0,2)
        stream.seek(max(0,stream.tell()-limit))
        return stream.read().decode('utf-8',errors='replace')

def diagnosis(exe):
    lines=['Diagnóstico local — '+datetime.now().strftime('%d/%m/%Y %H:%M:%S'), 'Executável: '+(exe or 'não selecionado')]
    logs=runtime_logs(exe)
    lines.append(f'Logs encontrados: {len(logs)}')
    text='\n'.join(read_tail(p) for p in logs).lower()
    if 'dlss-nr not available' in text:
        lines.append('RECURSO: DLSS-NR indisponível no hardware/plataforma desta sessão. Isso não significa que todo DLSS esteja indisponível; não atribui por si só os artefatos a esse recurso.')
    if 'not detecting a valid camera' in text:
        lines.append('CÂMERA: o runtime relata que não detectou uma câmera válida. Isso pode impedir a reconstrução correta do cenário; não comprova que todos os artefatos tenham essa causa.')
    if 'failed to recreate swap chain' in text:
        lines.append('APRESENTAÇÃO: falha ao recriar swap chain. Teste o modo janela e evite alternar resolução/Alt+Tab durante o teste; compare com o jogo sem Remix.')
    if 'non-primary, non-raytraced render target' in text:
        lines.append('RENDERIZAÇÃO: existem chamadas em render targets não capturados para ray tracing; há fallback para rasterização.')
    if not logs:lines.append('Execute o jogo uma vez com Remix e atualize esta tela para procurar logs.')
    lines.extend(['', 'AC1: compatibilidade experimental. Instalar o runtime não adapta automaticamente os shaders do jogo.', 'Teste uma mudança por vez, em uma cena jogável:', '1. Compare com o jogo sem Remix usando Restaurar (feche o jogo primeiro). Reinstale para continuar os testes.', '2. Alt + X → Developer → Game Setup: confira a câmera e a classificação de UI/céu.', '3. Shader-based Vertex Capture pode ajudar somente em jogos que ainda fornecem matrizes fixas. Teste ligado/desligado; não é correção garantida para AC1.', '4. Se o problema for ruído e não geometria, compare resolução nativa/DLSS e Ray Reconstruction nas opções gráficas.', '5. Capture uma imagem do defeito e preserve os logs desta mesma sessão.', '', 'Documentação: https://docs.omniverse.nvidia.com/kit/docs/rtx_remix/latest/docs/runtimeinterface/remix-runtimeinterface-gamesetup.html'])
    return '\n'.join(lines)
