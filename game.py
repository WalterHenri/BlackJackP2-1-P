import pygame
import sys
import socket
from constants import *
from card import Deck, Card
from player import Player
from menu import Menu
from network import NetworkManager
from renderer import GameRenderer
from event_handler import EventHandler
from room_client import RoomClient
from room_menu import RoomMenu

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
        
        # Game components will be initialized when starting a game
        self.deck = None
        self.local_player = None
        self.remote_player = None
        
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
        self.deck = Deck()
        self.local_player = Player("You")
        self.remote_player = Player("Opponent")
        
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
        if message.get('type') == 'game_state':
            # Update remote player's hand and status
            remote_hand = message.get('hand', [])
            self.remote_player.hand = [Card(card['value'], card['suit']) for card in remote_hand]
            self.remote_player.status = message.get('status', 'playing')
            self.remote_player.calculate_score()
            
            # Check if game is over
            if self.local_player.status != "playing" and self.remote_player.status != "playing":
                self.game_state = GameState.GAME_OVER
    
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
        if self.game_state == GameState.PLAYING and self.local_player.status == "playing":
            self.local_player.hit(self.deck)
            self.network.send_message({'type': 'hit'})
            self.network.send_game_state(self.local_player)
            
            # Check if busted
            if self.local_player.status == "busted":
                if self.remote_player.status != "playing":
                    self.game_state = GameState.GAME_OVER
    
    def stand(self):
        if self.game_state == GameState.PLAYING and self.local_player.status == "playing":
            self.local_player.stand()
            self.network.send_message({'type': 'stand'})
            self.network.send_game_state(self.local_player)
            
            # Check if game is over
            if self.remote_player.status != "playing":
                self.game_state = GameState.GAME_OVER
    
    def determine_winner(self):
        if self.local_player.status == "busted":
            return "Opponent wins!"
        elif self.remote_player.status == "busted":
            return "You win!"
        elif self.local_player.score > self.remote_player.score:
            return "You win!"
        elif self.remote_player.score > self.local_player.score:
            return "Opponent wins!"
        else:
            return "It's a tie!"
    
    def restart_game(self):
        self.deck = Deck()
        self.local_player = Player("You")
        self.remote_player = Player("Opponent")
        self.game_state = GameState.PLAYING
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
            elif self.game_state == GameState.ROOM_LIST:
                self.room_menu.draw_room_list()
            elif self.game_state == GameState.CREATE_ROOM:
                self.room_menu.draw_create_room()
            elif self.game_state == GameState.JOIN_SCREEN:
                self.menu.draw_join_screen()
            elif self.game_state == GameState.WAITING:
                self.renderer.draw_waiting_screen(self.menu)
            elif self.game_state == GameState.PLAYING:
                self.renderer.draw_game(self.local_player, self.remote_player)
            elif self.game_state == GameState.GAME_OVER:
                self.renderer.draw_game(self.local_player, self.remote_player)
                self.renderer.draw_game_over(self.determine_winner())
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # Limpeza ao encerrar
        self.network.close_connection()
        self.room_client.disconnect()
        pygame.quit()
        sys.exit() 