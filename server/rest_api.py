import json
import threading
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from lobby_server import LobbyServer

class BlackjackRESTHandler(BaseHTTPRequestHandler):
    """Handler para a API REST do servidor de Blackjack"""
    
    # Armazenar referência ao servidor de lobby
    lobby_server = None
    
    def _set_headers(self, status_code=200, content_type='application/json'):
        """Configura os cabeçalhos da resposta HTTP"""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')  # CORS
        self.end_headers()
    
    def _json_response(self, data, status_code=200):
        """Envia uma resposta em formato JSON"""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Gerencia solicitações OPTIONS para suporte a CORS"""
        self._set_headers()
    
    def do_GET(self):
        """Gerencia solicitações GET"""
        if self.path == '/status':
            # Retorna o status do servidor
            if self.lobby_server:
                data = {
                    "status": "online",
                    "total_rooms": len(self.lobby_server.rooms),
                    "total_players": sum(len(room["players"]) for room in self.lobby_server.rooms.values()),
                    "uptime": time.time() - self.server_start_time
                }
                self._json_response(data)
            else:
                self._json_response({"status": "error", "message": "Servidor de lobby não está disponível"}, 500)
        
        elif self.path == '/rooms':
            # Lista todas as salas disponíveis
            if self.lobby_server:
                # Remove informações sensíveis como senhas
                safe_rooms = []
                for room_id, room in self.lobby_server.rooms.items():
                    room_copy = room.copy()
                    if "password" in room_copy:
                        del room_copy["password"]
                    safe_rooms.append(room_copy)
                    
                self._json_response({"status": "success", "rooms": safe_rooms})
            else:
                self._json_response({"status": "error", "message": "Servidor de lobby não está disponível"}, 500)
        
        elif self.path.startswith('/room/'):
            # Obter detalhes de uma sala específica
            room_id = self.path.split('/')[2]
            if self.lobby_server and room_id in self.lobby_server.rooms:
                room_copy = self.lobby_server.rooms[room_id].copy()
                if "password" in room_copy:
                    del room_copy["password"]
                self._json_response({"status": "success", "room": room_copy})
            else:
                self._json_response({"status": "error", "message": "Sala não encontrada"}, 404)
        
        else:
            # Rota não encontrada
            self._json_response({"status": "error", "message": "Rota não encontrada"}, 404)
    
    def do_POST(self):
        """Gerencia solicitações POST"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._json_response({"status": "error", "message": "JSON inválido"}, 400)
            return
        
        if self.path == '/admin/close_room':
            # Rota para fechar uma sala (admin)
            room_id = data.get('room_id')
            admin_key = data.get('admin_key')
            
            # Verificação básica de autenticação
            if admin_key != 'chave_admin_secreta':  # Em produção, use um sistema de autenticação mais seguro
                self._json_response({"status": "error", "message": "Não autorizado"}, 401)
                return
                
            if self.lobby_server and room_id in self.lobby_server.rooms:
                del self.lobby_server.rooms[room_id]
                self._json_response({"status": "success", "message": f"Sala {room_id} fechada"})
            else:
                self._json_response({"status": "error", "message": "Sala não encontrada"}, 404)
        
        else:
            # Rota não encontrada
            self._json_response({"status": "error", "message": "Rota não encontrada"}, 404)


def run_rest_server(host="0.0.0.0", port=8080, lobby_server=None):
    """Iniciar o servidor REST"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, BlackjackRESTHandler)
    
    # Configurar o handler para acessar o lobby_server
    BlackjackRESTHandler.lobby_server = lobby_server
    BlackjackRESTHandler.server_start_time = time.time()
    
    print(f"Iniciando servidor REST em {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iniciar servidor REST para BlackJack P2P")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                        help="Endereço IP do servidor (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, 
                        help="Porta para o servidor REST (padrão: 8080)")
    parser.add_argument("--lobby-port", type=int, default=5000, 
                        help="Porta para o servidor de lobby (padrão: 5000)")
    
    args = parser.parse_args()
    
    # Iniciar lobby server
    lobby_server = LobbyServer(host=args.host, port=args.lobby_port)
    lobby_thread = threading.Thread(target=lobby_server.start)
    lobby_thread.daemon = True
    lobby_thread.start()
    
    try:
        # Iniciar REST API
        run_rest_server(host=args.host, port=args.port, lobby_server=lobby_server)
    except KeyboardInterrupt:
        print("Servidor interrompido")
    finally:
        if lobby_server:
            lobby_server.stop() 