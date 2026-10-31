"""Instalação reversível do runtime, sem dependências externas."""
import hashlib
import json
import shutil
import struct
import urllib.request
import uuid
import zipfile
import sys
import re
from datetime import datetime
from pathlib import Path

BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA = BASE / 'dados'
API = 'https://api.github.com/repos/NVIDIAGameWorks/rtx-remix/releases/latest'

def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default

def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def architecture(exe):
    with open(exe, 'rb') as f:
        if f.read(2) != b'MZ':
            raise ValueError('Selecione um executável Windows válido.')
        f.seek(0x3c)
        offset = struct.unpack('<I', f.read(4))[0]
        f.seek(offset)
        if f.read(4) != b'PE\0\0':
            raise ValueError('Cabeçalho PE inválido.')
        machine = struct.unpack('<H', f.read(2))[0]
    if machine not in (0x14c, 0x8664):
        raise ValueError('Somente jogos Windows x86 e x64 são suportados.')
    return 'x86' if machine == 0x14c else 'x64'

def select_asset(release, arch):
    # GitHub publica também debug, debugoptimized e symbols para a mesma arquitetura.
    pattern = re.compile(r'^rtx-remix-for-' + re.escape(arch) + r'-games-release-.+(?<!-symbols)\.zip$', re.I)
    candidates = [a for a in release['assets'] if pattern.fullmatch(a['name'])]
    if len(candidates) != 1:
        raise ValueError(f'Pacote release {arch} não identificado na versão {release.get("tag_name", "desconhecida")}.')
    return candidates[0]

def download_runtime(arch, log=print):
    log('Consultando a versão oficial mais recente no GitHub...')
    request = urllib.request.Request(API, headers={'User-Agent': 'RemixLauncher', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=40) as response:
        release = json.load(response)
    asset = select_asset(release, arch)
    target = DATA / 'downloads' / asset['name']
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix('.part')
    expected = asset.get('digest', '') or ''
    if target.is_file() and target.stat().st_size == asset['size'] and expected.startswith('sha256:') and digest(target) == expected.split(':', 1)[1]:
        log('Pacote já baixado e SHA-256 validado. Usando cache local.')
        return target
    log(f"Baixando {release['tag_name']}: {asset['name']}")
    req = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'RemixLauncher'})
    try:
        with urllib.request.urlopen(req, timeout=90) as response, open(part, 'wb') as out:
            received = 0
            last_percent = -5
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
                received += len(chunk)
                percent = int(received * 100 / max(asset['size'], 1))
                if percent >= last_percent + 5:
                    log(f'Download {percent}% — {received / 1024**2:.0f} / {asset["size"] / 1024**2:.0f} MB')
                    last_percent = percent
        if part.stat().st_size != asset['size']:
            raise ValueError('Download incompleto.')
        if expected.startswith('sha256:') and digest(part) != expected.split(':', 1)[1]:
            raise ValueError('SHA-256 do download não corresponde ao GitHub.')
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)
    return target

def unpack_runtime(archive, destination, arch):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        total = sum(i.file_size for i in z.infolist())
        if total > 20 * 1024**3:
            raise ValueError('ZIP excede o limite de 20 GB descompactados.')
        for entry in z.infolist():
            name = entry.filename.replace('\\', '/')
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or ':' in name or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP contém caminho inseguro ou link simbólico.')
        z.extractall(destination)
    roots = [p.parent for p in destination.rglob('d3d9.dll') if p.parent.name not in ('.trex', '.trex_arm64')]
    roots = [p for p in roots if (p / '.trex').is_dir()] if arch == 'x86' else [p for p in roots if (p / 'd3d9_x64.dll').exists()]
    if len(roots) != 1:
        raise ValueError(f'O ZIP não contém um runtime {arch} reconhecido. Use o pacote completo oficial.')
    if architecture(roots[0] / 'd3d9.dll') != arch:
        raise ValueError('Arquitetura da DLL incompatível com o jogo.')
    return roots[0]

def checked_path(root, relative):
    root = Path(root).resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root) or path == root:
        raise ValueError('Caminho fora da pasta do jogo.')
    # Não escrever através de junctions ou links, mesmo dentro da pasta.
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError(f'Link/junction não permitido: {parent}')
    return path

def install(game, runtime, backup_root, log=print):
    exe = Path(game['exe']).resolve()
    root = exe.parent
    backup = Path(backup_root) / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    files = sorted(p for p in Path(runtime).rglob('*') if p.is_file())
    if not files:
        raise ValueError('Runtime vazio.')
    entries = []
    for source in files:
        rel = source.relative_to(runtime).as_posix()
        target = checked_path(root, rel)
        if target.exists() and not target.is_file():
            raise ValueError(f'Destino não é um arquivo: {rel}')
        entries.append({'path': rel, 'existed': target.exists(), 'installed_sha256': digest(source)})
    manifest = {'game': game, 'root': str(root), 'status': 'preparing', 'files': entries, 'created_dirs': []}
    backup.mkdir(parents=True)
    # Todo o backup termina antes da primeira alteração no jogo.
    for entry in entries:
        if entry['existed']:
            src = checked_path(root, entry['path'])
            dst = backup / 'original' / entry['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            entry['original_sha256'] = digest(dst)
    for entry in entries:
        parent = checked_path(root, entry['path']).parent
        while parent != root and not parent.exists():
            relative = parent.relative_to(root).as_posix()
            if relative not in manifest['created_dirs']:
                manifest['created_dirs'].append(relative)
            parent = parent.parent
    manifest['status'] = 'installing'
    save_json(backup / 'manifest.json', manifest)
    try:
        for entry in entries:
            target = checked_path(root, entry['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(runtime) / entry['path'], target)
        manifest['status'] = 'installed'
        save_json(backup / 'manifest.json', manifest)
    except Exception:
        log('Instalação interrompida. Revertendo os arquivos...')
        restore(backup, log)
        raise
    log(f'Instalado. Backup: {backup}')
    return backup

def restore(backup, log=print):
    backup = Path(backup)
    manifest = read_json(backup / 'manifest.json')
    root = Path(manifest['root'])
    if manifest['status'] == 'restored':
        raise ValueError('Esse backup já foi restaurado.')
    # Validar todos os originais antes de modificar qualquer arquivo.
    for entry in manifest['files']:
        checked_path(root, entry['path'])
        if entry['existed']:
            original = checked_path(backup / 'original', entry['path'])
            if not original.is_file() or digest(original) != entry['original_sha256']:
                raise ValueError(f"Backup ausente ou corrompido: {entry['path']}")
    # Preservar também arquivos alterados depois da instalação.
    recovery = backup / 'antes-de-restaurar' / uuid.uuid4().hex[:8]
    for entry in manifest['files']:
        target = checked_path(root, entry['path'])
        if target.is_file():
            dst = recovery / entry['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, dst)
    for entry in manifest['files']:
        target = checked_path(root, entry['path'])
        if entry['existed']:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / 'original' / entry['path'], target)
        else:
            target.unlink(missing_ok=True)
    for relative in sorted(manifest.get('created_dirs', []), key=len, reverse=True):
        directory = checked_path(root, relative)
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    manifest['status'] = 'restored'
    save_json(backup / 'manifest.json', manifest)
    log('Arquivos anteriores restaurados. Capturas e outros arquivos pessoais foram preservados.')
