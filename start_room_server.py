#!/usr/bin/env python3
from room_server import RoomServer

if __name__ == "__main__":
    print("Iniciando servidor de salas para o jogo de Blackjack P2P...")
    print("Pressione Ctrl+C para encerrar")
    
    server = RoomServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuário")
    finally:
        server.stop() 