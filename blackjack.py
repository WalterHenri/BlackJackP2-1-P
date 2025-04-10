import pygame
import random
import sys
import socket
import threading
import json
from enum import Enum

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 30
CARD_WIDTH = 100
CARD_HEIGHT = 150
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (100, 149, 237)
GOLD = (255, 215, 0)

class GameState(Enum):
    MENU = 0
    WAITING = 1
    PLAYING = 2
    GAME_OVER = 3
    JOIN_SCREEN = 4

class Card:
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        
    def get_numeric_value(self):
        if self.value in ['J', 'Q', 'K']:
            return 10
        elif self.value == 'A':
            return 11  # In this simple version, Ace is always 11
        else:
            return int(self.value)
    
    def __str__(self):
        return f"{self.value} of {self.suit}"

class Deck:
    def __init__(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(value, suit) for suit in suits for value in values]
        random.shuffle(self.cards)
    
    def draw(self):
        if len(self.cards) > 0:
            return self.cards.pop()
        return None

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.score = 0
        self.status = "playing"  # can be "playing", "standing", "busted"
    
    def hit(self, deck):
        card = deck.draw()
        if card:
            self.hand.append(card)
            self.calculate_score()
            if self.score > 21:
                self.status = "busted"
        return card
    
    def stand(self):
        self.status = "standing"
    
    def calculate_score(self):
        self.score = sum(card.get_numeric_value() for card in self.hand)
        # Simple Ace handling for this version - if bust with Ace, count some Aces as 1
        num_aces = sum(1 for card in self.hand if card.value == 'A')
        while self.score > 21 and num_aces > 0:
            self.score -= 10  # Count an Ace as 1 instead of 11
            num_aces -= 1
        return self.score

