import pygame
import sys
import socket
from constants import *
from card import Deck, Card
from cards import create_sprite_deck
from player import Player
from menu import Menu
from settings import Settings
from network import NetworkManager
from renderer import GameRenderer
from event_handler import EventHandler
from room_client import RoomClient
from room_menu import RoomMenu
from sound_manager import SoundManager

class BlackjackGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("P2P Blackjack")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)
        
        self.game_state = GameState.MENU
        self.menu = Menu(self.screen, self.font, self.small_font)
        self.room_menu = RoomMenu(self.screen, self.font, self.small_font)
        self.settings = Settings(self.screen, self.font, self.small_font)
        
        # Game components will be initialized when starting a game
        self.deck = None
        self.local_player = None
        self.remote_player = None
        
        # Inicializa o gerenciador de sons com as configurações
        self.sound_manager = SoundManager(self.settings)
        
        # Initialize subsystems
        self.network = NetworkManager(self)
        self.renderer = GameRenderer(self.screen, self.font, self.small_font)
        self.event_handler = EventHandler(self)
        
        # Room client para comunicação com o servidor de salas
        self.room_client = RoomClient(ROOM_SERVER_HOST, ROOM_SERVER_PORT)
        self.room_client.set_callback(self.handle_room_server_message)
        
        # Tenta conectar ao servidor de salas
        try:
            self.room_client.connect()
        except:
            print("Não foi possível conectar ao servidor de salas")
    
    def initialize_game(self, is_host, peer_address=None):
        # Usa o SpriteDeck em vez do Deck padrão
        self.deck = create_sprite_deck()
        self.local_player = Player("You")
        self.remote_player = Player("Opponent")
        
        # Inicializa o controle de turnos
        # O host sempre começa jogando
        self.is_local_turn = is_host
        
        # Networking setup
        self.network.setup_network(is_host, peer_address)
        
        if is_host:
            self.game_state = GameState.WAITING
        else:
            # Client immediately tries to connect
            self.game_state = GameState.PLAYING
    
    def deal_initial_cards(self):
        # Deal two cards to each player
        for _ in range(2):
            self.local_player.hit(self.deck)
            self.remote_player.hit(self.deck)
        
        # Send initial state to the other player
        self.network.send_game_state(self.local_player)
    
    def handle_message(self, message):
        msg_type = message.get('type', 'unknown')
        print(f"Recebida mensagem do tipo: {msg_type}")
        
        if msg_type == 'game_state':
            # Update remote player's hand and status
            remote_hand = message.get('hand', [])
            
            # Recria as cartas a partir dos dados recebidos
            # Precisamos usar Card em vez de CardSprite porque não temos a sprite do lado do cliente
            self.remote_player.hand = []
            for card_data in remote_hand:
                card_value = card_data['value']
                card_suit = card_data['suit']
                
                # Cria uma carta normal (Card) para cada carta recebida
                card = Card(card_value, card_suit)
                self.remote_player.hand.append(card)
            
            self.remote_player.status = message.get('status', 'playing')
            self.remote_player.calculate_score()
            
            # Se o oponente estourou, o jogo termina imediatamente
            if self.remote_player.status == "busted":
                print("Oponente estourou! Finalizando o jogo.")
                self.game_state = GameState.GAME_OVER
            # Se ambos pararam, o jogo também termina
            elif self.local_player.status != "playing" and self.remote_player.status != "playing":
                self.game_state = GameState.GAME_OVER
        
        elif msg_type == 'restart_game':
            # O host iniciou um novo jogo, então reiniciamos também
            # A diferença é que não enviamos mensagem de reinício de volta (para evitar loop)
            self.deck = create_sprite_deck()
            self.local_player = Player("You")
            self.remote_player = Player("Opponent")
            self.game_state = GameState.PLAYING
            # Para o cliente, é a vez do host jogar no início
            self.is_local_turn = False
            print("Jogo reiniciado pelo host. Aguardando primeiro turno do host.")
            
        elif msg_type == 'host_left':
            # O host saiu da mesa, então também devemos voltar para a lista de salas
            print("O host saiu da mesa. Retornando para a lista de salas.")
            self.network.close_connection()
            self.game_state = GameState.ROOM_LIST
            self.room_client.list_rooms()
            
        elif msg_type == 'end_turn':
            # O oponente encerrou seu turno, agora é nossa vez
            print("Mensagem de fim de turno recebida. Agora é a nossa vez de jogar.")
            self.is_local_turn = True
            
        elif msg_type == 'hit':
            print("Oponente pediu mais uma carta")
            
        elif msg_type == 'stand':
            print("Oponente decidiu parar")
    
    def handle_room_server_message(self, message):
        """Processa mensagens do servidor de salas"""
        command = message.get('command')
        
        if command == 'room_list':
            # Atualizar lista de salas
            self.room_menu.update_rooms(message.get('rooms', []))
        
        elif command == 'room_created':
            # Sala criada com sucesso, guardar o ID
            self.room_client.set_room_id(message.get('room_id'))
            
            # Iniciar jogo como host
            self.initialize_game(is_host=True)
        
        elif command == 'join_success':
            # Conseguiu entrar na sala, iniciar jogo como cliente
            host_ip = message.get('host_ip')
            self.initialize_game(is_host=False, peer_address=host_ip)
        
        elif command == 'join_failed':
            # Falha ao entrar na sala, mostrar mensagem de erro
            print(f"Falha ao entrar na sala: {message.get('reason')}")
            # Voltar para o menu de salas
            self.game_state = GameState.ROOM_LIST
            # Atualizar lista de salas
            self.room_client.list_rooms()
    
    def hit(self):
        if self.game_state == GameState.PLAYING and self.local_player.status == "playing" and self.is_local_turn:
            # Reproduz o som de carta
            self.sound_manager.play_card_sound()
            
            # Processa a ação de pedir carta
            self.local_player.hit(self.deck)
            self.network.send_message({'type': 'hit'})
            self.network.send_game_state(self.local_player)
            
            # Check if busted
            if self.local_player.status == "busted":
                # Se o jogador estourar, o jogo termina imediatamente
                print("Jogador local estourou! Finalizando o jogo.")
                self.game_state = GameState.GAME_OVER
            else:
                # Apenas passa o turno se não estourou
                self.end_turn()
    
    def stand(self):
        if self.game_state == GameState.PLAYING and self.local_player.status == "playing" and self.is_local_turn:
            self.local_player.stand()
            self.network.send_message({'type': 'stand'})
            self.network.send_game_state(self.local_player)
            
            # Check if game is over
            if self.remote_player.status != "playing":
                self.game_state = GameState.GAME_OVER
            else:
                # Após parar, o turno passa para o oponente
                self.end_turn()
    
    def end_turn(self):
        # Encerra o turno atual e passa para o oponente
        self.is_local_turn = False
        # Avisa o oponente que agora é a vez dele
        print(f"Enviando mensagem de fim de turno para o oponente")
        self.network.send_message({'type': 'end_turn'})
    
    def determine_winner(self):
        if self.local_player.status == "busted":
            return "Oponente venceu!"
        elif self.remote_player.status == "busted":
            return "Você venceu!"
        elif self.local_player.score > self.remote_player.score:
            return "Você venceu!"
        elif self.remote_player.score > self.local_player.score:
            return "Oponente venceu!"
        else:
            return "Empate!"
    
    def restart_game(self):
        # Usa o SpriteDeck em vez do Deck padrão
        self.deck = create_sprite_deck()
        self.local_player = Player("You")
        self.remote_player = Player("Opponent")
        self.game_state = GameState.PLAYING
        
        # O host sempre começa jogando quando reinicia o jogo
        if hasattr(self.network, 'is_host'):
            self.is_local_turn = self.network.is_host
            
        # Envia mensagem para o oponente informando que o jogo foi reiniciado
        if hasattr(self.network, 'is_host') and self.network.is_host:
            self.network.send_message({'type': 'restart_game'})
        
        # Distribui as cartas iniciais
        self.deal_initial_cards()
    
    def handle_menu_update(self):
        """Atualiza o jogo baseado nas ações do menu"""
        if self.game_state == GameState.ROOM_LIST:
            self.room_menu.draw_room_list()
        elif self.game_state == GameState.CREATE_ROOM:
            self.room_menu.draw_create_room()
    
    def handle_room_list_action(self, action):
        """Processa ações da tela de lista de salas"""
        if action == "refresh":
            self.room_client.list_rooms()
        
        elif action == "create_room":
            self.game_state = GameState.CREATE_ROOM
            self.room_menu.room_name_input = ""
            self.room_menu.room_name_active = True
        
        elif action == "join_room":
            selected_room = self.room_menu.get_selected_room()
            if selected_room:
                self.room_client.join_room(selected_room['id'])
        
        elif action == "back":
            self.game_state = GameState.MENU
    
    def handle_create_room_action(self, action):
        """Processa ações da tela de criação de sala"""
        if action == "confirm_create":
            room_name = self.room_menu.room_name_input
            if room_name:
                # Usar o IP atual como o IP do host
                host_ip = socket.gethostbyname(socket.gethostname())
                self.room_client.create_room(room_name, host_ip)
        
        elif action == "back":
            self.game_state = GameState.ROOM_LIST
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Menu screen events
                if self.game_state == GameState.MENU:
                    self.event_handler.handle_menu_events(event)
                
                # Settings screen events
                elif self.game_state == GameState.SETTINGS:
                    self.event_handler.handle_settings_events(event)
                
                # Room list events
                elif self.game_state == GameState.ROOM_LIST:
                    action = self.room_menu.handle_room_list_event(event)
                    if action:
                        self.handle_room_list_action(action)
                
                # Create room events
                elif self.game_state == GameState.CREATE_ROOM:
                    action = self.room_menu.handle_create_room_event(event)
                    if action:
                        self.handle_create_room_action(action)
                
                # Join screen events
                elif self.game_state == GameState.JOIN_SCREEN:
                    self.event_handler.handle_join_screen_events(event)
                
                # Waiting screen events
                elif self.game_state == GameState.WAITING:
                    self.event_handler.handle_waiting_screen_events(event)
                
                # Game events
                elif self.game_state == GameState.PLAYING:
                    self.event_handler.handle_playing_events(event)
                
                # Game over events
                elif self.game_state == GameState.GAME_OVER:
                    self.event_handler.handle_game_over_events(event)
            
            # Draw
            if self.game_state == GameState.MENU:
                self.menu.draw_menu()
            elif self.game_state == GameState.SETTINGS:
                self.settings.draw()
            elif self.game_state == GameState.ROOM_LIST:
                self.room_menu.draw_room_list()
            elif self.game_state == GameState.CREATE_ROOM:
                self.room_menu.draw_create_room()
            elif self.game_state == GameState.JOIN_SCREEN:
                self.menu.draw_join_screen()
            elif self.game_state == GameState.WAITING:
                self.renderer.draw_waiting_screen(self.menu)
            elif self.game_state == GameState.PLAYING:
                self.renderer.draw_game(self.local_player, self.remote_player, self.is_local_turn)
            elif self.game_state == GameState.GAME_OVER:
                # Desenha o jogo primeiro (para mostrar as cartas)
                self.renderer.draw_game(self.local_player, self.remote_player, False)  # Em game over, ninguém está jogando
                # Depois desenha o painel de fim de jogo, passando se é host ou não
                is_host = self.network.is_host if hasattr(self.network, 'is_host') else False
                self.renderer.draw_game_over(self.determine_winner(), is_host)
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # Limpeza ao encerrar
        self.network.close_connection()
        self.room_client.disconnect()
        pygame.quit()
        sys.exit() 