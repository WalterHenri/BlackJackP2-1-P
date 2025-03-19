import socket
import json
import threading
import time
import uuid

class MatchmakingService:
    def __init__(self):
        self.server_address = "localhost"  # Para produção, usar o endereço real do servidor
        self.server_port = 5000  # Porta padrão para o serviço
        self.local_discovery_port = 5001  # Porta para descoberta na rede local
        self.rooms = {}  # Armazena as informações das salas disponíveis
        self.local_rooms = {}  # Armazena as informações das salas na rede local
        
        # Iniciar thread para descoberta na rede local
        self.local_discovery_running = False
        self.local_discovery_thread = None
        
    def create_game(self, host_name, room_name=None, password=None):
        """Criar uma nova sala de jogo online"""
        try:
            # Em produção, esta função enviaria uma solicitação ao servidor de matchmaking
            # Para fins de demonstração, simularemos uma resposta bem-sucedida
            
            # Gerar ID único para a sala
            game_id = str(uuid.uuid4().int)[:4]  # Pegar os primeiros 4 dígitos
            
            # Usar endereço local e porta aleatória para simulação
            host_address = f"{socket.gethostbyname(socket.gethostname())}:5678"
            
            room_data = {
                "game_id": game_id,
                "host_name": host_name,
                "host_address": host_address,
                "players": [host_name],
                "room_name": room_name or f"Sala de {host_name}",
                "has_password": password is not None,
                "password": password,
                "created_at": time.time()
            }
            
            # Armazenar informações da sala (em produção, isso seria feito no servidor)
            self.rooms[game_id] = room_data
            
            return True, game_id, room_data
        
        except Exception as e:
            return False, None, str(e)
    
    def create_local_game(self, host_name, room_name=None, password=None):
        """Criar uma nova sala de jogo na rede local"""
        try:
            # Gerar ID único para a sala
            game_id = str(uuid.uuid4().int)[:4]  # Pegar os primeiros 4 dígitos
            
            # Usar endereço local
            host_address = f"{socket.gethostbyname(socket.gethostname())}:5678"
            
            room_data = {
                "game_id": game_id,
                "host_name": host_name,
                "host_address": host_address,
                "players": [host_name],
                "room_name": room_name or f"Sala de {host_name}",
                "has_password": password is not None,
                "password": password,
                "created_at": time.time()
            }
            
            # Armazenar informações da sala localmente
            self.local_rooms[game_id] = room_data
            
            # Iniciar broadcast na rede local se ainda não estiver rodando
            if not self.local_discovery_running:
                self.start_local_discovery()
            
            return True, game_id, room_data
        
        except Exception as e:
            return False, None, str(e)
    
    def join_game(self, game_id, password=None):
        """Entrar em uma sala de jogo online"""
        try:
            # Em produção, esta função enviaria uma solicitação ao servidor de matchmaking
            # Para fins de demonstração, simplesmente verificamos se a sala existe localmente
            
            if game_id not in self.rooms:
                return False, "Sala não encontrada"
            
            room = self.rooms[game_id]
            
            # Verificar senha se necessário
            if room.get("has_password", False) and room.get("password") != password:
                return False, "Senha incorreta"
            
            return True, room
        
        except Exception as e:
            return False, str(e)
    
    def join_local_game(self, game_id, password=None):
        """Entrar em uma sala de jogo na rede local"""
        try:
            if game_id not in self.local_rooms:
                return False, "Sala não encontrada na rede local"
            
            room = self.local_rooms[game_id]
            
            # Verificar senha se necessário
            if room.get("has_password", False) and room.get("password") != password:
                return False, "Senha incorreta"
            
            return True, room
        
        except Exception as e:
            return False, str(e)
    
    def list_games(self):
        """Listar todas as salas de jogo disponíveis online"""
        try:
            # Em produção, esta função enviaria uma solicitação ao servidor de matchmaking
            # Para fins de demonstração, retornaremos as salas armazenadas localmente
            
            # Filtrar salas antigas (mais de 30 minutos)
            current_time = time.time()
            active_rooms = [room for room in self.rooms.values() 
                            if current_time - room["created_at"] < 1800]
            
            # Remover senhas antes de enviar para o cliente
            for room in active_rooms:
                room.pop("password", None)
            
            return True, active_rooms
        
        except Exception as e:
            return False, str(e)
    
    def list_local_games(self):
        """Listar todas as salas de jogo disponíveis na rede local"""
        try:
            # Filtrar salas antigas (mais de 30 minutos)
            current_time = time.time()
            active_rooms = [room for room in self.local_rooms.values() 
                            if current_time - room["created_at"] < 1800]
            
            # Remover senhas antes de enviar para o cliente
            for room in active_rooms:
                room.pop("password", None)
            
            return True, active_rooms
        
        except Exception as e:
            return False, str(e)
    
    def update_lobby(self, game_id, players, mode="online"):
        """Atualizar a lista de jogadores em uma sala"""
        try:
            # Em produção, esta função enviaria uma atualização ao servidor de matchmaking
            # Para fins de demonstração, atualizamos localmente
            
            rooms = self.rooms if mode == "online" else self.local_rooms
            
            if game_id not in rooms:
                return False, "Sala não encontrada"
            
            rooms[game_id]["players"] = players
            return True, "Lobby atualizado com sucesso"
        
        except Exception as e:
            return False, str(e)
    
    def leave_game(self, game_id, mode="online"):
        """Sair de uma sala de jogo"""
        try:
            # Em produção, esta função enviaria uma notificação ao servidor de matchmaking
            # Para fins de demonstração, não fazemos nada além de retornar sucesso
            return True, "Saiu da sala com sucesso"
        
        except Exception as e:
            return False, str(e)
    
    def start_local_discovery(self):
        """Iniciar serviço de descoberta na rede local"""
        self.local_discovery_running = True
        self.local_discovery_thread = threading.Thread(target=self._local_discovery_service)
        self.local_discovery_thread.daemon = True
        self.local_discovery_thread.start()
    
    def _local_discovery_service(self):
        """Serviço para anunciar e descobrir jogos na rede local usando UDP broadcast"""
        try:
            # Criação do socket UDP para broadcast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.local_discovery_port))
            
            while self.local_discovery_running:
                # Enviar broadcast de salas disponíveis a cada 5 segundos
                if self.local_rooms:
                    data = json.dumps({
                        "type": "room_broadcast",
                        "rooms": list(self.local_rooms.values())
                    }).encode('utf-8')
                    
                    sock.sendto(data, ('<broadcast>', self.local_discovery_port))
                
                # Esperar 5 segundos
                time.sleep(5)
        
        except Exception as e:
            print(f"Erro no serviço de descoberta local: {e}")
        finally:
            self.local_discovery_running = False
            sock.close()
    
    def stop_local_discovery(self):
        """Parar o serviço de descoberta na rede local"""
        self.local_discovery_running = False
        if self.local_discovery_thread:
            self.local_discovery_thread.join(timeout=1)
            self.local_discovery_thread = None