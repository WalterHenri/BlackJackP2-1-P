import socket
import threading
import json
from constants import GameState
from card import Card

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
                    
                    # Distribuir as cartas iniciais para o cliente também
                    self.game.deal_initial_cards()
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