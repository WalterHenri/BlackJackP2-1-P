import pygame
import sys
import os
import json
import uuid
import time
import asyncio # Adicionar import
import threading # Adicionar import novamente para a thread do WebSocket
import websockets # Adicionar import
from queue import Queue, Empty # Adicionar import novamente para a fila de envio
from pygame.locals import *
import queue # Importar queue

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.player import Player
from shared.models.game import Game
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager # Manter por enquanto, pode ser removido depois
from client.card_sprites import CardSprites
from client.player_data import get_player_balance, update_player_balance, check_player_eliminated

# Inicializar pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)

# Configurações da tela
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CARD_WIDTH = 100
CARD_HEIGHT = 150
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50


# --- Classe ServerConnection REMOVIDA --- #

# --- Fim da Classe ServerConnection --- #


# --- WebSocketClient Class --- #
class WebSocketClient:
    def __init__(self, uri, status_callback, message_queue):
        self._uri = uri
        self._status_callback = status_callback
        self._message_queue = message_queue
        self._conn = None
        self._thread = None
        self._send_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._connected = False
        self._loop = None

    def connect(self):
        if self._thread is not None and self._thread.is_alive():
            print("WebSocket thread já está rodando.")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

    def _run_async_loop(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            print(f"Erro fatal no loop async do WebSocket: {e}")
            self._connected = False
            self._status_callback("Error")
        finally:
             if self._loop:
                self._loop.close()
             self._connected = False
             print("Loop async do WebSocket finalizado.")

    async def _main_loop(self):
        while not self._stop_event.is_set():
            try:
                self._status_callback("Connecting...")
                async with websockets.connect(self._uri) as websocket:
                    self._conn = websocket
                    self._connected = True
                    self._status_callback("Connected")
                    print(f"Conectado ao WebSocket em {self._uri}")

                    # Iniciar tarefas concorrentes para enviar e receber
                    recv_task = asyncio.create_task(self._recv_loop())
                    send_task = asyncio.create_task(self._send_loop())
                    # Corrigir erro "Passing coroutines is forbidden"
                    stop_wait_task = asyncio.create_task(self._stop_event.wait()) 
                    done, pending = await asyncio.wait(
                        [recv_task, send_task, stop_wait_task], # Usar a task criada
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancelar tarefas pendentes ao sair
                    for task in pending:
                        task.cancel()
                    
                    # Verificar se saímos por causa do stop_event
                    if self._stop_event.is_set():
                         print("Stop event set, saindo do main loop.")
                         break # Sai do loop while externo
            
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
                print(f"WebSocket desconectado: {e.code} {e.reason}")
            except ConnectionRefusedError:
                print("Erro de conexão WebSocket: Conexão recusada.")
            except OSError as e: # Captura erros como [WinError 10049] ou [Errno 11001] getaddrinfo failed
                print(f"Erro de conexão WebSocket (OS): {e}")
            except Exception as e:
                print(f"Erro inesperado no main_loop WebSocket: {e}")
            finally:
                self._conn = None
                self._connected = False
                if not self._stop_event.is_set():
                    self._status_callback("Disconnected")
                    print("Tentando reconectar em 5 segundos...")
                    await asyncio.sleep(5)
                else:
                    print("Não tentando reconectar, stop event ativo.")
                    self._status_callback("Stopped")

    async def _recv_loop(self):
        while self._connected and not self._stop_event.is_set():
            try:
                message_str = await self._conn.recv()
                try:
                    message_dict = json.loads(message_str)
                    self._message_queue.put(message_dict)
                except json.JSONDecodeError:
                    print(f"Erro: Recebido JSON inválido do WebSocket: {message_str}")
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                print("Recv loop: Conexão fechada.")
                self._connected = False
                break
            except asyncio.CancelledError:
                print("Recv loop cancelado.")
                break
            except Exception as e:
                print(f"Erro no recv_loop WebSocket: {e}")
                self._connected = False
                break
        print("Recv loop finalizado.")

    async def _send_loop(self):
        while self._connected and not self._stop_event.is_set():
            try:
                # Espera por uma mensagem na fila ou pelo stop event
                get_task = asyncio.create_task(self._send_queue.get())
                stop_task = asyncio.create_task(self._stop_event.wait())
                done, pending = await asyncio.wait(
                    [get_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if stop_task in done:
                    get_task.cancel() # Cancela a espera da fila se paramos
                    print("Send loop: Stop event recebido.")
                    break

                if get_task in done:
                    message_dict = get_task.result()
                    message_str = json.dumps(message_dict)
                    await self._conn.send(message_str)
                    self._send_queue.task_done()
                else: # stop_task must be done
                     get_task.cancel()
                     break

            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                print("Send loop: Conexão fechada.")
                self._connected = False
                break
            except asyncio.CancelledError:
                print("Send loop cancelado.")
                break
            except Exception as e:
                print(f"Erro no send_loop WebSocket: {e}")
                self._connected = False
                break
        print("Send loop finalizado.")

    def send(self, message_dict):
        if not self._connected:
            print("Erro: Tentativa de enviar mensagem WebSocket sem conexão.")
            return False
        try:
            # Adiciona à fila de envio (que será processada pelo _send_loop)
            if self._loop and self._loop.is_running():
                 asyncio.run_coroutine_threadsafe(self._send_queue.put(message_dict), self._loop)
                 return True
            else:
                 print("Erro: Loop async não está rodando para enfileirar mensagem.")
                 return False
        except Exception as e:
             print(f"Erro ao enfileirar mensagem para envio: {e}")
             return False

    def is_connected(self):
        return self._connected

    def close(self):
        print("Solicitando fechamento do WebSocket...")
        self._stop_event.set() # Sinaliza para as tarefas pararem
        # Tentar acordar o _send_loop se ele estiver esperando na fila
        if self._loop and self._loop.is_running():
             asyncio.run_coroutine_threadsafe(self._send_queue.put(None), self._loop) # Envia None para desbloquear

        if self._thread is not None and self._thread.is_alive():
            print("Aguardando thread WebSocket finalizar...")
            self._thread.join(timeout=5) # Espera um pouco pela thread
            if self._thread.is_alive():
                print("Thread WebSocket não finalizou a tempo.")
        self._thread = None
        print("Fechamento do WebSocket solicitado.")

# --- Fim da Classe WebSocketClient --- #

class BlackjackClient:
    def __init__(self):
        """Inicializar o cliente do jogo"""
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Blackjack P2P")
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_view = "menu"
        self.messages = []
        self.player_name = "Player"
        self.name_input_active = True  # Iniciar com o campo de nome ativo
        self.player_balance = get_player_balance(self.player_name)
        print(f"Saldo carregado inicialmente: {self.player_balance}")
        self.player = None # Será criado ao definir nome ou conectar
        self.player_id = None # ID atribuído pelo servidor
        self.dealer = None
        self.my_server = None
        self.client_socket = None
        self.server_address = "itetech-001-site1.qtempurl.com" # Endereço base do servidor
        self.local_port = 0 # Para escuta P2P local
        self.lobby_players = [] # Inicializa a lista de jogadores do lobby
        self.websocket_client = None # Instância do novo WebSocketClient
        self.server_status = "Disconnected"
        self.current_bet = 0
        self.bet_amount = 100  # Valor inicial da aposta
        self.selected_bot_count = 1
        self.selected_bot_strategy = "random"
        self.cursor_visible = True
        self.cursor_timer = 0
        self.p2p_manager = None
        self.game = None # Instância do jogo local (para single-player)
        self.game_state = None # Estado recebido do servidor (para multiplayer)
        self.host_mode = False
        self.max_players = 8 # Definir número máximo de jogadores para criar sala

        # Novo estado para seleção de modo
        self.connection_mode = "online" # Modo padrão
        self.room_list = []
        self.room_id = ""
        self.room_id_input = ""
        self.room_id_input_active = False
        self.room_name_input = ""
        self.room_name_input_active = False
        self.password_input = ""
        self.password_input_active = False
        self.connection_mode_selection = "online"  # Modo selecionado na tela de criação/busca de sala
        self.room_browser_scroll = 0
        self.selected_room_index = -1
        self.error_message = ""
        self.success_message = ""
        self.message_timer = 0

        # Fontes
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        # Carregar sprites das cartas
        self.card_sprites = CardSprites()

        # Adicionar variável para controlar a exibição do pop-up de tutorial
        self.show_tutorial = False

        # Fila para comunicação entre thread WebSocket e thread principal Pygame
        self._message_queue = queue.Queue() # Criar a fila segura

    def start(self):
        """Iniciar o loop principal do jogo"""
        self.running = True

        while self.running:
            # Processar mensagens recebidas do WebSocket
            self.process_websocket_messages() 

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        # --- Limpeza ao Sair --- #
        # Salvar o saldo do jogador
        if self.player and hasattr(self.player, 'balance'):
            update_player_balance(self.player_name, self.player.balance)
            print(f"Salvando saldo final: {self.player_name} = {self.player.balance}")
        else: # Tenta salvar mesmo sem objeto Player, usando self.player_name e self.player_balance
             try:
                 current_balance = get_player_balance(self.player_name) # Pega o último salvo
                 if self.player_balance != current_balance: # Salva só se mudou
                     update_player_balance(self.player_name, self.player_balance)
                     print(f"Salvando saldo final (sem obj Player): {self.player_name} = {self.player_balance}")
             except Exception as e:
                 print(f"Erro ao tentar salvar saldo na saída: {e}")
            
        # Fechar conexão WebSocket
        if self.websocket_client:
            self.websocket_client.close()
            
        # Fechar Pygame
        pygame.quit()
        sys.exit()

    def process_websocket_messages(self):
        """Processa mensagens da fila segura recebidas do WebSocketClient."""
        while True: 
            try:
                message_dict = self._message_queue.get_nowait()
            except queue.Empty:
                break

            msg_type = message_dict.get("type", "").upper()
            payload = message_dict.get("payload")
            # print(f"[Queue] Processando: {msg_type}") # Log verboso
            
            handler_map = {
                "ROOMS_LIST": self.handle_rooms_list,
                "ROOM_CREATED": self.handle_room_created,
                "JOIN_SUCCESS": self.handle_join_accepted, # CORRIGIDO: Esperar JOIN_SUCCESS
                "JOIN_ERROR": self.handle_join_error,
                "NAME_SET": self.handle_name_set,
                "PLAYER_JOINED": self.handle_player_joined,
                "PLAYER_LEFT": self.handle_player_left,
                "NEW_HOST": self.handle_new_host, # Adicionado
                "ROOM_UPDATE": self.handle_room_update, # Adicionado
                "LEFT_ROOM": self.handle_left_room, # Adicionado
                "ERROR": self.handle_server_error,
                "GAME_STATE": self.handle_game_state,
                "DISCONNECTED": self.handle_server_disconnect # Mensagem interna do client
            }

            handler = handler_map.get(msg_type)
            if handler:
                 # print(f"[WebSocketClient] Chamando handler para: {msg_type}") # Log verboso
                 handler(payload)
            else:
                print(f"Tipo de mensagem do WebSocket desconhecida ou sem handler: {msg_type}")

    # --- Handlers para Mensagens WebSocket --- #
    # RESTAURADO: Handler para NAME_SET
    def handle_name_set(self, payload):
        if payload and "playerId" in payload and "name" in payload:
            self.player_id = payload["playerId"]
            self.player_name = payload["name"] # Atualiza nome local com o confirmado pelo server
            print(f"Nome '{self.player_name}' definido com ID {self.player_id}")
            self.success_message = "Conectado e nome definido!"
            self.message_timer = pygame.time.get_ticks()
            # Criar o objeto Player localmente
            # Atualizar saldo ao definir o nome
            old_balance = self.player_balance
            self.player_balance = get_player_balance(self.player_name) 
            print(f"Saldo para {self.player_name} atualizado de {old_balance} para {self.player_balance}")
            self.player = Player(self.player_name, self.player_balance, self.player_id)
        else:
            print("Erro: Payload inválido para NAME_SET")
            self.error_message = "Erro ao definir nome no servidor."
            self.message_timer = pygame.time.get_ticks()
            # Lidar com erro? Solicitar nome novamente?

    # RESTAURADO: Handler para ROOMS_LIST
    def handle_rooms_list(self, payload):
        print(f"Recebido ROOMS_LIST: {payload}")
        if isinstance(payload, list):
            self.room_list = []
            for room_info in payload:
                # Assume que o payload é uma lista de dicionários
                self.room_list.append({
                    "id": room_info.get("id"),
                    "name": room_info.get("name", "Sem nome"),
                    "playerCount": room_info.get("playerCount", 0),
                    "hasPassword": room_info.get("hasPassword", False),
                    "hostName": room_info.get("hostName", "Desconhecido")
                })
            # Não mostrar mensagem de sucesso para atualização silenciosa
            # self.success_message = "Lista de salas atualizada."
            # self.message_timer = pygame.time.get_ticks()
        else:
            print("Erro: Payload inválido para ROOMS_LIST")
            self.error_message = "Erro ao ler lista de salas."
            self.message_timer = pygame.time.get_ticks()

    # RESTAURADO: Handler para ROOM_CREATED (Baseado na lógica anterior)
    def handle_room_created(self, payload):
        print(f"[DEBUG] Entrando em handle_room_created. Payload: {payload}") # << NOVO PRINT
        print(f"[DEBUG] Valor de self.player_id ao entrar: {self.player_id}") # << NOVO PRINT
        # CORREÇÃO: Verificar 'hostPlayerId' (camelCase) como recebido do servidor
        if payload and "roomId" in payload and "name" in payload and "hostPlayerId" in payload:
            # Verifica se o hostPlayerId bate com o nosso ID
            print(f"[DEBUG] Verificando host: {payload['hostPlayerId']} vs {self.player_id}") # << NOVO PRINT
            if payload["hostPlayerId"] == self.player_id:
                self.room_id = payload["roomId"]
                room_name = payload["name"]
                self.success_message = f"Sala '{room_name}' criada (Cód: {self.room_id})!"
                self.message_timer = pygame.time.get_ticks()
                print(f"[DEBUG] Antes de mudar view em handle_room_created: {self.current_view}")
                self.current_view = "lobby"
                print(f"[DEBUG] Depois de mudar view em handle_room_created: {self.current_view}")
                self.host_mode = True
                # Define o jogador atual como o único na lista de lobby ao criar
                # Certificar que self.player existe antes de acessar atributos
                if self.player:
                    # CORREÇÃO: Usar 'playerId' (camelCase) para consistência interna
                    self.lobby_players = [{'playerId': self.player.player_id, 'name': self.player.name}]
                else: # Fallback se self.player ainda não foi criado
                    # CORREÇÃO: Usar 'playerId' (camelCase) para consistência interna
                    self.lobby_players = [{'playerId': self.player_id, 'name': self.player_name}]
                print(f"Entrando no lobby como Host. Jogadores: {self.lobby_players}")
            else:
                 # Recebemos ROOM_CREATED de uma sala que não criamos? Estranho.
                 print(f"Aviso: Recebido ROOM_CREATED para sala {payload['roomId']} mas o host é {payload['hostPlayerId']} (Nosso ID: {self.player_id})")
        else:
            print("[DEBUG] Payload inválido ou chaves ausentes em handle_room_created.") # << NOVO PRINT
            # Usar a mensagem de erro do servidor se disponível
            error_msg = payload.get('message', 'Erro desconhecido do servidor') if isinstance(payload, dict) else "Payload inválido"
            self.error_message = f"Falha ao criar sala: {error_msg}"
            self.message_timer = pygame.time.get_ticks()

    def handle_join_accepted(self, payload):
        """Chamado quando o servidor aceita o pedido para entrar em uma sala (JOIN_SUCCESS)."""
        print(f"[DEBUG] Entrando em handle_join_accepted. Payload: {payload}") # << NOVO PRINT
        # CORREÇÃO: Verificar "roomId" como chave primária, como visto no log
        if payload and "roomId" in payload:
            print(f"[DEBUG] Payload válido encontrado em handle_join_accepted.") # << NOVO PRINT
            self.room_id = payload["roomId"] # CORREÇÃO: Usar "roomId"
            room_name = payload.get("name", self.room_id)
            # CORREÇÃO: Usar 'hostPlayerId' (camelCase) como recebido do servidor, visto no log
            self.host_mode = (payload.get("hostPlayerId") == self.player_id)
            print(f"[DEBUG] room_id set para {self.room_id}. Host mode: {self.host_mode} (Host ID: {payload.get('hostPlayerId')}, Player ID: {self.player_id})") # << DEBUG ATUALIZADO
            self.lobby_players = payload.get("players", [])
            print(f"[DEBUG] Lobby players set para: {self.lobby_players}") # << NOVO PRINT
 
            self.success_message = f"Entrou na sala '{room_name}' (Cód: {self.room_id})!"
            self.message_timer = pygame.time.get_ticks()
            print(f"[DEBUG] Prestes a mudar view para 'lobby'. View atual: {self.current_view}") # << NOVO PRINT
            self.current_view = "lobby"
            print(f"[DEBUG] View alterada para 'lobby' em handle_join_accepted.") # << NOVO PRINT
            # Não precisa chamar update_lobby_view(), render_lobby lê self.lobby_players
        else:
            print(f"[DEBUG] Payload inválido ou sem 'roomId' em handle_join_accepted.") # << DEBUG ATUALIZADO
            # CORREÇÃO: Usar 'id' (camelCase) como recebido do servidor, não 'roomId'
            error_msg_key = 'message' # Chave padrão para mensagem de erro
            self.error_message = f"Falha ao entrar: {payload.get(error_msg_key, 'Payload inválido do servidor') if isinstance(payload, dict) else 'Payload inválido'}"
            self.message_timer = pygame.time.get_ticks()

    def handle_join_error(self, payload):
        message = payload.get("message", "Erro desconhecido") if payload else "Erro desconhecido"
        print(f"Recebido JOIN_ERROR: {message}")
        self.error_message = f"Falha ao entrar: {message}"
        self.message_timer = pygame.time.get_ticks()

    def handle_player_joined(self, payload):
        """Chamado quando outro jogador entra na sala."""
        print(f"[DEBUG] handle_player_joined recebeu: {payload}")
        # Verifica se estamos na sala correta e se temos dados válidos do jogador
        if isinstance(payload, dict) and payload.get("roomId") == self.room_id and isinstance(payload.get("player"), dict):
             player_info = payload["player"]
             # O servidor pode enviar 'id' em vez de 'playerId', verificamos ambos
             player_id = player_info.get('id') or player_info.get('playerId')
             player_name = player_info.get('name', 'Desconhecido')
             
             print(f"[DEBUG] Jogador {player_name} (ID: {player_id}) entrou na sala.")
             
             # Só prosseguir se tivermos um ID válido
             if player_id:
                 # Verificar se o jogador já está na lista (usando qualquer uma das chaves possíveis)
                 already_in_list = any(p.get('playerId') == player_id or p.get('id') == player_id for p in self.lobby_players)
                 
                 if not already_in_list:
                     # Adicionar à lista com o formato que a lista espera (usando 'playerId')
                     new_player = {'playerId': player_id, 'name': player_name}
                     self.lobby_players.append(new_player)
                     print(f"[DEBUG] Adicionado à lista de lobby: {new_player}")
                     print(f"[DEBUG] Lista atualizada: {self.lobby_players}")
                     
                     self.success_message = f"{player_name} entrou na sala."
                     self.message_timer = pygame.time.get_ticks()
                 else:
                     print(f"[DEBUG] Jogador {player_name} já estava na lista do lobby.")
             else:
                 print(f"[DEBUG] ID de jogador inválido: {player_info}")
        else:
            print(f"PLAYER_JOINED ignorado (sala errada, não estamos em sala, ou payload inválido). Payload: {payload}")

    def handle_player_left(self, payload):
        """Chamado quando outro jogador sai da sala."""
        print(f"[DEBUG] handle_player_left recebeu: {payload}")
        if isinstance(payload, dict) and payload.get("roomId") == self.room_id and "playerId" in payload:
             player_id_left = payload["playerId"]
             player_name = next((p.get('name', player_id_left) for p in self.lobby_players if p.get('playerId') == player_id_left), player_id_left)
             print(f"Jogador {player_name} (ID: {player_id_left}) saiu da sala.")
             
             # Remover da lista local
             initial_count = len(self.lobby_players)
             self.lobby_players = [p for p in self.lobby_players if p.get('playerId') != player_id_left]
             
             if len(self.lobby_players) < initial_count:
                 self.info_message = f"{player_name} saiu da sala."
                 self.message_timer = pygame.time.get_ticks()
                 
                 # Verificar se ainda há outros jogadores na sala além de nós
                 player_ids_remaining = [p.get('playerId') for p in self.lobby_players]
                 print(f"[DEBUG] Jogadores restantes: {player_ids_remaining}. Nosso ID: {self.player_id}")
                 
                 # Se só sobrou nosso ID ou a lista está vazia, voltar ao navegador de salas
                 if len(player_ids_remaining) <= 1 and self.player_id in player_ids_remaining or not player_ids_remaining:
                     print(f"[DEBUG] Apenas você sobrou na sala. Retornando ao navegador...")
                     self.room_id = None
                     self.lobby_players = []
                     self.game_state = None
                     self.host_mode = False
                     self.current_view = "room_browser"
                     self.send_websocket_message("LIST_ROOMS")  # Atualiza a lista de salas
                     self.info_message = "Você era o último na sala. Retornando..."
                     self.message_timer = pygame.time.get_ticks()
             
             # A lógica de novo host é tratada em handle_new_host
        else:
            print(f"PLAYER_LEFT ignorado (sala errada, não estamos em sala, ou payload inválido). Payload: {payload}")

    def handle_new_host(self, payload):
        """Chamado quando um novo host é designado na sala."""
        if isinstance(payload, dict) and "hostId" in payload:
            new_host_id = payload["hostId"]
            new_host_name = payload.get("hostName", new_host_id)
            print(f"Novo host da sala: {new_host_name} ({new_host_id})")
            self.host_mode = (new_host_id == self.player_id)
            if self.host_mode:
                self.success_message = "Você agora é o Host!"
            else:
                self.success_message = f"{new_host_name} é o novo Host."
            self.message_timer = pygame.time.get_ticks()

    def handle_room_update(self, payload):
         """Atualiza a lista de jogadores (quando alguém sai/entra)."""
         # Usado principalmente para sincronizar a lista após saídas (NEW_HOST já informa)
         if isinstance(payload, dict) and "players" in payload:
              print("Atualizando lista de jogadores via ROOM_UPDATE.")
              self.lobby_players = payload["players"]

    def handle_left_room(self, payload):
        """Chamado após enviarmos LEAVE_ROOM e o servidor confirmar."""
        print("Recebido confirmação LEFT_ROOM do servidor.")
        # Limpar estado local relacionado à sala (feito ao clicar no botão Sair)
        # Apenas garantir que a view volte ao browser/menu se ainda não estiver lá
        if self.current_view == "lobby" or self.current_view == "game" or self.current_view == "confirm_leave_game":
             self.current_view = "room_browser"
             self.load_room_list(mode=self.connection_mode)
        self.room_id = ""
        self.lobby_players = []
        self.host_mode = False
        self.game_state = None

    def handle_server_error(self, payload):
        message = payload.get("message", "Erro desconhecido do servidor") if payload else "Erro desconhecido do servidor"
        print(f"Erro do servidor: {message}")
        self.error_message = f"Erro do Servidor: {message}"
        self.message_timer = pygame.time.get_ticks()

    def handle_game_state(self, payload):
        """Lida com a atualização do estado do jogo recebida do servidor."""
        print(f"Recebido GAME_STATE: {payload}")
        if payload: # Verifica se o payload não é nulo
            self.game_state = payload # Armazena todo o estado recebido
            # Mudar a view para o jogo somente se não estiver já no jogo
            # Isso evita transições desnecessárias se já estamos na tela correta
            if self.current_view != "game":
                print("Mudando a view para 'game'...")
                self.current_view = "game"
                self.success_message = "Jogo iniciado!"
                self.message_timer = pygame.time.get_ticks()
            else:
                 # Se já estamos no jogo, apenas atualiza o estado (útil para turnos)
                 print("Estado do jogo atualizado.")
        else:
            print("Erro: Payload de GAME_STATE está vazio ou inválido.")
            self.error_message = "Erro ao receber estado do jogo."
            self.message_timer = pygame.time.get_ticks()

    def handle_server_disconnect(self):
        print("Desconectado do servidor WebSocket.")
        self.error_message = "Desconectado do servidor."
        self.message_timer = pygame.time.get_ticks()
        self.server_status = "Disconnected"
        self.websocket_client = None
        self.player_id = None
        # Voltar para o menu principal
        if self.current_view not in ["menu", "bot_selection"]:
            self.current_view = "menu"
        self.host_mode = False
        self.game = None
        self.game_state = None
        self.room_id = ""
        # Limpar P2P também (se ainda existir)
        if self.p2p_manager:
            self.p2p_manager.close()
            self.p2p_manager = None

    # --- Fim Handlers --- #

    def handle_event(self, event):
        """Lidar com eventos de entrada do usuário baseado na view atual"""
        if self.current_view == "menu":
            self.handle_menu_event(event)
        elif self.current_view == "lobby":
            self.handle_lobby_event(event)
        elif self.current_view == "game":
            self.handle_game_event(event)
        elif self.current_view == "bot_selection":
            self.handle_bot_selection_event(event)
        elif self.current_view == "join_room":
            self.handle_join_room_event(event)
        elif self.current_view == "room_browser":
            self.handle_room_browser_event(event)
        # ADICIONADO: Handler para a nova view de confirmação
        elif self.current_view == "confirm_leave_game":
             self.handle_confirm_leave_game_event(event)

    def handle_menu_event(self, event):
        """Lidar com eventos na tela do menu"""
        # Verificar clique no botão Jogar Sozinho
        play_alone_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_alone_rect.collidepoint(event.pos):
            # Verificar se o campo de nome está ativo antes de prosseguir
            if not self.name_input_active:
                self.handle_solo_click()
                return
        
        # Verificar clique no botão Jogar Online
        play_online_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 50 + 20, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_online_rect.collidepoint(event.pos):
            if not self.name_input_active:
                self.handle_online_click() # Chama o método modificado
                return
                
        # Verificar clique no botão Jogar na Rede Local
        play_local_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 2 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_local_rect.collidepoint(event.pos):
            # Verificar se o campo de nome está ativo antes de prosseguir
            if not self.name_input_active:
                self.handle_local_network_click()
                return
                
        # Verificar clique no botão Sair
        exit_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 3 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and exit_rect.collidepoint(event.pos):
            # Salvar o saldo do jogador antes de sair
            update_player_balance(self.player_name, self.player_balance)
            pygame.quit()
            sys.exit()
            
        # Manipular eventos do campo de nome
        name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
        
        # Verifica clique no campo de nome
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Verificar se o clique foi dentro do campo de nome
            if name_input_rect.collidepoint(event.pos):
                # Ativar o campo de nome
                self.name_input_active = True
                if self.player_name == "Player" or self.player_name == "":
                    self.player_name = ""  # Limpar o nome padrão
            else:
                # Se o clique foi fora do campo e o campo estava ativo, desativar e atualizar o saldo
                if self.name_input_active:
                    self.name_input_active = False
                    # Se o nome ficou vazio, voltar para "Player"
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após mudar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(f"Nome atualizado para: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
            
        # Manipular teclas para o campo de nome
        if event.type == pygame.KEYDOWN:
            if self.name_input_active:
                if event.key == pygame.K_RETURN:
                    # Confirmar o nome com a tecla Enter
                    self.name_input_active = False
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após confirmar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(f"Nome confirmado: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
                elif event.key == pygame.K_BACKSPACE:
                    # Apagar o último caractere
                    self.player_name = self.player_name[:-1]
                else:
                    # Limitar o nome a 20 caracteres
                    if len(self.player_name) < 20:
                        self.player_name = self.player_name + event.unicode

        # Verificar clique no botão de ajuda
        help_button = pygame.Rect(SCREEN_WIDTH - 50, 20, 40, 40)
        if event.type == pygame.MOUSEBUTTONDOWN and help_button.collidepoint(event.pos):
            self.show_tutorial = not self.show_tutorial
            return
            
        # Se o tutorial estiver aberto e o usuário clicar fora dele, fechar o tutorial
        if self.show_tutorial and event.type == pygame.MOUSEBUTTONDOWN:
            tutorial_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 150, 400, 300)
            if not tutorial_rect.collidepoint(event.pos):
                self.show_tutorial = False
                return

    def handle_solo_click(self):
        """Manipular clique no botão Jogar Sozinho"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "bot_selection"

    def handle_online_click(self):
        """Manipular clique no botão Jogar Online - Conecta WebSocket ou vai para browser."""
        # ... (lógica para garantir nome do jogador)

        # Conectar WebSocket se não estiver conectado
        if not self.websocket_client or not self.websocket_client.is_connected():
             self.connect_websocket()
        else:
             # Se já conectado, verifica se já estamos em uma sala
             print("Já conectado ao WebSocket.")
             if not self.room_id: # Só vai para o browser se NÃO estiver em uma sala
                 self.current_view = "room_browser"
                 self.send_websocket_message("LIST_ROOMS")
             else:
                  # Se já está em sala, talvez não fazer nada ou ir direto pro lobby?
                  # Por segurança, não mudar a view aqui se já tem room_id.
                  print(f"Já conectado e em uma sala ({self.room_id}). Não mudando view.")
                  # Opcional: Forçar refresh da lista se estiver no browser?
                  if self.current_view == "room_browser":
                       self.send_websocket_message("LIST_ROOMS")

    def handle_local_network_click(self):
        """Manipular clique no botão Jogar em Rede Local"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.connection_mode = "local"
        self.current_view = "room_browser"
        self.load_room_list(mode="local")

    def handle_create_room_click(self, event):
        """Manipular clique no botão Criar Sala"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "create_room"
        self.password_input = ""
        self.password_input_active = True
        self.room_name_input = f"Sala de {self.player_name}"
        self.room_name_input_active = False
        self.room_id = self.generate_room_id()
        self.connection_mode_selection = "online"  # Padrão: online

    def handle_find_rooms_click(self, event):
        """Manipular clique no botão Buscar Salas"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "join_room"
        self.room_id_input = ""
        self.room_id_input_active = True
        self.password_input = ""
        self.password_input_active = False
        self.connection_mode_selection = "online"  # Padrão: online

    def generate_room_id(self):
        """Gerar um ID de sala aleatório de 4 dígitos"""
        import random
        return str(random.randint(1000, 9999))

    def handle_bot_selection_event(self, event):
        """Lidar com eventos na tela de seleção de bots"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões para selecionar o número de bots
            button_width = 300
            button_height = 60
            button_x = SCREEN_WIDTH // 2 - button_width // 2
            
            # Botão para 1 bot
            bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
            if bot1_button.collidepoint(mouse_pos):
                self.start_single_player(1)
                return
                
            # Botão para 2 bots
            bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
            if bot2_button.collidepoint(mouse_pos):
                self.start_single_player(2)
                return
                
            # Botão para 3 bots
            bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
            if bot3_button.collidepoint(mouse_pos):
                self.start_single_player(3)
                return
                
            # Botão para voltar
            back_button = pygame.Rect(button_x, 460, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return

    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            # print(f"[DEBUG] Clique no lobby em: {mouse_pos}") # DEBUG
            button_width = 200
            button_height = 50
            button_y = SCREEN_HEIGHT - 80

            # Coordenadas dos botões (devem ser iguais às de render_lobby)
            start_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            leave_button_rect = pygame.Rect(30, button_y, 150, button_height)
            # print(f"[DEBUG] Botão Sair Rect: {leave_button_rect}") # DEBUG
            # print(f"[DEBUG] Botão Iniciar Rect: {start_button_rect}") # DEBUG
            # print(f"[DEBUG] self.host_mode: {self.host_mode}") # DEBUG

            # Verificar clique no botão Sair
            if leave_button_rect.collidepoint(mouse_pos):
                # print("[DEBUG] Clique detectado no botão Sair.") # DEBUG
                if self.websocket_client and self.websocket_client.is_connected():
                    self.send_websocket_message("LEAVE_ROOM", {"roomId": self.room_id})
                
                # Limpar estado local e voltar para o browser
                self.room_id = None
                self.lobby_players = []
                self.host_mode = False
                self.current_view = "room_browser"
                self.success_message = "Você saiu da sala."
                self.message_timer = pygame.time.get_ticks()
                # Atualizar lista de salas ao sair
                self.load_room_list(mode=self.connection_mode)
                return

            # Verificar clique no botão Iniciar Jogo (apenas se for host)
            # Adicionando prints detalhados aqui
            is_on_start_button = start_button_rect.collidepoint(mouse_pos)
            # MOSTRAR RESULTADO DO COLLIDEPOINT EXPLICITAMENTE
            # print(f"[DEBUG] start_button_rect.collidepoint(mouse_pos): {is_on_start_button}") # DEBUG 
            # print(f"[DEBUG] Clique no botão iniciar? {is_on_start_button}") # DEBUG
            if self.host_mode and is_on_start_button:
                # print("[DEBUG] Clique detectado no botão Iniciar Jogo (Host Mode TRUE).") # DEBUG
                if self.websocket_client and self.websocket_client.is_connected():
                    # Verificar se há jogadores suficientes (ex: pelo menos 1?)
                    # print(f"[DEBUG] Verificando contagem de jogadores: {len(self.lobby_players)}") # DEBUG
                    if len(self.lobby_players) >= 1: # Mudar para 2 se quiser mínimo de 2 players
                         # print(f"[DEBUG] Enviando START_GAME para sala {self.room_id}") # DEBUG
                         if self.send_websocket_message("START_GAME", {"roomId": self.room_id}): # Revertido para maiúsculas
                              self.success_message = "Iniciando o jogo..."
                              self.message_timer = pygame.time.get_ticks()
                              # A mudança para a view 'game' deve ocorrer ao receber GAME_STARTED do servidor
                         else:
                              self.error_message = "Falha ao enviar comando para iniciar jogo."
                              self.message_timer = pygame.time.get_ticks()
                    else:
                        # print("[DEBUG] Não há jogadores suficientes.") # DEBUG
                        self.error_message = "Precisa de mais jogadores para iniciar."
                        self.message_timer = pygame.time.get_ticks()
                else:
                    # print("[DEBUG] Não conectado ao websocket para iniciar.") # DEBUG
                    self.error_message = "Não conectado para iniciar o jogo."
                    self.message_timer = pygame.time.get_ticks()
                return
            elif not self.host_mode and is_on_start_button:
                 # print("[DEBUG] Clique no botão Iniciar, mas não é Host.") # DEBUG
                 pass # Não faz nada se não for host
            elif self.host_mode and not is_on_start_button:
                 # print("[DEBUG] Host clicou, mas fora do botão Iniciar.") # DEBUG
                 pass # Não faz nada se clicar fora do botão

        # TODO: Adicionar lógica para eventos de teclado, se necessário
        # pass # Remover pass original

    def handle_game_event(self, event):
        """Lidar com eventos durante o jogo"""
        # Se estamos no modo online, usar a função de tratamento específica
        is_online = self.websocket_client and self.websocket_client.is_connected()
        if is_online:
            # Tratar o botão de voltar (comum a ambos os modos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                menu_button = pygame.Rect(10, 10, 120, 40)
                if menu_button.collidepoint(event.pos):
                    self.current_view = "confirm_leave_game"
                    return
            
            # Delegar os eventos de gameplay online para o handler específico
            self.handle_game_events(event)
            return

        # Código original para o modo offline
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos

            # Verificar se é nossa vez (para botões Hit/Stand)
            is_our_turn = False
            if self.game_state and "players" in self.game_state and "currentPlayerIndex" in self.game_state and self.game_state["currentPlayerIndex"] >= 0:
                 try:
                      current_player_index = self.game_state["currentPlayerIndex"]
                      # Adicionar verificação de índice válido
                      if 0 <= current_player_index < len(self.game_state["players"]):
                           is_our_turn = (self.game_state["players"][current_player_index]["playerId"] == self.player.player_id)
                 except IndexError:
                      print("Erro: Índice do jogador atual inválido no game_state.")
                      is_our_turn = False # Trata como não sendo nossa vez se houver erro

            # Botão de voltar ao menu (ou sair da partida)
            # A posição e visibilidade podem precisar de ajuste
            is_multiplayer = self.websocket_client is not None and self.websocket_client.is_connected()
            # Por ora, usamos o botão existente que aparece com < 4 players
            # Poderia ser um botão "Sair da Partida" sempre visível no online?
            show_back_button = not is_multiplayer # Exemplo: mostra só no single player
            # Para o teste, vamos permitir acionar a confirmação mesmo no single player por enquanto
            show_back_button = True # Temporário para testar

            if show_back_button:
                menu_button = pygame.Rect(10, 10, 120, 40)
                if menu_button.collidepoint(mouse_pos):
                    if is_multiplayer:
                        # Em jogo online, pede confirmação
                        self.current_view = "confirm_leave_game"
                    else:
                        # Em jogo single player, volta direto
                        self.current_view = "menu"
                        self.game = None # Limpa jogo local
                        self.game_state = None
                        self.host_mode = False
                    return # Sai do handler após clicar no botão

            # --- Lógica dos botões de ação (Hit, Stand, Bet, New Round) --- #
            FOOTER_HEIGHT = 150
            footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
            controls_x = 20
            controls_width = SCREEN_WIDTH // 2 - 40
            button_y = footer_start_y + 45

            if self.game_state:
                game_status = self.game_state.get("state")
                # Botões de ajuste e confirmação de aposta
                if game_status == "BETTING":
                    bet_amount_x = controls_x + 120
                    bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, WHITE)
                    btn_width, btn_height, btn_y = 36, 36, footer_start_y + 12
                    decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
                    increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
                    bet_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                    if decrease_bet_button.collidepoint(mouse_pos): self.decrease_bet(); return
                    if increase_bet_button.collidepoint(mouse_pos): self.increase_bet(); return
                    if bet_button.collidepoint(mouse_pos): self.place_bet(); return

                # Botões Hit/Stand
                elif game_status == "PLAYER_TURN" and is_our_turn:
                    button_width_half = (controls_width - 10) // 2
                    hit_button = pygame.Rect(controls_x, button_y, button_width_half, 50)
                    stand_button = pygame.Rect(controls_x + button_width_half + 10, button_y, button_width_half, 50)
                    if hit_button.collidepoint(mouse_pos): self.hit(); return
                    if stand_button.collidepoint(mouse_pos): self.stand(); return

                # Botão Nova Rodada
                elif game_status == "GAME_OVER":
                    new_round_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                    if new_round_button.collidepoint(mouse_pos): self.new_round(); return

    def update(self):
        """Atualizar o estado do jogo"""
        # Processar mensagens da fila do WebSocket (se a fila for usada)
        self.process_websocket_messages()

        # Lógica P2P removida por enquanto
        # if hasattr(self, 'p2p_manager') and self.p2p_manager: ...

        # Só atualiza o p2p_manager se ele existir (modo multiplayer)
        if hasattr(self, 'p2p_manager') and self.p2p_manager:
            self.p2p_manager.update()  # Process any pending P2P network messages

        # Atualizar estado do jogo se for o host
        if self.host_mode and self.game:
            # Verificar se todos os jogadores fizeram suas apostas
            if (self.game_state and 
                self.game_state["state"] == "BETTING" and 
                all(player["current_bet"] > 0 for player in self.game_state["players"])):
                self.game._deal_initial_cards()
                self.broadcast_game_state()

            # Bot play logic
            if self.game_state and self.game_state["state"] == "PLAYER_TURN":
                current_player = self.game_state["players"][self.game_state["currentPlayerIndex"]]
                if current_player["name"].startswith("Bot"):
                    self.bot_play()
                    
                # Verificar se o jogo acabou implicitamente (todos pararam ou estouraram)
                active_players = [p for p in self.game_state["players"] 
                                # CORREÇÃO: Usar playerId
                                if not p["is_busted"] and (p["playerId"] != self.game_state["players"][self.game_state["currentPlayerIndex"]]["playerId"])]
                if not active_players:
                    # Se não há mais jogadores ativos além do atual, o jogo termina
                    self.check_winner()

        # Atualizar mensagens do jogo
        if self.game_state and "messages" in self.game_state:
            self.messages = self.game_state["messages"]

    def render(self):
        """Renderizar a interface do jogo"""
        # Desenha a view atual
        if self.current_view == "menu":
            self.render_menu()
        elif self.current_view == "lobby":
            self.render_lobby()
        elif self.current_view == "game":
            self.render_game()
        elif self.current_view == "bot_selection":
            self.render_bot_selection()
        elif self.current_view == "join_room":
            self.render_join_room()
        elif self.current_view == "room_browser":
            self.render_room_browser()
        # ADICIONADO: Renderiza o popup de confirmação SOBRE a tela do jogo
        elif self.current_view == "confirm_leave_game":
             # Renderiza a tela do jogo por baixo primeiro
             self.render_game()
             # Depois renderiza o popup de confirmação por cima
             self.render_confirm_leave_game()

        # Renderizar mensagens de erro ou sucesso (por cima de tudo)
        self.display_messages()

        pygame.display.flip()

    def render_menu(self):
        """Renderizar a tela do menu"""
        # Desenhar o fundo com gradiente
        self.screen.fill((0, 100, 0))  # Verde escuro para o fundo
        
        # Desenhar área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 80, 0), title_bg)
        
        # Desenhar título do jogo
        title = self.title_font.render("Blackjack 21 P2P", True, (240, 240, 240))
        title_shadow = self.title_font.render("Blackjack 21 P2P", True, (0, 40, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        shadow_rect = title_shadow.get_rect(center=(SCREEN_WIDTH // 2 + 2, 62))
        self.screen.blit(title_shadow, shadow_rect)
        self.screen.blit(title, title_rect)
        
        # Não carregar o saldo toda vez - usar o valor já armazenado em self.player_balance
        
        # Campo de nome
        name_label = self.medium_font.render("Nome:", True, WHITE)
        self.screen.blit(name_label, (SCREEN_WIDTH // 2 - 150, 150))
        
        # Desenhar campo de nome com borda que muda de cor baseado no foco
        name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
        mouse_pos = pygame.mouse.get_pos()
        hover_name_input = name_input_rect.collidepoint(mouse_pos)
        
        # Determinar a cor da borda baseado no estado do input
        if self.name_input_active:
            border_color = (0, 120, 255)  # Azul quando ativo
        elif hover_name_input:
            border_color = (100, 180, 255)  # Azul claro quando o mouse está em cima
        else:
            border_color = (0, 80, 0)  # Verde escuro quando inativo
        
        # Desenhar campo de texto com cantos arredondados
        pygame.draw.rect(self.screen, WHITE, name_input_rect, border_radius=5)
        pygame.draw.rect(self.screen, border_color, name_input_rect, 2, border_radius=5)
        
        # Texto dentro do campo
        if self.player_name == "":
            name_text = self.small_font.render("Player", True, GRAY)
            self.screen.blit(name_text, (name_input_rect.x + 10, name_input_rect.y + 8))
        else:
            name_text = self.small_font.render(self.player_name, True, BLACK)
            text_rect = name_text.get_rect(midleft=(name_input_rect.x + 10, name_input_rect.centery))
            self.screen.blit(name_text, text_rect)
        
        # Adicionar cursor piscante quando o campo estiver ativo
        if self.name_input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_pos = name_input_rect.x + 10 + name_text.get_width()
            pygame.draw.line(self.screen, BLACK, 
                            (cursor_pos, name_input_rect.y + 5), 
                            (cursor_pos, name_input_rect.y + 25), 2)
        
        # Texto de ajuda abaixo do campo de nome
        hint_text = self.small_font.render("Clique para mudar seu nome", True, (200, 200, 200))
        self.screen.blit(hint_text, (SCREEN_WIDTH // 2 - 90, 185))
        
        # Exibir saldo do jogador
        balance_label = self.medium_font.render(f"Saldo: {self.player_balance} moedas", True, WHITE)
        self.screen.blit(balance_label, (SCREEN_WIDTH // 2 - 150, 220))
        
        # Aviso de saldo baixo
        if self.player_balance <= 100:
            warning_text = self.small_font.render("Saldo baixo!", True, (255, 100, 100))
            self.screen.blit(warning_text, (SCREEN_WIDTH // 2 + 100, 220))
        
        # Desenhar botões do menu
        self.draw_menu_buttons()
        
        # Botão de ajuda no canto superior direito
        help_button = pygame.Rect(SCREEN_WIDTH - 50, 20, 40, 40)
        mouse_pos = pygame.mouse.get_pos()
        help_color = (0, 120, 200) if help_button.collidepoint(mouse_pos) else (0, 80, 160)
        pygame.draw.rect(self.screen, help_color, help_button, border_radius=20)
        pygame.draw.rect(self.screen, WHITE, help_button, 2, border_radius=20)
        help_text = self.medium_font.render("?", True, WHITE)
        help_rect = help_text.get_rect(center=help_button.center)
        self.screen.blit(help_text, help_rect)
        
        # Exibir tutorial em pop-up se ativado
        if self.show_tutorial:
            self.render_tutorial_popup()
    
    def render_tutorial_popup(self):
        """Renderiza o pop-up de tutorial"""
        # Fundo semi-transparente para destacar o pop-up
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))  # Preto semi-transparente
        self.screen.blit(s, (0, 0))
        
        # Desenhar o pop-up
        popup_rect = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 200, 500, 400)
        pygame.draw.rect(self.screen, (0, 80, 0), popup_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, popup_rect, 3, border_radius=10)
        
        # Título do tutorial
        title = self.medium_font.render("Como Jogar Blackjack", True, WHITE)
        title_rect = title.get_rect(midtop=(popup_rect.centerx, popup_rect.y + 20))
        self.screen.blit(title, title_rect)
        
        # Linha separadora
        pygame.draw.line(self.screen, WHITE, 
                        (popup_rect.x + 20, popup_rect.y + 50), 
                        (popup_rect.x + popup_rect.width - 20, popup_rect.y + 50), 2)
        
        # Texto do tutorial
        tutorial_texts = [
            "Objetivo: Chegue o mais próximo possível de 21 pontos sem passar.",
            "Cartas numéricas valem seu número, figuras (J,Q,K) valem 10,",
            "e Ases podem valer 1 ou 11, conforme for melhor para a mão.",
            "",
            "Ações:",
            "- Hit: Peça mais uma carta.",
            "- Stand: Mantenha sua mão e passe a vez.",
            "- Apostar: Defina o valor da sua aposta no início de cada rodada.",
            "",
            "O dealer pega cartas até atingir pelo menos 17 pontos.",
            "Se você ultrapassar 21, perde automaticamente (estouro).",
            "Se o dealer estourar, você ganha.",
            "Se ninguém estourar, ganha quem tiver o valor mais alto."
        ]
        
        y_pos = popup_rect.y + 60
        for text in tutorial_texts:
            rendered_text = self.small_font.render(text, True, WHITE)
            text_rect = rendered_text.get_rect(topleft=(popup_rect.x + 30, y_pos))
            self.screen.blit(rendered_text, text_rect)
            y_pos += 25
        
        # Botão de fechar
        close_text = self.small_font.render("Clique em qualquer lugar para fechar", True, (200, 200, 200))
        close_rect = close_text.get_rect(midbottom=(popup_rect.centerx, popup_rect.bottom - 15))
        self.screen.blit(close_text, close_rect)
    
    def draw_menu_buttons(self):
        """Desenha os botões do menu principal"""
        # Função auxiliar para desenhar botões
        def draw_menu_button(rect, text, color, hover_color=(0, 120, 255)):
            mouse_pos = pygame.mouse.get_pos()
            button_color = hover_color if rect.collidepoint(mouse_pos) else color
            
            # Desenhar botão com cantos arredondados
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=10)
            
            # Texto do botão
            button_text = self.medium_font.render(text, True, WHITE)
            text_rect = button_text.get_rect(center=rect.center)
            self.screen.blit(button_text, text_rect)
        
        # Posicionamento dos botões
        button_width = 250
        button_height = 50
        button_spacing = 20
        start_y = 280
        
        # Botão Jogar Sozinho
        play_alone_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                      start_y, 
                                      button_width, 
                                      button_height)
        draw_menu_button(play_alone_rect, "Jogar Sozinho", (0, 100, 0), (0, 150, 0))
        
        # Botão Jogar Online
        play_online_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                       start_y + button_height + button_spacing, 
                                       button_width, 
                                       button_height)
        draw_menu_button(play_online_rect, "Jogar Online", (0, 80, 150), (0, 100, 200))
        
        # Botão Jogar na Rede Local
        play_local_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                      start_y + 2 * (button_height + button_spacing), 
                                      button_width, 
                                      button_height)
        draw_menu_button(play_local_rect, "Jogar na Rede Local", (150, 100, 0), (200, 130, 0))
        
        # Botão Sair
        exit_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                start_y + 3 * (button_height + button_spacing), 
                                button_width, 
                                button_height)
        draw_menu_button(exit_rect, "Sair", (150, 0, 0), (200, 0, 0))

    def render_lobby(self):
        """Renderizar a tela de lobby da sala"""
        # print("[DEBUG] Entrando em render_lobby") # DEBUG
        self.screen.fill((0, 50, 0)) # Fundo verde escuro

        # Título (Nome da Sala ou ID)
        # print(f"[DEBUG] room_id: {self.room_id}") # DEBUG
        room_name_text = f"Sala: {self.room_id if self.room_id else '???'}" # Evitar erro se room_id for None/vazio
        title = self.large_font.render(room_name_text, True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)

        # --- Exibir o Código da Sala ---
        code_label_text = "Código para Convidar:"
        code_label_surface = self.medium_font.render(code_label_text, True, (200, 200, 200))
        code_label_rect = code_label_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(code_label_surface, code_label_rect)

        # print(f"[DEBUG] renderizando código: {self.room_id}") # DEBUG
        code_text_val = self.room_id if self.room_id else "N/A"
        code_text = self.large_font.render(code_text_val, True, (255, 220, 0)) # Amarelo destacado
        code_text_rect = code_text.get_rect(center=(SCREEN_WIDTH // 2, 140))
        # Adicionar um fundo para o código para destacar
        code_bg_rect = code_text_rect.inflate(20, 10)
        pygame.draw.rect(self.screen, (0, 30, 0), code_bg_rect, border_radius=5)
        self.screen.blit(code_text, code_text_rect)
        # --- Fim Código da Sala ---

        # Lista de Jogadores
        player_list_y = 200
        player_label = self.medium_font.render("Jogadores:", True, WHITE)
        self.screen.blit(player_label, (50, player_list_y))
        
        # print(f"[DEBUG] lobby_players: {self.lobby_players}") # DEBUG
        # print(f"[DEBUG] self.player_id: {self.player_id}") # DEBUG
        if not isinstance(self.lobby_players, list):
             # print("[DEBUG] ERRO: self.lobby_players não é uma lista!") # DEBUG
             self.lobby_players = [] # Tenta corrigir

        for i, player_info in enumerate(self.lobby_players):
            # print(f"[DEBUG] Renderizando jogador {i}: {player_info}") # DEBUG
            player_name = player_info.get('name', 'Desconhecido')
            player_id_in_list = player_info.get('playerId') # CORREÇÃO: Usar playerId
            # Verifica se é o host comparando com self.player_id
            is_host = player_id_in_list is not None and player_id_in_list == self.player_id 
            display_text = f"{i+1}. {player_name}"
            if is_host:
                display_text += " (Host)"
            
            player_surface = self.medium_font.render(display_text, True, WHITE)
            self.screen.blit(player_surface, (70, player_list_y + 40 + i * 30))

        # Botões
        button_width = 200
        button_height = 50
        button_y = SCREEN_HEIGHT - 80

        # Botão Iniciar Jogo (apenas para o host)
        if self.host_mode:
            start_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            start_color = (0, 150, 0) # Verde
            mouse_pos = pygame.mouse.get_pos()
            if start_button_rect.collidepoint(mouse_pos):
                start_color = (0, 200, 0) # Verde mais claro no hover

            pygame.draw.rect(self.screen, start_color, start_button_rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, start_button_rect, 2, border_radius=10)
            start_text = self.medium_font.render("Iniciar Jogo", True, WHITE)
            start_text_rect = start_text.get_rect(center=start_button_rect.center)
            self.screen.blit(start_text, start_text_rect)
        else:
            # Mensagem para não-hosts
            wait_text = self.medium_font.render("Aguardando Host iniciar...", True, (200, 200, 200))
            wait_rect = wait_text.get_rect(center=(SCREEN_WIDTH // 2, button_y + button_height // 2))
            self.screen.blit(wait_text, wait_rect)


        # Botão Sair da Sala
        leave_button_rect = pygame.Rect(30, button_y, 150, button_height)
        leave_color = (150, 0, 0) # Vermelho
        mouse_pos = pygame.mouse.get_pos()
        if leave_button_rect.collidepoint(mouse_pos):
            leave_color = (200, 0, 0) # Vermelho mais claro no hover

        pygame.draw.rect(self.screen, leave_color, leave_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, leave_button_rect, 2, border_radius=10)
        leave_text = self.medium_font.render("Sair", True, WHITE)
        leave_text_rect = leave_text.get_rect(center=leave_button_rect.center)
        self.screen.blit(leave_text, leave_text_rect)

    def render_game(self):
        """Renderizar a tela do jogo"""
        if not self.game_state:
            self.screen.fill(GREEN)  # Fundo verde
            self.medium_font.render_to(self.screen, (self.width // 2 - 150, self.height // 2 - 20), "Aguardando estado do jogo...", WHITE)
            return

        # Acesso seguro aos dados do game_state
        game_data = self.game_state
        dealer_hand = game_data.get("dealerHand", [])
        players = game_data.get("players", [])  # Lista de estados dos jogadores
        game_phase = game_data.get("state", "UNKNOWN")  # Ex: BETTING, PLAYER_TURN, DEALER_TURN, ROUND_OVER
        current_player_id = game_data.get("currentPlayerId")

        # Tentar encontrar o estado do nosso jogador
        our_player_state = next((p for p in players if p.get("id") == self.player_id or p.get("playerId") == self.player_id), None)
        
        # Salvar em uma variável temporária para uso em handle_game_events
        self.our_player_state = our_player_state

        # Background com gradiente (ou simples)
        self.screen.fill((0, 50, 0))  # Verde base escuro

        # --- Renderizar Mão do Dealer --- #
        self.medium_font.render_to(self.screen, (50, 50), "Dealer:" + (f" ({game_data.get('dealerHandValue', '?')})" if game_phase != "BETTING" else ""), WHITE)
        dealer_cards_x = 50
        # Esconder a primeira carta do dealer se for a vez do jogador
        hide_dealer_card = (game_phase == "PLAYER_TURN" and len(dealer_hand) > 0)
        for i, card_info in enumerate(dealer_hand):
            if isinstance(card_info, dict):
                card_img_key = card_info.get("display") if not (hide_dealer_card and i == 0) else "card_back"
                card_img = self.card_images.get(card_img_key)
                if card_img:
                    self.screen.blit(card_img, (dealer_cards_x, 80))
                    dealer_cards_x += self.card_width // 3  # Sobrepor cartas

        # --- Renderizar Mãos dos Jogadores --- #
        player_start_y = self.height - 250
        player_spacing = min(150, self.width // max(len(players), 1))
        
        for i, p_state in enumerate(players):
            if not isinstance(p_state, dict):
                continue
                
            player_id = p_state.get("id") or p_state.get("playerId")
            player_name = p_state.get("name", f"Jogador {i+1}")
            player_hand = p_state.get("hand", [])
            hand_value = p_state.get("handValue", 0)
            player_status = p_state.get("status", "PLAYING")  # Ex: PLAYING, BETTING, WAITING, BUSTED, BLACKJACK, STAND
            balance = p_state.get("balance", "?")
            current_bet = p_state.get("currentBet", 0)
            
            is_our_player = (player_id == self.player_id)
            is_current_player = (player_id == current_player_id)
            
            # Calcular posição horizontal baseada no índice
            player_x = 50 + (i * player_spacing)
            
            # Ajustar para distribuir melhor (opcional)
            if len(players) <= 4:
                player_x = 50 + (i * (self.width - 100) // max(len(players), 1))
            
            player_y = player_start_y
            
            # Nome e info do jogador
            name_color = YELLOW if is_our_player else WHITE
            player_label = f"{player_name}"
            if is_our_player:
                player_label += " (Você)"
            if is_current_player:
                player_label += " - Turno"
                
            self.medium_font.render_to(self.screen, (player_x, player_y), player_label, name_color)
            self.small_font.render_to(self.screen, (player_x, player_y + 25), f"Saldo: {balance} | Aposta: {current_bet}", WHITE)
            
            # Renderizar cartas
            cards_x = player_x
            cards_y = player_y + 50
            for card_info in player_hand:
                if isinstance(card_info, dict):
                    card_img = self.card_images.get(card_info.get("display", "card_back"))
                    if card_img:
                        self.screen.blit(card_img, (cards_x, cards_y))
                        cards_x += self.card_width // 3  # Sobrepor cartas
            
            # Valor da mão e status
            hand_value_text = f"Valor: {hand_value}"
            status_color = WHITE
            if player_status == "BUSTED":
                hand_value_text += " (Estourou!)"
                status_color = RED
            elif player_status == "BLACKJACK":
                hand_value_text += " (Blackjack!)"
                status_color = YELLOW
            elif player_status == "STAND":
                hand_value_text += " (Parou)"
            
            self.medium_font.render_to(self.screen, (player_x, cards_y + self.card_height + 10), hand_value_text, status_color)
        
        # --- Renderizar Botões de Ação (Apenas para nosso jogador) --- #
        if our_player_state:
            is_our_turn = (current_player_id == self.player_id)
            button_y = self.height - 60
            button_x_start = self.width - 450
            button_spacing = 110
            
            # BETTING: Campo de aposta e botão de confirmar
            if game_phase == "BETTING" and our_player_state.get("status") == "BETTING":
                bet_button_rect = pygame.Rect(button_x_start, button_y, 100, 40)
                pygame.draw.rect(self.screen, BUTTON_COLOR if not self.bet_input_active else BUTTON_HOVER_COLOR, bet_button_rect, border_radius=5)
                self.small_font.render_to(self.screen, (bet_button_rect.centerx - 35, bet_button_rect.centery - 10), "Apostar", BLACK)
                
                # Campo de Input de Aposta
                input_rect = pygame.Rect(button_x_start + button_spacing, button_y, 150, 40)
                pygame.draw.rect(self.screen, WHITE, input_rect, border_radius=5)
                pygame.draw.rect(self.screen, BLACK, input_rect, 2, 5)  # Borda
                bet_text = self.bet_amount_str if self.bet_input_active else str(our_player_state.get("currentBet", 0))
                self.small_font.render_to(self.screen, (input_rect.x + 10, input_rect.centery - 10), bet_text, BLACK)
            
            # PLAYER_TURN: Botões Hit e Stand
            elif game_phase == "PLAYER_TURN" and is_our_turn and our_player_state.get("status") == "PLAYING":
                hit_button_rect = pygame.Rect(button_x_start, button_y, 100, 40)
                stand_button_rect = pygame.Rect(button_x_start + button_spacing, button_y, 100, 40)
                
                pygame.draw.rect(self.screen, BUTTON_COLOR, hit_button_rect, border_radius=5)
                self.small_font.render_to(self.screen, (hit_button_rect.centerx - 20, hit_button_rect.centery - 10), "Hit", BLACK)
                
                pygame.draw.rect(self.screen, BUTTON_COLOR, stand_button_rect, border_radius=5)
                self.small_font.render_to(self.screen, (stand_button_rect.centerx - 30, stand_button_rect.centery - 10), "Stand", BLACK)
            
            # ROUND_OVER: Botão Nova Rodada
            elif game_phase == "ROUND_OVER" and self.host_mode:  # Nova rodada apenas para o host
                new_round_button_rect = pygame.Rect(button_x_start, button_y, 180, 40)
                pygame.draw.rect(self.screen, BUTTON_COLOR, new_round_button_rect, border_radius=5)
                self.small_font.render_to(self.screen, (new_round_button_rect.centerx - 60, new_round_button_rect.centery - 10), "Nova Rodada", BLACK)
        
        # Exibir mensagens e outras informações
        self.display_messages()

    def handle_game_events(self, event):
        """Processar eventos na tela de jogo online"""
        if not self.game_state or not hasattr(self, 'our_player_state') or not self.our_player_state:
            return
            
        game_phase = self.game_state.get("state", "UNKNOWN")
        current_player_id = self.game_state.get("currentPlayerId")
        is_our_turn = (current_player_id == self.player_id)
        
        button_y = self.height - 60
        button_x_start = self.width - 450
        button_spacing = 110
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            
            # Lógica de clique para APOSTA
            if game_phase == "BETTING" and self.our_player_state.get("status") == "BETTING":
                bet_button_rect = pygame.Rect(button_x_start, button_y, 100, 40)
                input_rect = pygame.Rect(button_x_start + button_spacing, button_y, 150, 40)
                
                if bet_button_rect.collidepoint(mouse_pos):
                    try:
                        bet_value = int(self.bet_amount_str) if self.bet_input_active else self.our_player_state.get("currentBet", 0)
                        if bet_value > 0:
                            print(f"[DEBUG] Enviando PLACE_BET: {bet_value}")
                            self.send_websocket_message("PLACE_BET", {"amount": bet_value})
                            self.bet_input_active = False
                        else:
                            self.error_message = "Aposta deve ser maior que zero."
                            self.message_timer = pygame.time.get_ticks()
                    except ValueError:
                        self.error_message = "Valor de aposta inválido."
                        self.message_timer = pygame.time.get_ticks()
                        
                elif input_rect.collidepoint(mouse_pos):
                    self.bet_input_active = True
                    self.bet_amount_str = ""
                else:
                    self.bet_input_active = False
            
            # Lógica de clique para HIT e STAND
            elif game_phase == "PLAYER_TURN" and is_our_turn and self.our_player_state.get("status") == "PLAYING":
                hit_button_rect = pygame.Rect(button_x_start, button_y, 100, 40)
                stand_button_rect = pygame.Rect(button_x_start + button_spacing, button_y, 100, 40)
                
                if hit_button_rect.collidepoint(mouse_pos):
                    print("[DEBUG] Enviando HIT")
                    self.send_websocket_message("HIT")
                elif stand_button_rect.collidepoint(mouse_pos):
                    print("[DEBUG] Enviando STAND")
                    self.send_websocket_message("STAND")
            
            # Lógica de clique para NOVA RODADA
            elif game_phase == "ROUND_OVER" and self.host_mode:
                new_round_button_rect = pygame.Rect(button_x_start, button_y, 180, 40)
                if new_round_button_rect.collidepoint(mouse_pos):
                    print("[DEBUG] Enviando NEW_ROUND")
                    self.send_websocket_message("NEW_ROUND")
        
        # Lógica de input de teclado para APOSTA
        elif event.type == pygame.KEYDOWN and self.bet_input_active:
            if event.key == pygame.K_RETURN:
                try:
                    bet_value = int(self.bet_amount_str)
                    if bet_value > 0:
                        print(f"[DEBUG] Enviando PLACE_BET: {bet_value}")
                        self.send_websocket_message("PLACE_BET", {"amount": bet_value})
                        self.bet_input_active = False
                    else:
                        self.error_message = "Aposta deve ser maior que zero."
                        self.message_timer = pygame.time.get_ticks()
                except ValueError:
                    self.error_message = "Valor de aposta inválido."
                    self.message_timer = pygame.time.get_ticks()
            elif event.key == pygame.K_BACKSPACE:
                self.bet_amount_str = self.bet_amount_str[:-1]
            elif event.unicode.isdigit():
                self.bet_amount_str += event.unicode

    def render_card(self, card, x, y, scale=1.0):
        """Renderizar uma carta de baralho com escala personalizada"""
        # Calcular escala baseada no tamanho desejado da carta
        final_scale = self.card_sprites.CARD_WIDTH / CARD_WIDTH * scale
        
        # Obter a sprite da carta com a escala apropriada
        # CORREÇÃO: As chaves em 'card' também são camelCase
        card_sprite = self.card_sprites.get_card(card["suit"], card["value"], final_scale)
        
        # Desenhar a carta na posição especificada
        self.screen.blit(card_sprite, (x, y))

    def render_card_back(self, x, y, scale=1.0):
        """Renderizar o verso de uma carta com escala personalizada"""
        final_scale = self.card_sprites.CARD_WIDTH / CARD_WIDTH * scale
        card_back = self.card_sprites.get_card_back(final_scale)
        self.screen.blit(card_back, (x, y))

    def create_game(self):
        """Criar um novo jogo como host"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        self.game = Game()
        self.game.initialize_game(self.player)

        # Iniciar o servidor P2P
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

        # Criar lobby no serviço de matchmaking
        success, game_id, lobby = self.matchmaking_service.create_game(self.player_name)
        if success:
            self.game.game_id = game_id
            self.current_view = "lobby"
            self.host_mode = True
            self.game_state = self.game.get_game_state()
        else:
            print(f"Erro ao criar lobby: {lobby}")

    def join_game_screen(self):
        """Mostrar tela para entrar em um jogo existente"""
        # Na implementação real, você pode adicionar uma tela para listar lobbies disponíveis
        # Simplificado para este exemplo
        success, lobbies = self.matchmaking_service.list_games()
        if success and lobbies:
            # Apenas entrar no primeiro lobby disponível para este exemplo
            self.join_game(lobbies[0]["game_id"])
        else:
            print("Nenhum jogo disponível")

    def join_game(self, game_id):
        """Entrar em um jogo existente"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar ao lobby
        success, lobby = self.matchmaking_service.join_game(game_id)
        if not success:
            print(f"Erro ao entrar no lobby: {lobby}")
            return

        # Conectar ao host P2P
        host_address = lobby["host_address"]
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.start()

        connect_success, message = self.p2p_manager.connect_to_host(host_address)
        if connect_success:
            # Enviar mensagem de solicitação para entrar
            join_message = Message.create_join_request(
                self.player.player_id,
                self.player.name
            )
            self.p2p_manager.send_message(join_message)

            self.current_view = "lobby"
            self.host_mode = False
        else:
            print(f"Erro ao conectar ao host: {message}")

    def on_message_received(self, sender_id, message):
        """Callback para mensagens recebidas"""
        if message.msg_type == MessageType.GAME_STATE:
            # Atualizar o estado do jogo
            self.game_state = message.content

            # Se o jogo começou, mudar para a view do jogo
            if self.game_state["state"] not in ["WAITING_FOR_PLAYERS"]:
                self.current_view = "game"

        elif message.msg_type == MessageType.JOIN_REQUEST and self.host_mode:
            # Processar solicitação de entrada (apenas o host)
            player_id = message.content["player_id"]
            player_name = message.content["player_name"]

            # Criar novo jogador e adicionar ao jogo
            new_player = Player(player_name, 1000, player_id)
            success, player_index = self.game.add_player(new_player)

            # Enviar resposta
            response = Message.create_join_response(
                self.player.player_id,
                success,
                self.game.game_id if success else None,
                "Jogo já iniciado" if not success else None
            )
            self.p2p_manager.send_message(response, player_id)

            # Atualizar lobby no matchmaking service
            player_list = [p.name for p in self.game.state_manager.players]
            self.matchmaking_service.update_lobby(self.game.game_id, player_list)

            # Enviar estado atualizado do jogo para todos
            self.broadcast_game_state()

        elif message.msg_type == MessageType.JOIN_RESPONSE and not self.host_mode:
            # Processar resposta de solicitação de entrada
            if message.content["accepted"]:
                print(f"Entrou no jogo {message.content['game_id']}")
            else:
                print(f"Falha ao entrar no jogo: {message.content['reason']}")
                self.current_view = "menu"

        elif message.msg_type == MessageType.PLAYER_ACTION:
            # Processar ação do jogador (apenas o host)
            if self.host_mode:
                self.process_player_action(sender_id, message.content)

    def on_player_connected(self, player_id, player_data):
        """Callback para quando um novo jogador se conecta"""
        print(f"Jogador conectado: {player_id}")

    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")

        # Se somos o host, remover o jogador do jogo
        if self.host_mode and self.game:
            self.game.remove_player(player_id)
            self.broadcast_game_state()

    def process_player_action(self, player_id, action_data):
        """Processar uma ação de jogador (host)"""
        action_type = action_data["action_type"]
        action_data = action_data["action_data"]

        if action_type == ActionType.PLACE_BET:
            success, message = self.game.place_bet(player_id, action_data["amount"])
        elif action_type == ActionType.HIT:
            success, message = self.game.hit(player_id)
        elif action_type == ActionType.STAND:
            success, message = self.game.stand(player_id)
        else:
            success, message = False, "Ação desconhecida"

        # Adicionar mensagem ao jogo
        if success:
            self.game.messages.append(message)

        # Atualizar estado do jogo para todos
        self.broadcast_game_state()

    def broadcast_game_state(self):
        """Enviar o estado atual do jogo para todos os jogadores"""
        if self.host_mode and self.game:
            self.game_state = self.game.get_game_state()
            if hasattr(self, 'p2p_manager') and self.p2p_manager:  # Only send messages in multiplayer mode
                game_state_message = Message.create_game_state_message(
                    self.player.player_id,
                    self.game_state
                )
                self.p2p_manager.send_message(game_state_message)

    def hit(self):
        """Pedir mais uma carta"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            hit_message = Message.create_action_message(
                self.player.player_id,
                ActionType.HIT
            )
            self.p2p_manager.send_message(hit_message)
        else:
            # Host processa diretamente
            success, message = self.game.hit(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def stand(self):
        """Parar de pedir cartas"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            stand_message = Message.create_action_message(
                self.player.player_id,
                ActionType.STAND
            )
            self.p2p_manager.send_message(stand_message)
        else:
            # Host processa diretamente
            success, message = self.game.stand(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def place_bet(self):
        """Envia a aposta do jogador para o servidor."""
        if self.current_view == "game" and self.game_state and self.game_state.get("state") == "BETTING":
            # Verificar se é a vez do jogador (ou se apostas são simultâneas)
            # Aqui, assumimos que o jogador pode apostar se o estado for BETTING
            if self.websocket_client and self.websocket_client.is_connected() and self.room_id:
                print(f"Enviando aposta: {self.bet_amount} para sala {self.room_id}")
                payload = {
                    "roomId": self.room_id,
                    "amount": self.bet_amount
                    # O servidor identificará o jogador pelo ID da conexão/jogador
                }
                if self.send_websocket_message("PLACE_BET", payload):
                    self.success_message = f"Aposta de {self.bet_amount} enviada."
                    self.message_timer = pygame.time.get_ticks()
                    # Opcional: Atualizar status local do jogador para 'Apostou' ou aguardar confirmação
                    # Ex: self.game_state['players'][my_index]['status'] = 'Bet Placed'
                else:
                    self.error_message = "Falha ao enviar aposta."
                    self.message_timer = pygame.time.get_ticks()
            else:
                self.error_message = "Não conectado ou fora de uma sala para apostar."
                self.message_timer = pygame.time.get_ticks()
        else:
            print("Não é possível apostar agora (view ou estado incorreto).")

    def start_game(self):
        """Inicia o jogo (se for o host) e notifica o servidor."""
        if not self.host_mode:
            print("Apenas o host pode iniciar o jogo.")
            self.error_message = "Aguardando o host iniciar o jogo."
            self.message_timer = pygame.time.get_ticks()
            return

        if len(self.lobby_players) < 1: # Mínimo 1 (host)
             print("Não há jogadores suficientes para iniciar.")
             self.error_message = "Jogadores insuficientes."
             self.message_timer = pygame.time.get_ticks()
             return

        print("Iniciando jogo como host...")
        # Cria a instância do jogo local
        self.game = Game() 

        # Adiciona os jogadores atuais do lobby ao jogo
        if not self.player: 
             self.error_message = "Erro interno: Host não definido."
             self.message_timer = pygame.time.get_ticks()
             print("Erro: Tentando iniciar jogo sem self.player definido.")
             # Tenta criar o player novamente se não existir por algum motivo
             if self.player_id and self.player_name:
                 self.player = Player(self.player_name, self.player_balance, self.player_id)
        else:
                 self.current_view = "menu" # Volta pro menu se não tem dados do host
                 return
        
        # Adiciona jogadores ao objeto Game
        players_added_to_game = []
        for player_info in self.lobby_players:
            player_id = player_info.get('id')
            player_name = player_info.get('name')
            if player_id and player_name:
                # Se for o host, usa o objeto self.player já existente
                if player_id == self.player_id:
                    if self.player not in players_added_to_game: # Evita duplicar
                         self.game.add_player(self.player) 
                         players_added_to_game.append(self.player)
                         print(f"Adicionado host ao jogo: {self.player.name} ({self.player.player_id})")
                else:
                    # Cria objetos Player para os outros (saldo inicial padrão?)
                    other_player = Player(player_name, 1000, player_id)
                    if other_player not in players_added_to_game:
                         self.game.add_player(other_player)
                         players_added_to_game.append(other_player)
                         print(f"Adicionado jogador ao jogo: {other_player.name} ({other_player.player_id})")
            else:
                 print(f"Aviso: Informação inválida para jogador no lobby: {player_info}")

        if not self.game.players: # Verifica se pelo menos um jogador foi adicionado
             self.error_message = "Erro ao adicionar jogadores ao jogo."
             self.message_timer = pygame.time.get_ticks()
             print("Erro: Nenhum jogador adicionado ao objeto Game.")
             self.game = None # Reseta se deu erro
             return

        # Inicia a lógica do jogo localmente 
        # self.game.initialize_game(self.player) # Passa o host ou a lista?
        # Adaptação: initialize_game pode não ser necessário se add_player configura
        self.game.dealer_hand = [] # Garante que mão do dealer está vazia
        self.game.deal_initial_cards() # Exemplo: distribuir cartas iniciais
        self.game_state = self.game.get_game_state() # Pega o estado inicial

        print("Jogo inicializado localmente. Notificando servidor...")
        # Envia mensagem para o servidor indicando que o jogo começou
        payload = {"roomId": self.room_id}
        self.send_websocket_message("START_GAME", payload)

        # Muda para a tela de jogo
        self.current_view = "game"
        self.success_message = "Jogo iniciado!"
        self.message_timer = pygame.time.get_ticks()

    def new_round(self):
        """Envia comando NEW_ROUND para o servidor (se for o host).""" # Descrição atualizada
        # No modo online, apenas o host (ou o servidor automaticamente) inicia nova rodada.
        # O cliente apenas renderiza o estado recebido. No máximo, o host envia um comando.
        if self.current_view == "game" and self.game_state and self.game_state.get("state") == "GAME_OVER":
            # Simplificação: Qualquer jogador pode tentar iniciar (servidor valida se é host)
            if self.websocket_client and self.websocket_client.is_connected() and self.room_id:
                print(f"Solicitando NOVA RODADA para sala {self.room_id}")
                payload = {"roomId": self.room_id}
                if self.send_websocket_message("NEW_ROUND", payload):
                    self.success_message = "Solicitação de nova rodada enviada."
                    self.message_timer = pygame.time.get_ticks()
                    # O cliente deve aguardar o novo GAME_STATE do servidor
                else:
                    self.error_message = "Falha ao solicitar nova rodada."
                    self.message_timer = pygame.time.get_ticks()
            else:
                self.error_message = "Não conectado ou fora de uma sala."
                self.message_timer = pygame.time.get_ticks()
        else:
            print("Não é possível iniciar nova rodada agora (jogo não acabou?).")

    def leave_lobby(self):
        """Sair do lobby e voltar ao menu (envia comando LEAVE_ROOM)"""
        if self.websocket_client and self.websocket_client.is_connected() and self.room_id:
            print(f"Enviando comando LEAVE_ROOM para sala {self.room_id}")
            self.send_websocket_message("LEAVE_ROOM", {"roomId": self.room_id})
        
        # Limpar estado local
        self.game = None
        self.game_state = None
        self.current_view = "menu"
        self.host_mode = False
        self.room_id = ""
        # Limpar P2P Manager (se ainda existir)
        if self.p2p_manager: ...

    def increase_bet(self):
        """Aumentar o valor da aposta"""
        self.bet_amount += 10
        if self.bet_amount > self.player.balance:
            self.bet_amount = self.player.balance

    def decrease_bet(self):
        """Diminuir o valor da aposta"""
        self.bet_amount -= 10
        if self.bet_amount < 10:
            self.bet_amount = 10

    def create_bot(self, name, strategy="default"):
        """Criar um bot com a estratégia especificada
        Estratégias:
        - default: Para em 17+, pede em 16-
        - aggressive: Para em 18+, pede em 17-
        - conservative: Para em 15+, pede em 14-
        """
        bot_player = Player(name, 1000, str(uuid.uuid4()))
        bot_player.strategy = strategy
        return bot_player

    def start_single_player(self, num_bots=1):
        """Iniciar jogo single player contra o número selecionado de bots"""
        print(f"Iniciando jogo single player com {self.player_name}, saldo: {self.player_balance}")
        
        # Criar jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Criar novo jogo
        self.game = Game()
        
        # Adicionar jogador humano primeiro (para garantir que começa)
        self.game.initialize_game(self.player)
        
        # Criar e adicionar bots com estratégias diferentes
        bot_names = ["Bot Conservador", "Bot Normal", "Bot Agressivo"]
        bot_strategies = ["conservative", "default", "aggressive"]
        
        # Adicionar apenas o número de bots selecionado
        for i in range(min(num_bots, 3)):
            bot_player = self.create_bot(bot_names[i], bot_strategies[i])
            self.game.add_player(bot_player)
        
        # Configurar como host e iniciar o jogo
        self.host_mode = True
        self.current_view = "game"
        
        # Iniciar o jogo
        self.game.start_game()
        self.game_state = self.game.get_game_state()
        self.game.messages.append(f"Jogo iniciado contra {num_bots} bot(s)!")
        
        # Garantir que as apostas iniciais sejam feitas
        initial_bet = min(100, self.player.balance)  # Não apostar mais do que o jogador tem
        self.game.place_bet(self.player.player_id, initial_bet)  # Aposta inicial do jogador
        
        # Apostas iniciais dos bots
        for player in self.game.state_manager.players:
            if player.player_id != self.player.player_id:
                self.game.place_bet(player.player_id, 100)
        
        # Distribuir cartas iniciais
        self.game._deal_initial_cards()
        self.broadcast_game_state()

    def bot_play(self):
        """Lógica de jogo dos bots"""
        if not self.game_state:
            return

        current_player = self.game_state["players"][self.game_state["currentPlayerIndex"]]
        # Verifique se o jogador atual é um bot (nome começa com "Bot")
        if not current_player["name"].startswith("Bot"):
            return

        # Lógica de apostas do bot
        if self.game_state["state"] == "BETTING":
            # Bot sempre aposta 100
            self.game.place_bet(current_player["id"], 100)
            self.game.messages.append(f"{current_player['name']} apostou 100")
            self.broadcast_game_state()
            return

        # Lógica de jogo do bot
        if self.game_state["state"] == "PLAYER_TURN":
            # Verificar se o jogador humano estourou
            human_player = next((p for p in self.game_state["players"] if not p["name"].startswith("Bot")), None)
            if human_player and human_player["is_busted"]:
                # Se o jogador humano estourou, o bot para
                success, message = self.game.stand(current_player["id"])
                if success:
                    self.game.messages.append(f"{current_player['name']} parou")
                self.broadcast_game_state()
                return

            # Esperar um pouco para simular "pensamento"
            time.sleep(0.5)  # Reduzido para manter o jogo fluido com múltiplos bots

            # Encontrar a estratégia do bot atual
            hand_value = current_player["hand_value"]
            bot_player = next((p for p in self.game.state_manager.players if p.player_id == current_player["id"]), None)
            
            if bot_player:
                strategy = getattr(bot_player, "strategy", "default")
                
                # Aplicar estratégia
                limit = 17  # Padrão
                if strategy == "aggressive":
                    limit = 18
                elif strategy == "conservative":
                    limit = 15
                
                if hand_value < limit:
                    success, message = self.game.hit(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} pediu carta")
                else:
                    success, message = self.game.stand(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} parou")

            self.broadcast_game_state()

    def check_winner(self):
        """Verificar o vencedor da rodada"""
        if not self.game_state:
            return

        players = self.game_state["players"]
        
        # Separar jogadores humanos e bots
        human_player = next((p for p in players if not p["name"].startswith("Bot")), None)
        if not human_player:
            return
            
        active_players = [p for p in players if not p["is_busted"]]
        
        # Se todos estouraram, não há vencedor
        if not active_players:
            self.game.messages.append("Todos estouraram! Ninguém ganha.")
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se apenas um jogador não estourou, ele é o vencedor
        if len(active_players) == 1:
            winner = active_players[0]
            self.game.messages.append(f"{winner['name']} venceu! (Único jogador não estourado)")
            
            # Processar resultado (apenas para jogadores humanos)
            if winner["name"] == self.player.name:
                old_balance = self.player.balance
                # Calcular o prêmio (soma de todas as apostas)
                total_pot = sum(p["current_bet"] for p in players)
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance} (ganhou {total_pot})")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
                
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se múltiplos jogadores não estouraram, encontre o maior valor
        max_value = max(p["hand_value"] for p in active_players)
        winners = [p for p in active_players if p["hand_value"] == max_value]
        
        # Anunciar vencedores
        if len(winners) == 1:
            self.game.messages.append(f"{winners[0]['name']} venceu com {max_value} pontos!")
            
            # Processar resultado (apenas para jogadores humanos)
            if winners[0]["name"] == self.player.name:
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
        else:
            winner_names = ", ".join(w["name"] for w in winners)
            self.game.messages.append(f"Empate entre {winner_names} com {max_value} pontos!")
            
            # Verificar se o jogador humano está entre os vencedores
            if any(w["name"] == self.player.name for w in winners):
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} empatou! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
            
        self.game_state["state"] = "GAME_OVER"
        self.broadcast_game_state()

    def render_bot_selection(self):
        """Renderizar a tela de seleção de bots"""
        # Background
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        title = self.title_font.render("Selecione o Número de Bots", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        def draw_selection_button(rect, text, color, hover_color):
            """Desenhar botão de seleção com efeito hover"""
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            
            # Sombra
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pygame.draw.rect(self.screen, (0, 0, 0, 128), shadow_rect, border_radius=15)
            
            # Botão
            current_color = hover_color if is_hover else color
            pygame.draw.rect(self.screen, current_color, rect, border_radius=15)
            
            # Borda
            if is_hover:
                pygame.draw.rect(self.screen, (255, 255, 255, 128), rect, 2, border_radius=15)
            
            # Texto
            text_surface = self.medium_font.render(text, True, (240, 240, 240))
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Botões para selecionar o número de bots
        button_width = 300
        button_height = 60
        button_x = SCREEN_WIDTH // 2 - button_width // 2
        
        # Cores dos botões
        button_colors = [
            ((0, 100, 180), (0, 140, 230)),  # 1 Bot
            ((0, 130, 150), (0, 170, 190)),  # 2 Bots
            ((0, 150, 120), (0, 190, 160)),  # 3 Bots
            ((150, 30, 30), (190, 50, 50))   # Voltar
        ]
        
        # Botão para 1 bot
        bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
        draw_selection_button(bot1_button, "Jogar com 1 Bot", button_colors[0][0], button_colors[0][1])
        
        # Botão para 2 bots
        bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
        draw_selection_button(bot2_button, "Jogar com 2 Bots", button_colors[1][0], button_colors[1][1])
        
        # Botão para 3 bots
        bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
        draw_selection_button(bot3_button, "Jogar com 3 Bots", button_colors[2][0], button_colors[2][1])
        
        # Botão para voltar
        back_button = pygame.Rect(button_x, 460, button_width, button_height)
        draw_selection_button(back_button, "Voltar", button_colors[3][0], button_colors[3][1])
        
        # Descrição dos tipos de bots
        info_y = 550
        info_texts = [
            "Bot Conservador: Para com 15+ pontos",
            "Bot Normal: Para com 17+ pontos",
            "Bot Agressivo: Para com 18+ pontos"
        ]
        
        info_rect = pygame.Rect(SCREEN_WIDTH // 2 - 300, info_y - 20, 600, 150)
        pygame.draw.rect(self.screen, (0, 50, 0), info_rect, border_radius=10)
        pygame.draw.rect(self.screen, (0, 80, 0), info_rect, 2, border_radius=10)
        
        for i, text in enumerate(info_texts):
            info_text = self.small_font.render(text, True, (220, 220, 220))
            text_rect = info_text.get_rect(centerx=SCREEN_WIDTH // 2, y=info_y + i * 30)
            self.screen.blit(info_text, text_rect)

    def render_message(self, message, color):
        """Renderizar uma mensagem temporária na tela"""
        message_surface = self.medium_font.render(message, True, color)
        message_rect = message_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        
        # Fundo semi-transparente
        padding = 10
        bg_rect = pygame.Rect(message_rect.x - padding, message_rect.y - padding, 
                            message_rect.width + padding * 2, message_rect.height + padding * 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 150))
        self.screen.blit(bg_surface, bg_rect)
        
        # Desenhar borda
        pygame.draw.rect(self.screen, color, bg_rect, 2, border_radius=5)
        
        # Desenhar mensagem
        self.screen.blit(message_surface, message_rect)

    def render_join_room(self):
        """Renderizar a tela para juntar-se a uma sala específica usando o ID"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        # Título
        title = self.title_font.render("Juntar-se a uma Sala", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Área central
        form_width = 500
        form_height = 300 # Altura original para caber senha e modo
        form_x = SCREEN_WIDTH // 2 - form_width // 2
        form_y = 150
        
        form_bg = pygame.Rect(form_x, form_y, form_width, form_height)
        pygame.draw.rect(self.screen, (0, 60, 0), form_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), form_bg, 2, border_radius=10)
        
        y_offset = form_y + 30
        
        # ID da Sala (agora Código da Sala)
        id_label = self.medium_font.render("Código da Sala:", True, WHITE) # Texto modificado
        self.screen.blit(id_label, (form_x + 30, y_offset))
        
        # Campo de entrada para o ID/Código da sala
        id_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.room_id_input_active:
            id_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            id_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, (0, 80, 0), id_box, border_radius=5) # Fundo interno do campo
        pygame.draw.rect(self.screen, id_border_color, id_box, 2, border_radius=5) # Borda
        
        # Texto do ID da sala
        cursor = "|" if self.room_id_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        id_text = self.medium_font.render(self.room_id_input + cursor, True, WHITE)
        self.screen.blit(id_text, (id_box.x + 10, id_box.y + 5))
        
        y_offset += 100
        
        # Senha
        password_label = self.medium_font.render("Senha da Sala:", True, WHITE)
        self.screen.blit(password_label, (form_x + 30, y_offset))
        
        # Campo de entrada para a senha
        password_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.password_input_active:
            password_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            password_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, (0, 80, 0), password_box, border_radius=5) # Fundo interno
        pygame.draw.rect(self.screen, password_border_color, password_box, 2, border_radius=5) # Borda
        
        # Texto da senha (mostrado como asteriscos)
        password_display = "*" * len(self.password_input)
        cursor = "|" if self.password_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        password_text = self.medium_font.render(password_display + cursor, True, WHITE)
        self.screen.blit(password_text, (password_box.x + 10, password_box.y + 5))
        
        password_info = self.small_font.render("Deixe em branco para salas sem senha", True, (200, 200, 200))
        self.screen.blit(password_info, (form_x + 30, y_offset + 90))
        
        y_offset += 120
        
        # Seleção de modo de conexão
        # Removido temporariamente para simplificar, restaurar se necessário
        # mode_label = self.medium_font.render("Modo de Conexão:", True, WHITE)
        # self.screen.blit(mode_label, (form_x + 30, y_offset))
        # ... (código dos botões de modo) ...
        
        # Botões de ação (Ajustar Y se modo for removido)
        button_width = 200
        button_height = 50
        button_y = 500 # Posição original
        
        # Botão Buscar Salas (Restaurado)
        mouse_pos = pygame.mouse.get_pos()
        browse_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        browse_color = (0, 130, 180) if browse_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, browse_color, browse_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, browse_button, 2, border_radius=10)
        browse_text = self.medium_font.render("Lista de Salas", True, WHITE)
        browse_text_rect = browse_text.get_rect(center=browse_button.center)
        self.screen.blit(browse_text, browse_text_rect)

        # Botão Entrar
        join_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, join_color, join_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, join_button, 2, border_radius=10)
        join_text = self.medium_font.render("Entrar", True, WHITE)
        join_text_rect = join_text.get_rect(center=join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Botão Cancelar
        cancel_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        cancel_color = (150, 0, 0) if cancel_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, cancel_color, cancel_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, cancel_button, 2, border_radius=10)
        cancel_text = self.medium_font.render("Cancelar", True, WHITE)
        cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
        self.screen.blit(cancel_text, cancel_text_rect)
    
        # Exibir mensagens de erro/sucesso
        self.display_messages()

    def handle_room_browser_event(self, event):
        """Lidar com eventos na tela do navegador de salas"""
        list_item_height = 50 # Ajustar para corresponder à renderização
        list_height = 400 # Ajustar para corresponder à renderização
        visible_items = 6 # Ajustar para corresponder à renderização
        list_x = SCREEN_WIDTH // 2 - 400 # Ajustar para corresponder à renderização
        list_width = 800 # Ajustar para corresponder à renderização
        list_y = 150 # Y inicial da área da lista
        header_y = list_y + 20 # Y onde os cabeçalhos são desenhados

        # Coordenadas dos botões baseadas em render_room_browser
        button_width = 200
        button_height = 50
        button_y = 650
        refresh_button_rect = pygame.Rect(SCREEN_WIDTH - 160, 60, 120, 40)
        create_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        join_id_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        back_button_rect = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        mode_y = 150 + list_height + 20 # list_y + list_height + 20
        online_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
        local_button_rect = pygame.Rect(SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
        scroll_up_button = pygame.Rect(list_x + list_width - 40, 150 + 20, 30, 30) # list_y + 20
        scroll_down_button = pygame.Rect(list_x + list_width - 40, 150 + list_height - 50, 30, 30) # list_y + list_height - 50

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Botão Voltar
            if back_button_rect.collidepoint(mouse_pos):
                self.current_view = "menu"
                # Não desconectar WebSocket aqui, talvez voltar para menu principal?
                # if self.websocket_client:
                #     self.websocket_client.close()
                #     self.websocket_client = None
                #     self.server_status = "Disconnected"
                return

            # Botão Criar Sala
            if create_button_rect.collidepoint(mouse_pos):
                # CORREÇÃO: Enviar comando CREATE_ROOM em vez de ir para tela inexistente
                if self.websocket_client and self.websocket_client.is_connected():
                    print("Solicitando criação de sala ao servidor...")
                    # Usar valores padrão ou pegar de uma UI futura?
                    # Por enquanto, cria sala padrão.
                    payload = { 
                        "roomName": f"Sala de {self.player_name}", # Nome padrão 
                        "password": None, # Sem senha por padrão
                        "maxPlayers": self.max_players 
                    }
                    if self.send_websocket_message("CREATE_ROOM", payload):
                        self.success_message = "Enviando pedido para criar sala..."
                        self.message_timer = pygame.time.get_ticks()
                    else:
                        self.error_message = "Falha ao enviar pedido para criar sala."
                        self.message_timer = pygame.time.get_ticks()
                else:
                    self.error_message = "Não conectado ao servidor."
                    self.message_timer = pygame.time.get_ticks()
                    self.connect_websocket() # Tentar conectar se não estiver
                return

            # Botão Entrar com ID/Código
            if join_id_button_rect.collidepoint(mouse_pos):
                self.current_view = "join_room"
                self.room_id_input = ""
                self.password_input = ""
                self.room_id_input_active = False
                self.password_input_active = False
                return

            # Botão Atualizar Lista
            if refresh_button_rect.collidepoint(mouse_pos):
                self.load_room_list(mode=self.connection_mode)
                return
            
            # Botões de modo
            if online_button_rect.collidepoint(mouse_pos):
                if self.connection_mode != "online":
                    self.connection_mode = "online"
                    self.connect_websocket() # Tenta conectar/reconectar se mudar para online
                    self.load_room_list(mode="online")
                return
            if local_button_rect.collidepoint(mouse_pos):
                 if self.connection_mode != "local":
                    self.connection_mode = "local"
                    if self.websocket_client:
                         self.websocket_client.close()
                         self.websocket_client = None
                    self.load_room_list(mode="local") # Busca local
                 return

            # Selecionar sala da lista ou clicar no botão "Entrar" da linha
            if list_x < mouse_pos[0] < list_x + list_width and 150 + 60 < mouse_pos[1] < 150 + list_height:
                for i in range(visible_items):
                    item_index = self.room_browser_scroll + i
                    if item_index < len(self.room_list):
                        # CORREÇÃO: Calcular item_y e rects como em render_room_browser
                        # item_y agora representa a linha base do texto no item
                        item_y = header_y + 60 + (i * list_item_height) # Usar list_item_height
                        # Rect para detectar clique na linha (excluindo o botão)
                        item_rect = pygame.Rect(list_x + 10, item_y - 5, list_width - 100, list_item_height) # Aproximado
                        # Rect EXATO para o botão "Entrar"
                        join_button_line_rect = pygame.Rect(list_x + 720, item_y - 5, 60, 30)

                        # Verificar clique no botão "Entrar" da linha PRIMEIRO
                        if join_button_line_rect.collidepoint(mouse_pos):
                            self.join_selected_room(item_index) # Chama função para entrar
                            return
                        # Verificar clique na linha (para seleção), se não foi no botão
                        elif item_rect.collidepoint(mouse_pos):
                            self.selected_room_index = item_index
                            print(f"Sala selecionada: {self.room_list[item_index]['name']}")
                            return

            # Botões de Scroll
            if len(self.room_list) > visible_items:
                 if scroll_up_button.collidepoint(mouse_pos):
                     self.room_browser_scroll = max(0, self.room_browser_scroll - 1)
                     return
                 if scroll_down_button.collidepoint(mouse_pos):
                     max_scroll = max(0, len(self.room_list) - visible_items)
                     self.room_browser_scroll = min(max_scroll, self.room_browser_scroll + 1)
                     return

        # Scroll da lista com roda do mouse
        elif event.type == pygame.MOUSEWHEEL:
            if len(self.room_list) > visible_items:
                max_scroll = max(0, len(self.room_list) - visible_items)
                self.room_browser_scroll -= event.y
                self.room_browser_scroll = max(0, min(self.room_browser_scroll, max_scroll))

    def load_room_list(self, mode="online"):
        """Carregar a lista de salas disponíveis via WebSocket."""
        if mode == "online":
            if self.websocket_client and self.websocket_client.is_connected():
                print("Solicitando lista de salas via WebSocket...")
                self.send_websocket_message("LIST_ROOMS")
            else:
                self.error_message = "Não conectado para listar salas."
                self.message_timer = pygame.time.get_ticks()
                # CORRIGIR INDENTAÇÃO: Deve estar dentro do else
                self.connect_websocket() # Tenta conectar
        else:
            self.error_message = "Busca local não implementada."
            self.message_timer = pygame.time.get_ticks()

    def join_selected_room(self, index):
        """Tenta entrar na sala selecionada na lista."""
        if index < 0 or index >= len(self.room_list):
            return
        
        room = self.room_list[index]
        print(f"Tentando entrar na sala selecionada: {room['name']} (ID: {room['id']})")
        
        # Se a sala tiver senha, ir para a tela de join com ID preenchido
        if room.get("hasPassword", False):
            self.room_id_input = room["id"]
            self.password_input = ""
            self.password_input_active = True # Focar na senha
            self.room_id_input_active = False
            self.current_view = "join_room"
            return
        
        # Se não tem senha, entrar diretamente
        # Criar o jogador (se necessário)
        if not self.player:
            # CORRIGIR INDENTAÇÃO: Adicionar indentação
            self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Conectar à sala (chama connect_to_online_room ou connect_to_local_room)
        success = False
        if self.connection_mode == "online":
            success = self.connect_to_online_room(room["id"], None) # Sem senha
        else:
            success = self.connect_to_local_room(room["id"], None) # Sem senha
        
        if success:
             # A mudança de view ocorrerá na resposta do servidor (JOIN_SUCCESS)
            self.success_message = "Tentando conectar à sala..."
            self.message_timer = pygame.time.get_ticks()
        else:
            self.error_message = self.error_message or "Não foi possível enviar pedido para entrar na sala."
            self.message_timer = pygame.time.get_ticks()

    def connect_to_online_room(self, room_id, password=None):
        """Envia comando para entrar em sala online via WebSocket."""
        if not self.websocket_client or not self.websocket_client.is_connected():
            self.error_message = "Não conectado ao servidor WebSocket."
            self.message_timer = pygame.time.get_ticks()
            # CORRIGIR INDENTAÇÃO: Alinhar com as linhas acima
            self.connect_websocket() # Tentar reconectar
            return False

        # Enviar comando JSON (usa None para senha se vazia ou nula)
        payload = {"roomId": room_id, "password": password if password else None}
        if self.send_websocket_message("JOIN_ROOM", payload):
            self.success_message = "Solicitação para entrar na sala enviada..."
            self.message_timer = pygame.time.get_ticks()
            return True # Comando enviado, aguardar resposta
        else:
            self.error_message = "Falha ao enviar solicitação para entrar na sala."
            self.message_timer = pygame.time.get_ticks()
            return False

    def connect_to_local_room(self, room_id, password=None):
        """Conectar a uma sala na rede local usando o ID da sala"""
        # Verificar se o ID da sala foi informado
        if not room_id:
            self.error_message = "ID da sala não informado"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter informações da sala localmente via broadcast UDP
        success, room_info = self.matchmaking_service.get_local_room_info(room_id)
        if not success:
            self.error_message = "Sala não encontrada na rede local"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Verificar senha se necessário
        if room_info.get("hasPassword", False) and room_info.get("password") != password:
            self.error_message = "Senha incorreta"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter endereço do host
        host_address = room_info.get("host_address")
        if not host_address:
            self.error_message = "Endereço do host não disponível"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Configurar conexão P2P como cliente (se não existir)
        if not self.p2p_manager:
            self.p2p_manager = P2PManager(host=False, local_network=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
    
        # Conectar ao host
        connect_success, connection_message = self.p2p_manager.connect_to_host(host_address)
        if not connect_success:
            self.error_message = f"Erro ao conectar ao host: {connection_message}"
            self.message_timer = pygame.time.get_ticks()
            self.p2p_manager.stop() # Parar P2P se falhar
            self.p2p_manager = None
            return False
        
        # Enviar solicitação para entrar na sala
        # Criar jogador se não existir
        if not self.player:
             self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        join_message = Message.create_join_request(
            self.player.player_id,
            self.player.name,
            password=password
        )
        self.p2p_manager.send_message(join_message)
        
        # Registrar entrada no jogo local (opcional)
        # self.matchmaking_service.join_local_game(room_id, self.player_name)
        
        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        return True

    def handle_join_room_event(self, event):
        """Manipular eventos na tela de juntar-se a uma sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # CORRIGIR INDENTAÇÃO: Todo este bloco precisa ser indentado
            mouse_pos = pygame.mouse.get_pos()
            form_x = SCREEN_WIDTH // 2 - 250
            form_y = 150
        
            # Ativar/desativar campos de entrada
            # Campo ID da Sala
            id_box = pygame.Rect(form_x + 30, form_y + 70, 440, 40)
            if id_box.collidepoint(mouse_pos):
                self.room_id_input_active = True
                self.password_input_active = False
            
            # Campo Senha
            password_box = pygame.Rect(form_x + 30, form_y + 170, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_id_input_active = False
            
            # Botões de modo de conexão (Restaurar se a lógica for usada)
            # ... (código comentado) ...
            
            # Botão Buscar Salas
            button_width = 200
            button_height = 50
            button_y = 500
            browse_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if browse_button.collidepoint(mouse_pos):
                self.current_view = "room_browser"
                # self.connection_mode = self.connection_mode_selection # Usar modo padrão ou o que já estava
                self.load_room_list(mode=self.connection_mode)
                return
            
            # Botão Entrar
            join_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
            if join_button.collidepoint(mouse_pos):
                self.join_room_by_id()
                return
            
            # Botão Cancelar
            cancel_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return
                
        # CORRIGIR INDENTAÇÃO: Alinhar com o if event.type == MOUSEBUTTONDOWN
        elif event.type == pygame.KEYDOWN:
            # CORRIGIR INDENTAÇÃO: Indentar sob o elif
            if self.room_id_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_id_input = self.room_id_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_id_input_active = False
                elif len(self.room_id_input) < 8:  # Limitar tamanho do ID
                    # Permitir letras e números (original era só digit, ajustado)
                    if event.unicode.isalnum(): 
                        self.room_id_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:  # Limitar tamanho da senha
                    if event.unicode.isprintable():
                        self.password_input += event.unicode

    def join_room_by_id(self):
        """Entrar na sala usando o ID digitado"""
        if not self.room_id_input:
            self.error_message = "Digite o ID da sala"
            self.message_timer = pygame.time.get_ticks()
            return
        
        # Criar o jogador (se necessário)
        if not self.player:
             self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Conectar à sala baseado no modo selecionado (ou padrão se removido)
        # Usar self.connection_mode (do browser) ou self.connection_mode_selection (local da tela)?
        # Assumindo que se está nesta tela vindo do menu, o modo online é o padrão
        # A lógica original usava connection_mode_selection que só era setado ao clicar nos botões (removidos)
        # Vamos assumir online por padrão aqui.
        mode_to_use = "online" # Simplificado. A lógica de seleção de modo foi removida da UI.

        success = False
        if mode_to_use == "online":
            success = self.connect_to_online_room(self.room_id_input, self.password_input or None)
        else: # modo local (atualmente não alcançável por esta função como está)
            success = self.connect_to_local_room(self.room_id_input, self.password_input or None)
        
        if success:
            # Mudança de view deve ocorrer na resposta JOIN_SUCCESS
            self.success_message = "Tentando entrar na sala..."
            self.message_timer = pygame.time.get_ticks()
        else:
            # Mensagem de erro será definida pelas funções de conexão
            # Garantir que haja uma mensagem de erro se a conexão falhar
            self.error_message = self.error_message or "Falha ao tentar entrar na sala."
            self.message_timer = pygame.time.get_ticks()

    def update_lobby_view(self, players_list=None, add_player=None, remove_player_id=None):
        """Atualiza a representação interna dos jogadores no lobby."""
        # Esta função precisa ser criada ou adaptada para atualizar a UI
        # baseada nas informações recebidas (players_list, add_player, remove_player_id)
        print(f"Atualizando Lobby View: List={players_list}, Add={add_player}, Remove={remove_player_id}")
        # Exemplo: self.lobby_players = ...
        pass # Implementar lógica de UI do lobby

    def connect_websocket(self):
        """Inicia a conexão WebSocket."""
        if self.websocket_client and self.websocket_client.is_connected():
            print("Tentativa de conectar WebSocket, mas já conectado.")
            return

        print("Tentando conectar ao servidor WebSocket...")
        self.server_status = "Connecting..."
        # Formar URL ws:// ou wss://
        ws_schema = "ws://" # Mudar para wss:// se o servidor usar SSL
        ws_url = f"{ws_schema}{self.server_address}/ws"

        # Instanciar e conectar (a classe WebSocketClient será criada depois)
        # A conexão real e o loop de recebimento ocorrerão em background (thread/asyncio)
        self.websocket_client = WebSocketClient(ws_url, self.on_websocket_status, self._message_queue)
        self.websocket_client.connect() # Método connect inicia a thread/loop

    def on_websocket_status(self, status):
        """Callback chamado pelo WebSocketClient para atualizar o status."""
        self.server_status = status
        print(f"Callback on_websocket_status: {status}")
        if status == "Disconnected":
            self.handle_server_disconnect() # Chama handler de desconexão
        elif status == "Connected":
             # Enviar nome após conectar
             self.send_websocket_message("SET_NAME", {"name": self.player_name})
             # Mudar para browser após conectar com sucesso?
             self.current_view = "room_browser"
             self.send_websocket_message("LIST_ROOMS") # Pede lista inicial

    def send_websocket_message(self, msg_type, payload=None):
        """Envia uma mensagem JSON formatada pelo WebSocket."""
        if self.websocket_client and self.websocket_client.is_connected():
            message = {"type": msg_type}
            if payload is not None:
                message["payload"] = payload
            print(f"Enviando WebSocket: {message}")
            return self.websocket_client.send(message) # Método send na classe client
        else:
            print(f"Erro: Não conectado ao WebSocket para enviar {msg_type}")
            self.error_message = "Desconectado. Tente conectar novamente."
            self.message_timer = pygame.time.get_ticks()
            # Tentar reconectar?
            # self.connect_websocket()
            return False
    
    def render_room_browser(self):
        """Renderizar a tela de navegação de salas disponíveis"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        # Título
        mode_text = "Online" if self.connection_mode == "online" else "Rede Local"
        title = self.title_font.render(f"Salas Disponíveis ({mode_text})", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Botão de Atualizar
        refresh_button = pygame.Rect(SCREEN_WIDTH - 160, 60, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        refresh_color = (0, 130, 200) if refresh_button.collidepoint(mouse_pos) else (0, 100, 170)
        pygame.draw.rect(self.screen, refresh_color, refresh_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, refresh_button, 2, border_radius=10)
        refresh_text = self.small_font.render("Atualizar", True, WHITE)
        refresh_text_rect = refresh_text.get_rect(center=refresh_button.center)
        self.screen.blit(refresh_text, refresh_text_rect)
        
        # Área central com a lista de salas
        list_width = 800
        list_height = 400
        list_x = SCREEN_WIDTH // 2 - list_width // 2
        list_y = 150
        
        list_bg = pygame.Rect(list_x, list_y, list_width, list_height)
        pygame.draw.rect(self.screen, (0, 60, 0), list_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), list_bg, 2, border_radius=10)
        
        # Cabeçalhos da lista
        header_y = list_y + 20
        headers = [
            {"text": "ID", "x": list_x + 50, "width": 100},
            {"text": "Nome da Sala", "x": list_x + 150, "width": 300},
            {"text": "Jogadores", "x": list_x + 470, "width": 100},
            {"text": "Protegida", "x": list_x + 590, "width": 120},
            {"text": "", "x": list_x + 720, "width": 80}  # Coluna para o botão Entrar
        ]
        
        for header in headers:
            text = self.medium_font.render(header["text"], True, (220, 220, 220))
            self.screen.blit(text, (header["x"], header_y))
        
        # Desenhar linha de separação
        pygame.draw.line(self.screen, (0, 100, 0), (list_x + 20, header_y + 40), 
                        (list_x + list_width - 20, header_y + 40), 2)
        
        # Mensagem se não houver salas
        if not self.room_list:
            no_rooms_text = self.medium_font.render("Nenhuma sala disponível", True, (200, 200, 200))
            no_rooms_rect = no_rooms_text.get_rect(center=(list_x + list_width // 2, list_y + list_height // 2))
            self.screen.blit(no_rooms_text, no_rooms_rect)
        else:
            # Lista de salas
            item_height = 50 # Renomear de list_item_height para consistência?
            visible_items = 6  # Número de itens visíveis na tela
            start_index = self.room_browser_scroll
            end_index = min(start_index + visible_items, len(self.room_list))
            
            for i in range(start_index, end_index):
                room = self.room_list[i]
                item_y = header_y + 60 + (i - start_index) * item_height
                
                # Destacar a sala selecionada
                if i == self.selected_room_index:
                    selection_rect = pygame.Rect(list_x + 10, item_y - 5, list_width - 20, item_height)
                    pygame.draw.rect(self.screen, (0, 80, 0), selection_rect, border_radius=5)
                
                # ID da sala
                id_text = self.medium_font.render(room["id"], True, WHITE)
                self.screen.blit(id_text, (list_x + 50, item_y))
                
                # Nome da sala
                name_text = self.medium_font.render(room["name"], True, WHITE)
                self.screen.blit(name_text, (list_x + 150, item_y))
                
                # Número de jogadores (Corrigido para playerCount)
                players_text = self.medium_font.render(f"{room['playerCount']}/8", True, WHITE)
                self.screen.blit(players_text, (list_x + 470, item_y))
                
                # Indicação se tem senha (Corrigido para hasPassword)
                has_password = room.get("hasPassword", False)
                password_text = self.medium_font.render("Sim" if has_password else "Não", True, 
                                                       (255, 150, 150) if has_password else (150, 255, 150))
                self.screen.blit(password_text, (list_x + 590, item_y))
                
                # Botão Entrar
                join_button = pygame.Rect(list_x + 720, item_y - 5, 60, 30)
                join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
                pygame.draw.rect(self.screen, join_color, join_button, border_radius=5)
                pygame.draw.rect(self.screen, WHITE, join_button, 1, border_radius=5)
                join_text = self.small_font.render("Entrar", True, WHITE)
                join_text_rect = join_text.get_rect(center=join_button.center)
                self.screen.blit(join_text, join_text_rect)
            
            # Controles de scroll
            if len(self.room_list) > visible_items:
                # Botão para cima
                up_button = pygame.Rect(list_x + list_width - 40, list_y + 20, 30, 30)
                up_color = (0, 130, 200) if up_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, up_color, up_button, border_radius=5)
                up_text = self.medium_font.render("▲", True, WHITE)
                up_text_rect = up_text.get_rect(center=up_button.center)
                self.screen.blit(up_text, up_text_rect)
                
                # Botão para baixo
                down_button = pygame.Rect(list_x + list_width - 40, list_y + list_height - 50, 30, 30)
                down_color = (0, 130, 200) if down_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, down_color, down_button, border_radius=5)
                down_text = self.medium_font.render("▼", True, WHITE)
                down_text_rect = down_text.get_rect(center=down_button.center)
                self.screen.blit(down_text, down_text_rect)
        
        # Botões de alternância de modo
        mode_y = list_y + list_height + 20
        
        # Botão de modo Online
        online_button = pygame.Rect(SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
        online_color = (0, 120, 210) if self.connection_mode == "online" else (0, 80, 0)
        pygame.draw.rect(self.screen, online_color, online_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, online_button, 2 if self.connection_mode == "online" else 1, border_radius=10)
        online_text = self.medium_font.render("Online", True, WHITE)
        online_text_rect = online_text.get_rect(center=online_button.center)
        self.screen.blit(online_text, online_text_rect)
        
        # Botão de modo Rede Local
        local_button = pygame.Rect(SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
        local_color = (0, 120, 210) if self.connection_mode == "local" else (0, 80, 0)
        pygame.draw.rect(self.screen, local_color, local_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, local_button, 2 if self.connection_mode == "local" else 1, border_radius=10)
        local_text = self.medium_font.render("Rede Local", True, WHITE)
        local_text_rect = local_text.get_rect(center=local_button.center)
        self.screen.blit(local_text, local_text_rect)
        
        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 650
        
        # Botão Criar Sala
        create_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        create_color = (0, 150, 100) if create_button.collidepoint(mouse_pos) else (0, 120, 80)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)
        
        # Botão Entrar com ID
        join_id_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_id_color = (0, 130, 180) if join_id_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, join_id_color, join_id_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, join_id_button, 2, border_radius=10)
        join_id_text = self.medium_font.render("Entrar com ID", True, WHITE)
        join_id_text_rect = join_id_text.get_rect(center=join_id_button.center)
        self.screen.blit(join_id_text, join_id_text_rect)
        
        # Botão Voltar
        back_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        back_color = (150, 0, 0) if back_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, back_color, back_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, back_button, 2, border_radius=10)
        back_text = self.medium_font.render("Voltar", True, WHITE)
        back_text_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    # <<<< INÍCIO CÓDIGO RESTAURADO display_messages >>>>
    def display_messages(self):
        """Exibe mensagens temporárias de erro ou sucesso na tela."""
        current_time = pygame.time.get_ticks()
        message_duration = 3000 # 3 segundos

        if self.error_message and current_time - self.message_timer < message_duration:
            self.render_message(self.error_message, RED)
            # Limpar a mensagem de sucesso para evitar sobreposição
            self.success_message = ""
        elif self.success_message and current_time - self.message_timer < message_duration:
            self.render_message(self.success_message, (0, 200, 0)) # Verde para sucesso
            # Limpar a mensagem de erro
            self.error_message = ""
        # CORRIGIR INDENTAÇÃO: Alinhar com if/elif
        else:
            # Limpar ambas as mensagens se o tempo expirou
            self.error_message = ""
            self.success_message = ""
    # <<<< FIM CÓDIGO RESTAURADO display_messages >>>>

    # --- NOVO HANDLER --- #
    def handle_confirm_leave_game_event(self, event):
         """Lida com eventos na tela de confirmação para sair do jogo."""
         if event.type == pygame.MOUSEBUTTONDOWN:
             mouse_pos = event.pos
             
             # Definir retângulos dos botões (devem corresponder a render_confirm_leave_game)
             popup_width = 400
             popup_height = 200
             popup_x = SCREEN_WIDTH // 2 - popup_width // 2
             popup_y = SCREEN_HEIGHT // 2 - popup_height // 2
             button_width = 150
             button_height = 50
             button_y = popup_y + popup_height - 70
             
             yes_button_rect = pygame.Rect(popup_x + 30, button_y, button_width, button_height)
             no_button_rect = pygame.Rect(popup_x + popup_width - button_width - 30, button_y, button_width, button_height)

             # Verificar clique no botão "Sim, Sair"
             if yes_button_rect.collidepoint(mouse_pos):
                 print("Confirmado: Sair da partida.")
                 # Enviar comando LEAVE_ROOM se estiver online
                 if self.websocket_client and self.websocket_client.is_connected() and self.room_id:
                     self.send_websocket_message("LEAVE_ROOM", {"roomId": self.room_id})
                 
                 # Limpar estado local e voltar ao menu
                 self.game = None # Limpa jogo single player
                 self.game_state = None
                 self.room_id = ""
                 self.lobby_players = []
                 self.host_mode = False
                 self.current_view = "menu"
                 self.success_message = "Você saiu da partida."
                 self.message_timer = pygame.time.get_ticks()
                 return

             # Verificar clique no botão "Não, Voltar"
             if no_button_rect.collidepoint(mouse_pos):
                 print("Cancelado: Voltar ao jogo.")
                 self.current_view = "game"
                 return
                 
             # Se clicar fora do popup, considerar como cancelar? (Opcional)
             # popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
             # if not popup_rect.collidepoint(mouse_pos):
             #      self.current_view = "game"
             #      return

    # --- NOVA FUNÇÃO DE RENDERIZAÇÃO --- #
    def render_confirm_leave_game(self):
         """Renderiza o pop-up de confirmação para sair do jogo."""
         # Fundo escurecido
         overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
         overlay.fill((0, 0, 0, 180)) # Preto semi-transparente
         self.screen.blit(overlay, (0, 0))

         # Janela do Pop-up
         popup_width = 400
         popup_height = 200
         popup_x = SCREEN_WIDTH // 2 - popup_width // 2
         popup_y = SCREEN_HEIGHT // 2 - popup_height // 2
         popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
         
         pygame.draw.rect(self.screen, (0, 60, 0), popup_rect, border_radius=15)
         pygame.draw.rect(self.screen, WHITE, popup_rect, 3, border_radius=15)

         # Mensagem de Confirmação
         title_font = self.medium_font
         text_font = self.small_font
         
         title_text = title_font.render("Sair da Partida?", True, WHITE)
         title_rect = title_text.get_rect(center=(popup_rect.centerx, popup_y + 40))
         self.screen.blit(title_text, title_rect)

         message_text = text_font.render("Tem certeza que deseja sair?", True, (200, 200, 200))
         message_rect = message_text.get_rect(center=(popup_rect.centerx, popup_y + 80))
         self.screen.blit(message_text, message_rect)
         
         message_text2 = text_font.render("(O progresso atual será perdido)", True, (200, 200, 200))
         message_rect2 = message_text2.get_rect(center=(popup_rect.centerx, popup_y + 100))
         self.screen.blit(message_text2, message_rect2)

         # Botões Sim/Não
         button_width = 150
         button_height = 50
         button_y = popup_y + popup_height - 70
         mouse_pos = pygame.mouse.get_pos()

         # Botão Sim
         yes_button_rect = pygame.Rect(popup_x + 30, button_y, button_width, button_height)
         yes_color = (180, 0, 0) if yes_button_rect.collidepoint(mouse_pos) else (140, 0, 0)
         pygame.draw.rect(self.screen, yes_color, yes_button_rect, border_radius=10)
         pygame.draw.rect(self.screen, WHITE, yes_button_rect, 2, border_radius=10)
         yes_text = self.medium_font.render("Sim, Sair", True, WHITE)
         yes_text_rect = yes_text.get_rect(center=yes_button_rect.center)
         self.screen.blit(yes_text, yes_text_rect)

         # Botão Não
         no_button_rect = pygame.Rect(popup_x + popup_width - button_width - 30, button_y, button_width, button_height)
         no_color = (0, 150, 0) if no_button_rect.collidepoint(mouse_pos) else (0, 120, 0)
         pygame.draw.rect(self.screen, no_color, no_button_rect, border_radius=10)
         pygame.draw.rect(self.screen, WHITE, no_button_rect, 2, border_radius=10)
         no_text = self.medium_font.render("Não, Voltar", True, WHITE)
         no_text_rect = no_text.get_rect(center=no_button_rect.center)
         self.screen.blit(no_text, no_text_rect)

if __name__ == "__main__":
    # Verificar se o arquivo de dados do jogador existe, se não, criar com saldo inicial
    data_file = os.path.join(os.path.dirname(__file__), 'player_data.txt')
    if not os.path.exists(data_file):
        try:
            with open(data_file, 'w') as f:
                 # Escreve um jogador padrão se o arquivo não existir
                 default_data = {"Player": 1000} # Saldo inicial de 1000
                 json.dump(default_data, f)
            print(f"Arquivo {data_file} criado com jogador padrão.")
        except Exception as e:
             print(f"Erro ao criar arquivo de dados inicial: {e}")

    client = BlackjackClient()
    client.start()

