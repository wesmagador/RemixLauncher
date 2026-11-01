"""Anexa o instalador à release do aplicativo, sem substituir a edição portátil."""
import hashlib
import json
import urllib.request
from urllib.parse import quote
import publish_releases as releases

def main():
    token=releases.credentials()
    def request(url,method='GET',data=None,binary=False):
        headers={'Authorization':'Bearer '+token,'User-Agent':'RemixLauncher-installer-publisher','Accept':'application/vnd.github+json'}
        if data is not None:headers['Content-Type']='application/octet-stream' if binary else 'application/json'
        body=data if binary else (json.dumps(data).encode() if data is not None else None)
        with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers,method=method),timeout=240) as response:return json.load(response)
    release=request(releases.API+'/releases/tags/v1.2.0')
    path=releases.ROOT/'dist/installer/RemixLauncher-Setup-1.2.0.exe'
    checksum=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n').encode()
    (path.parent/'RemixLauncher-Setup-1.2.0-SHA256.txt').write_bytes(checksum)
    assets={a['name']:a for a in request(releases.API+f'/releases/{release["id"]}/assets')}
    upload=release['upload_url'].split('{',1)[0]
    for name,content in [(path.name,path.read_bytes()),('RemixLauncher-Setup-1.2.0-SHA256.txt',checksum)]:
        if name in assets:
            asset=assets[name]
            if asset['size']!=len(content) or asset.get('digest') not in (None,'sha256:'+hashlib.sha256(content).hexdigest()):raise RuntimeError('Arquivo remoto diferente: '+name)
            print('Verificado: '+name,flush=True)
        else:
            asset=request(upload+'?name='+quote(name),'POST',content,True)
            assert asset['size']==len(content)
            print('Enviado: '+name,flush=True)
    marker='### Instalador Windows'
    if marker not in release['body']:
        notes='\n\n'+marker+'\n\nTambém disponível **RemixLauncher-Setup-1.2.0.exe**: assistente em português, instalação por usuário sem administrador, atalho no menu Iniciar, atalho opcional na área de trabalho e desinstalador.\n\nReinstalar preserva a pasta `dados`. Desinstalar preserva dados/backups e não altera os jogos. Para desfazer o runtime em um jogo, use Restaurar no launcher antes. A edição portátil não é migrada automaticamente; feche os aplicativos e copie a pasta `dados` se desejar migrar.\n\nVerificado em pasta isolada: instalação, reinstalação, abertura do launcher e desinstalação com backup preservado. SHA-256 do instalador no arquivo específico anexado.'
        request(releases.API+f'/releases/{release["id"]}','PATCH',{'body':release['body']+notes})
    print(release['html_url'])

if __name__=='__main__':main()
