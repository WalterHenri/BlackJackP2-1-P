import socket
import json
import threading
import uuid
import time
import random
import string
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

class LobbyServer:
    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.rooms = {}
        self.clients = {}
        self.server_socket = None
        self.running = False
        self.logger = logging.getLogger('LobbyServer')
        
    def generate_room_id(self):
        """Gera um ID de sala aleatório de 4 dígitos"""
        return ''.join(random.choices(string.digits, k=4))
        
    def start(self):
        """Inicia o servidor de lobby"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.running = True
        self.logger.info(f"Servidor de lobby iniciado em {self.host}:{self.port}")
        
        # Inicia uma thread para limpar salas antigas
        cleanup_thread = threading.Thread(target=self._cleanup_old_rooms)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        try:
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Nova conexão de {client_address}")
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
        except Exception as e:
            self.logger.error(f"Erro no servidor: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Para o servidor de lobby"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        self.logger.info("Servidor de lobby parado")
        
    def _handle_client(self, client_socket, client_address):
        """Manipula a conexão do cliente"""
        try:
            # Recebe a mensagem do cliente
            data = client_socket.recv(4096)
            if not data:
                return
                
            # Analisa a mensagem
            request = json.loads(data.decode('utf-8'))
            command = request.get("command")
            
            # Registra o comando recebido
            self.logger.info(f"Comando recebido de {client_address}: {command}")
            
            # Processa o comando
            response = self._process_command(command, request, client_address)
            
            # Envia a resposta
            client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Erro ao manipular cliente {client_address}: {e}")
        finally:
            client_socket.close()
            
    def _process_command(self, command, request, client_address=None):
        """Processa comandos dos clientes"""
        if command == "CREATE_ROOM":
            return self._create_room(request, client_address)
        elif command == "JOIN_ROOM":
            return self._join_room(request)
        elif command == "LIST_ROOMS":
            return self._list_rooms()
        elif command == "LEAVE_ROOM":
            return self._leave_room(request)
        elif command == "UPDATE_ROOM":
            return self._update_room(request)
        elif command == "GET_SERVER_STATUS":
            return self._get_server_status()
        else:
            return {"status": "error", "message": "Comando inválido"}
            
    def _create_room(self, request, client_address=None):
        """Cria uma nova sala"""
        host_name = request.get("host_name")
        room_name = request.get("room_name")
        password = request.get("password")
        
        if not host_name:
            return {"status": "error", "message": "Nome do host é obrigatório"}
            
        # Gera um ID único para a sala
        room_id = self.generate_room_id()
        while room_id in self.rooms:
            room_id = self.generate_room_id()
            
        # Pega o endereço IP do cliente se fornecido, ou usa o que detectamos
        host_ip = request.get('host_address')
        host_port = request.get('host_port', 5678)
        
        # Se não temos o endereço do host e temos o endereço do cliente, use-o
        if not host_ip and client_address:
            host_ip = client_address[0]
            
        # Se ainda não temos o endereço, use localhost (não recomendado para produção)
        if not host_ip:
            host_ip = "localhost"
            
        # Cria o endereço do host
        host_address = f"{host_ip}:{host_port}"
        
        # Cria a sala
        room = {
            "room_id": room_id,
            "host_name": host_name,
            "host_address": host_address,
            "players": [host_name],
            "room_name": room_name or f"Sala de {host_name}",
            "has_password": password is not None,
            "password": password,
            "created_at": time.time(),
            "public_ip": request.get("public_ip", host_ip)
        }
        
        self.rooms[room_id] = room
        self.logger.info(f"Sala criada: {room_id} - {room_name} por {host_name} em {host_address}")
        
        # Retorna uma cópia da sala sem a senha
        room_copy = room.copy()
        if "password" in room_copy:
            del room_copy["password"]
            
        return {
            "status": "success",
            "room_id": room_id,
            "room": room_copy
        }
        
    def _join_room(self, request):
        """Permite que um jogador entre em uma sala"""
        room_id = request.get("room_id")
        player_name = request.get("player_name")
        password = request.get("password")
        
        if not room_id or not player_name:
            return {"status": "error", "message": "ID da sala e nome do jogador são obrigatórios"}
            
        if room_id not in self.rooms:
            return {"status": "error", "message": "Sala não encontrada"}
            
        room = self.rooms[room_id]
        
        # Verifica a senha se necessário
        if room.get("has_password", False) and room.get("password") != password:
            return {"status": "error", "message": "Senha incorreta"}
            
        # Adiciona o jogador à sala
        if player_name not in room["players"]:
            room["players"].append(player_name)
            self.logger.info(f"Jogador {player_name} entrou na sala {room_id}")
            
        # Retorna uma cópia da sala sem a senha
        room_copy = room.copy()
        if "password" in room_copy:
            del room_copy["password"]
            
        return {
            "status": "success",
            "room": room_copy
        }
        
    def _list_rooms(self):
        """Lista todas as salas disponíveis"""
        # Filtra salas antigas (mais de 30 minutos)
        current_time = time.time()
        active_rooms = {}
        
        for room_id, room in self.rooms.items():
            if current_time - room["created_at"] < 1800:  # 30 minutos
                # Cria uma cópia da sala sem a senha
                room_copy = room.copy()
                if "password" in room_copy:
                    del room_copy["password"]
                active_rooms[room_id] = room_copy
                
        return {
            "status": "success",
            "rooms": list(active_rooms.values())
        }
        
    def _leave_room(self, request):
        """Remove um jogador de uma sala"""
        room_id = request.get("room_id")
        player_name = request.get("player_name")
        
        if not room_id or not player_name:
            return {"status": "error", "message": "ID da sala e nome do jogador são obrigatórios"}
            
        if room_id not in self.rooms:
            return {"status": "error", "message": "Sala não encontrada"}
            
        room = self.rooms[room_id]
        
        # Remove o jogador da sala
        if player_name in room["players"]:
            room["players"].remove(player_name)
            self.logger.info(f"Jogador {player_name} saiu da sala {room_id}")
            
        # Se não houver mais jogadores, remove a sala
        if not room["players"]:
            del self.rooms[room_id]
            self.logger.info(f"Sala {room_id} removida (sem jogadores)")
            return {"status": "success", "message": "Sala removida"}
            
        # Se o host saiu, define o próximo jogador como host
        if player_name == room["host_name"] and room["players"]:
            room["host_name"] = room["players"][0]
            self.logger.info(f"Novo host da sala {room_id}: {room['host_name']}")
            
        return {"status": "success", "message": "Jogador removido da sala"}
        
    def _update_room(self, request):
        """Atualiza informações de uma sala"""
        room_id = request.get("room_id")
        players = request.get("players")
        
        if not room_id:
            return {"status": "error", "message": "ID da sala é obrigatório"}
            
        if room_id not in self.rooms:
            return {"status": "error", "message": "Sala não encontrada"}
            
        room = self.rooms[room_id]
        
        # Atualiza a lista de jogadores
        if players is not None:
            room["players"] = players
            self.logger.info(f"Lista de jogadores atualizada na sala {room_id}: {players}")
            
        # Retorna uma cópia da sala sem a senha
        room_copy = room.copy()
        if "password" in room_copy:
            del room_copy["password"]
            
        return {
            "status": "success",
            "room": room_copy
        }
    
    def _get_server_status(self):
        """Retorna o status do servidor e estatísticas"""
        return {
            "status": "success",
            "server_status": "online",
            "total_rooms": len(self.rooms),
            "total_players": sum(len(room["players"]) for room in self.rooms.values())
        }
        
    def _cleanup_old_rooms(self):
        """Remove salas antigas periodicamente"""
        while self.running:
            time.sleep(60)  # Verifica a cada minuto
            
            current_time = time.time()
            room_ids_to_remove = []
            
            # Identifica salas inativas por mais de 30 minutos
            for room_id, room in self.rooms.items():
                if current_time - room["created_at"] > 1800:  # 30 minutos
                    room_ids_to_remove.append(room_id)
            
            # Remove as salas inativas
            for room_id in room_ids_to_remove:
                if room_id in self.rooms:
                    self.logger.info(f"Sala {room_id} removida por inatividade")
                    del self.rooms[room_id]

if __name__ == "__main__":
    # Executar o servidor diretamente se este script for executado
    server = LobbyServer(host="0.0.0.0", port=5000)
    server.start()
