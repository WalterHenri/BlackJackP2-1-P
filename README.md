# Peer-to-Peer Blackjack Game

Uma versão simples do jogo Blackjack (21) com networking peer-to-peer e sistema de salas, construído com Python e Pygame.

## Requisitos

- Python 3.6+
- Pygame

Instale o Pygame usando pip:

```
pip install pygame
```

## Como Jogar

O jogo segue as regras básicas do Blackjack:
- Cada jogador começa com 2 cartas
- Os jogadores decidem se querem "hit" (pedir mais uma carta) ou "stand" (ficar com as cartas atuais)
- O objetivo é chegar o mais próximo possível de 21 sem ultrapassar ("busting")
- O jogador com a mão mais próxima de 21 ao final da rodada vence

## Controles

- **Botão Hit**: Clique para pedir mais uma carta
- **Botão Stand**: Clique para parar de pedir cartas e encerrar seu turno
- Após o fim de um jogo:
  - Pressione **R** para reiniciar
  - Pressione **Q** para voltar ao menu de salas

## Sistema de Salas

O jogo agora possui um sistema de salas que permite:
- Criar salas com nomes personalizados
- Visualizar salas disponíveis
- Entrar em salas existentes
- Pesquisa automática de salas disponíveis

### Iniciando o Servidor de Salas

Antes de jogar, é necessário iniciar o servidor de salas:

```bash
python start_room_server.py
```

O servidor de salas gerencia todas as salas disponíveis e permite que os jogadores encontrem uns aos outros.

### Iniciando o Jogo

Para iniciar o jogo:

```bash
python main.py
```

## Sistema de Som e Música

O jogo possui um sistema completo de som e música:

- **Efeitos Sonoros**: Sons são reproduzidos quando cartas são distribuídas
- **Música de Fundo**: Música ambiente durante o jogo
- **Configurações**: É possível habilitar/desabilitar os sons e a música através da tela de configurações

### Adicionar Música de Fundo Personalizada

Para adicionar música de fundo ao jogo, coloque um arquivo MP3 em um dos seguintes caminhos:

```
assets/background-music.mp3
assets/bg-music.mp3
assets/music.mp3
```

O sistema tentará carregar o primeiro arquivo encontrado na ordem acima.

## Estrutura do Projeto

O projeto está dividido em vários módulos:

- `main.py` - Ponto de entrada da aplicação
- `constants.py` - Constantes e enumerações
- `card.py` - Classes para cartas e baralho
- `player.py` - Classe que representa o jogador
- `menu.py` - Interface do menu principal
- `room_menu.py` - Interface de gerenciamento de salas
- `room_client.py` - Cliente para o servidor de salas
- `room_server.py` - Servidor que gerencia as salas
- `network.py` - Gerenciamento de conexões peer-to-peer
- `renderer.py` - Renderização de elementos do jogo
- `event_handler.py` - Processamento de eventos
- `game.py` - Lógica principal do jogo
- `sound_manager.py` - Gerenciamento de sons e música
- `settings.py` - Configurações do jogo

## Resolução de Problemas

- Certifique-se de que o servidor de salas esteja em execução antes de iniciar o jogo
- Por padrão, o servidor de salas usa a porta 5001 e o jogo usa a porta 5000
- O sistema depende da descoberta correta do IP da máquina, o que pode não funcionar em algumas redes
- Se tiver problemas de conexão, verifique as configurações de firewall e certifique-se de que as portas estão abertas
- Se precisar jogar através da internet, pode ser necessário configurar o encaminhamento de portas no roteador
