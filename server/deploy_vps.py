import os
import sys
import argparse
import signal
import time
from lobby_server import LobbyServer
from matchmaking import MatchmakingService

# Adicionar o diretório raiz ao path para acessar módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def signal_handler(sig, frame):
    """Manipulador de sinal para encerramento gracioso"""
    print("\nEncerrando servidores...")
    if lobby_server:
        lobby_server.stop()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iniciar servidores para BlackJack P2P")
    parser.add_argument("--host", type=str, default="0.0.0.0", 
                        help="Endereço IP do servidor (padrão: 0.0.0.0)")
    parser.add_argument("--lobby-port", type=int, default=5000, 
                        help="Porta para o servidor de lobby (padrão: 5000)")
    parser.add_argument("--discovery-port", type=int, default=5001, 
                        help="Porta para o serviço de descoberta (padrão: 5001)")
    
    args = parser.parse_args()
    
    # Registrar manipulador de sinal para CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Iniciar servidor de lobby
    lobby_server = LobbyServer(host=args.host, port=args.lobby_port)
    
    print(f"Iniciando servidor de lobby em {args.host}:{args.lobby_port}")
    try:
        # Iniciar o servidor em uma thread
        import threading
        server_thread = threading.Thread(target=lobby_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # Manter o programa rodando
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Erro ao iniciar o servidor: {e}")
        if lobby_server:
            lobby_server.stop() 