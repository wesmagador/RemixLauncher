# Histórico de versões

## 1.2.0 — Biblioteca e diagnóstico

- Biblioteca em lista com filtro por nome e acesso à tela de cada jogo.
- Textos dos botões laterais centralizados.
- Adição de jogos por busca de instalações, busca em pasta ou seleção manual do executável.
- Descoberta de bibliotecas Steam, manifests Epic, locais de instalação do Windows e pastas comuns.
- Reconhecimento do executável DirectX 9 do Assassin’s Creed Director’s Cut.
- Logs persistentes com rotação, visualização e exportação local.
- Diagnóstico dos logs do runtime e execução opcional com log detalhado.
- Ícone incluído no executável, na janela e na barra de tarefas.
- Preservação do download automático, backup e restauração.
- Validação: oito testes automatizados e teste de inicialização do executável.

## 1.1.0 — Interface Qt e download automático corrigido

- Substituição da interface CustomTkinter por Qt, com fundo opaco.
- Seleção do pacote oficial release x86/x64, excluindo debug e symbols.
- Progresso do download e reutilização do cache validado por SHA-256 quando disponível.
- Correção de conflitos de bibliotecas no empacotamento.
- Mantidos cadastro de jogos, importação ZIP, backup, restauração e inicialização do jogo.
- Validação histórica: download completo do runtime x86, integridade do ZIP, conferência visual da interface e teste de inicialização do executável.

## 1.0.0 — Prévia inicial

- Interface escura inicial em CustomTkinter, com perfil do AC1.
- Cadastro de vários jogos e seleção de executáveis.
- Instalação do runtime, importação de ZIP e detecção de arquitetura.
- Backup dos arquivos afetados, restauração e reversão em caso de falha.
- Executável portátil com Python incorporado.
- Limitações conhecidas: transparência em alguns sistemas e falha na escolha do download quando a release contém múltiplos tipos de pacote. Corrigidas na 1.1.0.

## Sobre os arquivos históricos

Os executáveis 1.0.0 e 1.1.0 foram preservados das entregas locais anteriores. O versionamento Git começou depois dessas compilações; por isso, o código-fonte do commit associado às tags históricas não representa exatamente o código usado para compilar esses dois binários. As notas descrevem o comportamento conhecido e as verificações feitas em cada entrega. Builds intermediários de tentativa e diagnóstico não são versões de uso.

Os releases não incluem jogos, runtime NVIDIA, dependências separadas, logs, configurações pessoais ou backups. O launcher baixa o runtime oficial durante a instalação. A compatibilidade do AC1 com Remix continua experimental.
