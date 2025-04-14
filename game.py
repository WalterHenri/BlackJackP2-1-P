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
        
        # Initialize subsystems
        self.network = NetworkManager(self)
        self.renderer = GameRenderer(self.screen, self.font, self.small_font)
        self.event_handler = EventHandler(self)
        self.sound_manager = SoundManager(self.settings)
        
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
        
        # Reseta o estado do jogo no renderer
        self.renderer.reset_game_state()
        
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
            
            # Check if game is over - finaliza a partida imediatamente se o jogador remoto estourar
            if self.remote_player.status == "busted":
                self.game_state = GameState.GAME_OVER
            elif self.local_player.status != "playing" and self.remote_player.status != "playing":
                self.game_state = GameState.GAME_OVER
        
        elif message.get('type') == 'restart_game':
            # O host iniciou um novo jogo, então reiniciamos também
            # A diferença é que não enviamos mensagem de reinício de volta (para evitar loop)
            self.deck = create_sprite_deck()
            self.local_player = Player("You")
            self.remote_player = Player("Opponent")
            
            # Reseta o estado do jogo no renderer
            self.renderer.reset_game_state()
            
            # Atualiza o estado do jogo
            self.game_state = GameState.PLAYING
            
            # Não precisamos distribuir as cartas iniciais aqui, pois o host fará isso e enviará via game_state

        elif message.get('type') == 'host_left':
            # O host saiu da mesa, então também devemos voltar para a lista de salas
            print("O host saiu da mesa. Retornando para a lista de salas.")
            self.network.close_connection()
            self.game_state = GameState.ROOM_LIST
            self.room_client.list_rooms()
    
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
            # Reproduz o som da carta sendo puxada
            self.sound_manager.play_card_sound()
            
            # Adiciona uma nova carta à mão do jogador
            self.local_player.hit(self.deck)
            self.network.send_message({'type': 'hit'})
            self.network.send_game_state(self.local_player)
            
            # Check if busted - finaliza a partida imediatamente se o jogador local estourar
            if self.local_player.status == "busted":
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
        
        # Reseta o estado do jogo no renderer
        self.renderer.reset_game_state()
        
        # Atualiza o estado do jogo
        self.game_state = GameState.PLAYING
        
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
            
            # Verifica mudanças de estado para iniciar/parar música
            self.check_game_state_for_music()
            
            # Verifica se a música terminou e toca a próxima
            self.sound_manager.check_music_ended()
            
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
                self.renderer.draw_game(self.local_player, self.remote_player)
            elif self.game_state == GameState.GAME_OVER:
                # Desenha o jogo primeiro (para mostrar as cartas)
                self.renderer.draw_game(self.local_player, self.remote_player)
                # Depois desenha o painel de fim de jogo, passando se é host ou não
                is_host = self.network.is_host if hasattr(self.network, 'is_host') else False
                self.renderer.draw_game_over(self.determine_winner(), is_host)
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # Limpeza ao encerrar
        self.sound_manager.stop_music()
        self.network.close_connection()
        self.room_client.disconnect()
        pygame.quit()
        sys.exit()
    
    def check_game_state_for_music(self):
        """
        Verifica mudanças de estado do jogo para iniciar ou parar a música de fundo
        """
        # Estados onde a música deve tocar
        music_states = [GameState.WAITING, GameState.PLAYING]
        
        # Se estamos em um estado onde a música deve tocar
        if self.game_state in music_states:
            self.sound_manager.check_music_ended()
        # Se não estamos em um estado de música e não é a tela de configurações
        elif self.game_state != GameState.SETTINGS:
            # Parar música se estiver tocando
            if pygame.mixer.music.get_busy():
                self.sound_manager.stop_music() 