class Menu:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.ip_input = ""
        self.ip_input_active = False
        self.port = 5000
        
        # Button dimensions and positions
        button_width = 300
        button_height = 60
        button_margin = 30
        
        self.host_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 - button_height - button_margin,
            button_width, 
            button_height
        )
        
        self.join_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 + button_margin,
            button_width, 
            button_height
        )
        
        self.ip_input_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 200,
            SCREEN_HEIGHT // 2 - 30,
            400,
            60
        )
        
        self.back_button = pygame.Rect(
            50,
            SCREEN_HEIGHT - 100,
            120,
            50
        )
        
        self.connect_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 100,
            SCREEN_HEIGHT // 2 + 60,
            200,
            50
        )
    
    def draw_menu(self):
        # Background
        self.screen.fill(GREEN)
        
        # Title
        title_text = self.font.render("21 Blackjack - P2P", True, GOLD)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Host button
        pygame.draw.rect(self.screen, BLUE, self.host_button, border_radius=5)
        host_text = self.font.render("Host Game", True, WHITE)
        host_text_rect = host_text.get_rect(center=self.host_button.center)
        self.screen.blit(host_text, host_text_rect)
        
        # Join button
        pygame.draw.rect(self.screen, RED, self.join_button, border_radius=5)
        join_text = self.font.render("Join Game", True, WHITE)
        join_text_rect = join_text.get_rect(center=self.join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Instructions
        instructions_text = self.small_font.render("Choose to host a new game or join an existing one", True, WHITE)
        self.screen.blit(instructions_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT - 100))
    
    def draw_join_screen(self):
        # Background
        self.screen.fill(GREEN)
        
        # Title
        title_text = self.font.render("Join Game", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # IP input box
        pygame.draw.rect(self.screen, WHITE, self.ip_input_rect, border_radius=5)
        if self.ip_input_active:
            pygame.draw.rect(self.screen, LIGHT_BLUE, self.ip_input_rect, 3, border_radius=5)
        else:
            pygame.draw.rect(self.screen, BLACK, self.ip_input_rect, 3, border_radius=5)
        
        # IP input text
        ip_text = self.font.render(self.ip_input if self.ip_input else "Enter host IP address", True, 
                                  BLACK if self.ip_input else (150, 150, 150))
        ip_text_rect = ip_text.get_rect(center=self.ip_input_rect.center)
        self.screen.blit(ip_text, ip_text_rect)
        
        # Connect button
        pygame.draw.rect(self.screen, BLUE, self.connect_button, border_radius=5)
        connect_text = self.font.render("Connect", True, WHITE)
        connect_text_rect = connect_text.get_rect(center=self.connect_button.center)
        self.screen.blit(connect_text, connect_text_rect)
        
        # Back button
        pygame.draw.rect(self.screen, RED, self.back_button, border_radius=5)
        back_text = self.font.render("Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect)
        
        # Port text
        port_text = self.small_font.render(f"Port: {self.port}", True, WHITE)
        self.screen.blit(port_text, (SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT // 2 + 120))

class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.socket = None
        self.peer_socket = None
        self.is_connected = False
        self.is_host = False
        self.peer_address = None
    
    def setup_network(self, is_host, peer_address=None):
        self.is_host = is_host
        self.peer_address = peer_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_connected = False
        
        if is_host:
            try:
                self.socket.bind(('0.0.0.0', 5000))
                self.socket.listen(1)
                print("Waiting for opponent to connect...")
                self.connection_thread = threading.Thread(target=self.wait_for_connection)
                self.connection_thread.daemon = True
                self.connection_thread.start()
            except Exception as e:
                print(f"Failed to host: {e}")
                self.game.game_state = GameState.MENU
        else:
            if peer_address:
                try:
                    self.socket.connect((peer_address, 5000))
                    self.peer_socket = self.socket
                    self.is_connected = True
                    print("Connected to host!")
                    
                    # Start receiving messages
                    self.receive_thread = threading.Thread(target=self.receive_messages)
                    self.receive_thread.daemon = True
                    self.receive_thread.start()
                    
                    # Start the game
                    self.game.game_state = GameState.PLAYING
                except Exception as e:
                    print(f"Failed to connect: {e}")
                    self.game.game_state = GameState.MENU
    
    def wait_for_connection(self):
        client_socket, addr = self.socket.accept()
        self.peer_socket = client_socket
        self.is_connected = True
        print(f"Client connected from {addr}")
        
        # Start the game
        self.game.game_state = GameState.PLAYING
        
        # Start dealing initial cards
        self.game.deal_initial_cards()
        
        # Start receiving messages
        self.receive_messages()
    
    def send_message(self, message):
        try:
            self.peer_socket.sendall(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Failed to send message: {e}")
            self.is_connected = False
    
    def receive_messages(self):
        while self.is_connected:
            try:
                data = self.peer_socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                self.game.handle_message(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                self.is_connected = False
                break
    
    def send_game_state(self, player):
        hand_data = [{'value': card.value, 'suit': card.suit} for card in player.hand]
        message = {
            'type': 'game_state',
            'hand': hand_data,
            'status': player.status
        }
        self.send_message(message)
    
    def close_connection(self):
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self.peer_socket = None

class GameRenderer:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        
        # Button dimensions for gameplay
        self.hit_button = pygame.Rect(SCREEN_WIDTH // 4 - 50, SCREEN_HEIGHT - 100, 100, 40)
        self.stand_button = pygame.Rect(3 * SCREEN_WIDTH // 4 - 50, SCREEN_HEIGHT - 100, 100, 40)
    
    def draw_card(self, card, position):
        rect = pygame.Rect(position[0], position[1], CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(self.screen, WHITE, rect)
        pygame.draw.rect(self.screen, BLACK, rect, 2)
        
        color = RED if card.suit in ['Hearts', 'Diamonds'] else BLACK
        card_text = self.font.render(f"{card.value}", True, color)
        suit_text = self.font.render(card.suit[0], True, color)
        
        self.screen.blit(card_text, (position[0] + 10, position[1] + 10))
        self.screen.blit(suit_text, (position[0] + 10, position[1] + 40))
    
    def draw_hand(self, player, is_local):
        y_pos = SCREEN_HEIGHT - 350 if is_local else 50
        label = "Your hand:" if is_local else "Opponent's hand:"
        score_text = f"Score: {player.score}"
        status_text = f"Status: {player.status}"
        
        label_surface = self.font.render(label, True, WHITE)
        score_surface = self.font.render(score_text, True, WHITE)
        status_surface = self.font.render(status_text, True, WHITE)
        
        self.screen.blit(label_surface, (50, y_pos - 40))
        self.screen.blit(score_surface, (50, y_pos - 80))
        self.screen.blit(status_surface, (250, y_pos - 80))
        
        for i, card in enumerate(player.hand):
            self.draw_card(card, (50 + i * 30, y_pos))
    
    def draw_buttons(self):
        pygame.draw.rect(self.screen, GREEN, self.hit_button)
        pygame.draw.rect(self.screen, RED, self.stand_button)
        
        hit_text = self.font.render("Hit", True, WHITE)
        stand_text = self.font.render("Stand", True, WHITE)
        
        self.screen.blit(hit_text, (self.hit_button.x + 35, self.hit_button.y + 10))
        self.screen.blit(stand_text, (self.stand_button.x + 20, self.stand_button.y + 10))
    
    def draw_waiting_screen(self, menu):
        self.screen.fill(GREEN)
        waiting_text = self.font.render("Waiting for opponent to connect...", True, WHITE)
        self.screen.blit(waiting_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2))
        
        ip_info = socket.gethostbyname(socket.gethostname())
        ip_text = self.small_font.render(f"Your IP address: {ip_info}", True, WHITE)
        port_text = self.small_font.render(f"Port: 5000", True, WHITE)
        
        self.screen.blit(ip_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(port_text, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 80))
        
        # Back button
        pygame.draw.rect(self.screen, RED, menu.back_button, border_radius=5)
        back_text = self.font.render("Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=menu.back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    def draw_game_over(self, winner_text):
        game_over_text = self.font.render("Game Over!", True, WHITE)
        result_text = self.font.render(winner_text, True, WHITE)
        restart_text = self.small_font.render("Press R to restart or Q to quit", True, WHITE)
        
        self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(result_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50))
    
    def draw_game(self, local_player, remote_player):
        self.screen.fill(GREEN)
        self.draw_hand(local_player, True)
        self.draw_hand(remote_player, False)
        self.draw_buttons()

class EventHandler:
    def __init__(self, game):
        self.game = game
    
    def handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.host_button.collidepoint(mouse_pos):
                self.game.initialize_game(is_host=True)
            elif self.game.menu.join_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.JOIN_SCREEN
    
    def handle_join_screen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.ip_input_rect.collidepoint(mouse_pos):
                self.game.menu.ip_input_active = True
            else:
                self.game.menu.ip_input_active = False
            
            if self.game.menu.back_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.MENU
            
            if self.game.menu.connect_button.collidepoint(mouse_pos) and self.game.menu.ip_input:
                self.game.initialize_game(is_host=False, peer_address=self.game.menu.ip_input)
        
        if event.type == pygame.KEYDOWN and self.game.menu.ip_input_active:
            if event.key == pygame.K_RETURN:
                if self.game.menu.ip_input:
                    self.game.initialize_game(is_host=False, peer_address=self.game.menu.ip_input)
            elif event.key == pygame.K_BACKSPACE:
                self.game.menu.ip_input = self.game.menu.ip_input[:-1]
            else:
                self.game.menu.ip_input += event.unicode
    
    def handle_waiting_screen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.back_button.collidepoint(mouse_pos):
                self.game.network.close_connection()
                self.game.game_state = GameState.MENU
    
    def handle_playing_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.renderer.hit_button.collidepoint(mouse_pos) and self.game.local_player.status == "playing":
                self.game.hit()
            elif self.game.renderer.stand_button.collidepoint(mouse_pos) and self.game.local_player.status == "playing":
                self.game.stand()
    
    def handle_game_over_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # Restart
                # Reset game
                self.game.restart_game()
            elif event.key == pygame.K_q or event.key == pygame.K_m:  # Quit/Menu
                self.game.network.close_connection()
                self.game.game_state = GameState.MENU

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
        
        # Game components will be initialized when starting a game
        self.deck = None
        self.local_player = None
        self.remote_player = None
        
        # Initialize subsystems
        self.network = NetworkManager(self)
        self.renderer = GameRenderer(self.screen, self.font, self.small_font)
        self.event_handler = EventHandler(self)
    
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
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Menu screen events
                if self.game_state == GameState.MENU:
                    self.event_handler.handle_menu_events(event)
                
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
        
        self.network.close_connection()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = BlackjackGame()
    game.run() 