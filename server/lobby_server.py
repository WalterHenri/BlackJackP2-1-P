import socket
import json
import threading
import uuid
import time
import random
import string

class LobbyServer:
    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.rooms = {}
        self.clients = {}
        self.server_socket = None
        self.running = False
        
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
        print(f"Servidor de lobby iniciado em {self.host}:{self.port}")
        
        # Inicia uma thread para limpar salas antigas
        cleanup_thread = threading.Thread(target=self._cleanup_old_rooms)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        try:
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
        except Exception as e:
            print(f"Erro no servidor: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Para o servidor de lobby"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        print("Servidor de lobby parado")
        
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
            
            # Processa o comando
            response = self._process_command(command, request)
            
            # Envia a resposta
            client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Erro ao manipular cliente {client_address}: {e}")
        finally:
            client_socket.close()
            
    def _process_command(self, command, request):
        """Processa comandos dos clientes"""
        if command == "CREATE_ROOM":
            return self._create_room(request)
        elif command == "JOIN_ROOM":
            return self._join_room(request)
        elif command == "LIST_ROOMS":
            return self._list_rooms()
        elif command == "LEAVE_ROOM":
            return self._leave_room(request)
        elif command == "UPDATE_ROOM":
            return self._update_room(request)
        else:
            return {"status": "error", "message": "Comando inválido"}
            
    def _create_room(self, request):
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
            
        # Usa o endereço do cliente como endereço de host para a sala
        host_address = f"{request.get('host_address', 'localhost')}:{request.get('host_port', 5678)}"
        
        # Cria a sala
        room = {
            "room_id": room_id,
            "host_name": host_name,
            "host_address": host_address,
            "players": [host_name],
            "room_name": room_name or f"Sala de {host_name}",
            "has_password": password is not None,
            "password": password,
            "created_at": time.time()
        }
        
        self.rooms[room_id] = room
        
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
            
        # Se não houver mais jogadores, remove a sala
        if not room["players"]:
            del self.rooms[room_id]
            return {"status": "success", "message": "Sala removida"}
            
        # Se o host saiu, define o próximo jogador como host
        if player_name == room["host_name"] and room["players"]:
            room["host_name"] = room["players"][0]
            
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
            
        # Retorna uma cópia da sala sem a senha
        room_copy = room.copy()
        if "password" in room_copy:
            del room_copy["password"]
            
        return {
            "status": "success",
            "room": room_copy
        }
        
    def _cleanup_old_rooms(self):
        """Remove salas antigas periodicamente"""
        while self.running:
            time.sleep(60)  # Verifica a cada minuto
            
            current_time = time.time()
            room_ids_to_remove = []
            
            for room_id, room in self.rooms.items():
                if current_time - room["created_at"] > 1800:  # 30 minutos
                    room_ids_to_remove.append(room_id)
                    
            for room_id in room_ids_to_remove:
                del self.rooms[room_id]
                
            if room_ids_to_remove:
                print(f"Removidas {len(room_ids_to_remove)} salas antigas")
                
if __name__ == "__main__":
    # Inicia o servidor de lobby
    server = LobbyServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
