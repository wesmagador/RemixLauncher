"""Publica os binários preservados no GitHub usando o Git Credential Manager.

Não salva nem imprime credenciais. Execute apenas para publicar releases.
"""
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = 'wesmagador/RemixLauncher'
API = 'https://api.github.com/repos/' + REPO

RELEASES = [
    ('v1.0.0', 'RemixLauncher.exe', True, 'Prévia inicial', '''Primeira versão portátil do launcher, com interface CustomTkinter, perfil do AC1, cadastro de jogos, instalação/importação do runtime, backup e restauração.

**Limitações conhecidas:** a interface pode ficar transparente e o download automático pode falhar na seleção de pacotes. Para uso atual, prefira a versão 1.2.0. Esta versão está preservada como prévia histórica.'''),
    ('v1.1.0', 'RemixLauncher-Atualizacao.exe', False, 'Interface Qt e download automático', '''- Interface refeita em Qt, com fundo opaco.
- Download automático corrigido: seleciona somente o pacote release da arquitetura do jogo.
- Progresso do download e cache validado por SHA-256 quando fornecido pelo GitHub.
- Corrigidos conflitos de DLLs do empacotamento.
- Mantidos cadastro de jogos, importação ZIP, backup, restauração e botão Jogar.

Verificação histórica: runtime x86 baixado e validado, interface conferida e executável iniciado sem erro.'''),
    ('v1.2.0', 'RemixLauncher-1.2.exe', False, 'Biblioteca, descoberta de jogos e logs', '''- Biblioteca em lista com filtro; clicar no jogo abre seus controles.
- Botões laterais centralizados.
- Menu Adicionar jogo: buscar instalados, buscar em pasta ou selecionar .exe manualmente.
- Descoberta Steam/Epic/registro do Windows/pastas comuns e seleção do DX9 para AC1.
- Logs persistentes da aplicação com rotação.
- Visualizador de logs do runtime, diagnóstico e exportação local.
- Execução opcional com logs detalhados e registro do encerramento do jogo.
- Ícone corrigido na aplicação, janela e barra de tarefas.
- Backup e restauração preservados.

Validação: oito testes automatizados passaram; o EXE foi iniciado e encerrado sem erro, com ícone carregado e duas telas disponíveis.'''),
]

def credentials():
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True, check=True)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not fields.get('password'):
        raise RuntimeError('Git Credential Manager não forneceu autenticação para o GitHub.')
    return fields['password']

def main():
    token = credentials()
    def request(url, method='GET', payload=None, binary=False):
        headers = {'Authorization': 'Bearer '+token, 'User-Agent': 'RemixLauncher-release-publisher', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        if payload is not None:
            headers['Content-Type'] = 'application/octet-stream' if binary else 'application/json'
        body = payload if binary else (json.dumps(payload).encode() if payload is not None else None)
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method), timeout=240) as response:
            return json.load(response)
    # Consultar o destino antes de qualquer publicação.
    repository = request(API)
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    existing = {r['tag_name']:r for r in request(API+'/releases?per_page=100')}
    folder = ROOT/'release-artifacts'
    folder.mkdir(exist_ok=True)
    for tag, filename, prerelease, title, changes in RELEASES:
        source = ROOT/'dist'/filename
        if not source.is_file():raise FileNotFoundError(source)
        asset_name = 'RemixLauncher-'+tag[1:]+'.exe'
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        checksum = f'{sha}  {asset_name}\n'.encode()
        historical = '\n\n**Proveniência histórica:** binário preservado de entrega anterior ao primeiro commit Git. O código-fonte associado à tag não corresponde exatamente à compilação histórica.' if tag != 'v1.2.0' else ''
        notes = changes + historical + '\n\n**Uso:** baixe o `.exe` e execute no Windows. Não requer Python instalado. Mantenha a pasta `dados` junto ao executável para preservar a biblioteca e os backups. O runtime NVIDIA é baixado pelo launcher e não está incluído. AC1 continua com compatibilidade experimental.\n\nO arquivo SHA256SUMS permite conferir a integridade do download.'
        (folder/(tag+'-notes.md')).write_text(notes,encoding='utf-8')
        (folder/(tag+'-SHA256SUMS.txt')).write_bytes(checksum)
        release = existing.get(tag)
        if release is None:
            release = request(API+'/releases','POST',{'tag_name':tag,'target_commitish':commit,'name':tag+' — '+title,'body':notes,'draft':False,'prerelease':prerelease,'make_latest':'true' if tag=='v1.2.0' else 'false'})
        upload = release['upload_url'].split('{',1)[0]
        assets={a['name']:a for a in request(API+f'/releases/{release["id"]}/assets')}
        from urllib.parse import quote
        for name, content in [(asset_name,source.read_bytes()),('SHA256SUMS.txt',checksum)]:
            if name in assets:
                print(f'{tag}: arquivo já existente, preservado: {name}',flush=True)
                continue
            request(upload+'?name='+quote(name),'POST',content,True)
            print(f'{tag}: enviado {name}',flush=True)
        print('RELEASE '+release['html_url'],flush=True)

if __name__=='__main__':main()
