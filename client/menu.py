import pygame
import sys
import os
import json
import uuid
import time
from pygame.locals import *

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .constants import WHITE, GREEN, BLACK, RED, BLUE, YELLOW
from shared.models.player import Player
from shared.models.game import Game
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager
from client.player_data import get_player_balance, update_player_balance

class Menu:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 64)
        
        # Botões do menu principal
        self.play_alone_button = pygame.Rect(self.screen_width // 2 - 100, 220, 200, 50)
        self.play_online_button = pygame.Rect(self.screen_width // 2 - 100, 280, 200, 50)
        self.play_local_button = pygame.Rect(self.screen_width // 2 - 100, 340, 200, 50)
        self.exit_button = pygame.Rect(self.screen_width // 2 - 100, 400, 200, 50)
        
        # Campo de entrada de nome
        self.name_input_rect = pygame.Rect(self.screen_width // 2 - 100, 160, 200, 32)
        
        # Botões da tela de jogo online
        self.create_room_button = pygame.Rect(self.screen_width // 2 - 100, 220, 200, 50)
        self.join_room_button = pygame.Rect(self.screen_width // 2 - 100, 280, 200, 50)
        self.browse_rooms_button = pygame.Rect(self.screen_width // 2 - 100, 340, 200, 50)
        self.back_button = pygame.Rect(self.screen_width // 2 - 100, 400, 200, 50)
        
        # Botões da tela de seleção de bots
        self.easy_bot_button = pygame.Rect(self.screen_width // 2 - 100, 200, 200, 50)
        self.medium_bot_button = pygame.Rect(self.screen_width // 2 - 100, 260, 200, 50)
        self.hard_bot_button = pygame.Rect(self.screen_width // 2 - 100, 320, 200, 50)
        self.start_game_button = pygame.Rect(self.screen_width // 2 - 100, 380, 200, 50)
        self.back_to_menu_button = pygame.Rect(self.screen_width // 2 - 100, 440, 200, 50)
        
        # Botões da tela de lobby
        self.start_game_lobby_button = pygame.Rect(self.screen_width // 2 - 100, 400, 200, 50)
        self.leave_lobby_button = pygame.Rect(self.screen_width // 2 - 100, 460, 200, 50)
        
        # Estado atual do menu
        self.current_view = "menu"  # Valores: menu, bot_selection, online, create_room, join_room, room_browser
        
        # Lista de bots selecionados (inicialmente vazia)
        self.selected_bots = []
        self.max_bots = 3
        
    def draw_menu(self, screen, player_name="Player", name_input_active=False):
        """Renderiza a tela de menu principal"""
        screen.fill(GREEN)
        
        # Título
        title_text = self.title_font.render("Blackjack", True, BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Campo de nome
        pygame.draw.rect(screen, WHITE, self.name_input_rect, 0)
        pygame.draw.rect(screen, BLACK, self.name_input_rect, 2)
        
        name_text = self.font.render(player_name, True, BLACK)
        text_rect = name_text.get_rect(center=self.name_input_rect.center)
        screen.blit(name_text, text_rect)
        
        if name_input_active:
            # Mostrar cursor piscando
            cursor_pos = text_rect.right
            if pygame.time.get_ticks() % 1000 < 500:
                pygame.draw.line(screen, BLACK, (cursor_pos, self.name_input_rect.top + 5), 
                                (cursor_pos, self.name_input_rect.bottom - 5), 2)
        
        # Botão Jogar sozinho
        self._draw_button(screen, self.play_alone_button, "Jogar sozinho")
        
        # Botão Jogar online
        self._draw_button(screen, self.play_online_button, "Jogar online")
        
        # Botão Jogar rede local
        self._draw_button(screen, self.play_local_button, "Jogar na rede local")
        
        # Botão Sair
        self._draw_button(screen, self.exit_button, "Sair", RED)
        
    def draw_online_menu(self, screen, connection_mode="online"):
        """Renderiza a tela de menu para jogo online/local"""
        screen.fill(GREEN)
        
        # Título
        mode_text = "Online" if connection_mode == "online" else "Rede Local"
        title_text = self.title_font.render(f"Blackjack {mode_text}", True, BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Botão Criar sala
        self._draw_button(screen, self.create_room_button, "Criar sala")
        
        # Botão Entrar em sala
        self._draw_button(screen, self.join_room_button, "Entrar em sala")
        
        # Botão Navegar salas
        self._draw_button(screen, self.browse_rooms_button, "Navegar salas")
        
        # Botão Voltar
        self._draw_button(screen, self.back_button, "Voltar", YELLOW)
        
    def draw_bot_selection(self, screen, selected_bots):
        """Renderiza a tela de seleção de bots"""
        screen.fill(GREEN)
        
        # Título
        title_text = self.title_font.render("Selecione os Bots", True, BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Informações
        info_text = self.font.render(f"Bots selecionados: {len(selected_bots)}/{self.max_bots}", True, BLACK)
        info_rect = info_text.get_rect(center=(self.screen_width // 2, 140))
        screen.blit(info_text, info_rect)
        
        # Botão Bot Fácil
        bot_color = BLUE if "easy" in selected_bots else WHITE
        self._draw_button(screen, self.easy_bot_button, "Bot Fácil", bot_color)
        
        # Botão Bot Médio
        bot_color = BLUE if "medium" in selected_bots else WHITE
        self._draw_button(screen, self.medium_bot_button, "Bot Médio", bot_color)
        
        # Botão Bot Difícil
        bot_color = BLUE if "hard" in selected_bots else WHITE
        self._draw_button(screen, self.hard_bot_button, "Bot Difícil", bot_color)
        
        # Botão Iniciar Jogo
        start_color = GREEN if len(selected_bots) > 0 else WHITE
        self._draw_button(screen, self.start_game_button, "Iniciar Jogo", start_color)
        
        # Botão Voltar
        self._draw_button(screen, self.back_to_menu_button, "Voltar", YELLOW)
        
    def draw_lobby(self, screen, room_id="", room_name="", player_list=None, is_host=False):
        """Renderiza a tela de lobby"""
        if player_list is None:
            player_list = []
            
        screen.fill(GREEN)
        
        # Título
        title_text = self.title_font.render("Sala de Espera", True, BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Informações da sala
        room_text = self.font.render(f"Sala: {room_name} (ID: {room_id})", True, BLACK)
        room_rect = room_text.get_rect(center=(self.screen_width // 2, 140))
        screen.blit(room_text, room_rect)
        
        # Lista de jogadores
        y_pos = 200
        for i, player in enumerate(player_list):
            player_text = self.font.render(f"{i+1}. {player}", True, BLACK)
            screen.blit(player_text, (self.screen_width // 2 - 100, y_pos))
            y_pos += 40
        
        # Botão Iniciar Jogo (apenas para o host)
        if is_host:
            start_color = GREEN if len(player_list) > 1 else WHITE
            self._draw_button(screen, self.start_game_lobby_button, "Iniciar Jogo", start_color)
        
        # Botão Sair da Sala
        self._draw_button(screen, self.leave_lobby_button, "Sair da Sala", YELLOW)
        
    def _draw_button(self, screen, button_rect, text, color=WHITE, text_color=BLACK):
        """Desenha um botão com texto"""
        mouse_pos = pygame.mouse.get_pos()
        
        # Verifica se o mouse está sobre o botão
        if button_rect.collidepoint(mouse_pos):
            # Desenha o botão com uma cor mais escura quando o mouse está sobre ele
            pygame.draw.rect(screen, (max(color[0] - 30, 0), 
                                      max(color[1] - 30, 0), 
                                      max(color[2] - 30, 0)), button_rect)
        else:
            pygame.draw.rect(screen, color, button_rect)
        
        # Adiciona borda ao botão
        pygame.draw.rect(screen, BLACK, button_rect, 2)
        
        # Adiciona texto ao botão
        text_surf = self.font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect) 

class LobbyManager:
    def __init__(self, client):
        self.client = client
        self.game = None
        self.room_id = ""
        self.player_list = []
        self.host_mode = False
        self.p2p_manager = None
        
    def create_room(self, room_name, password="", mode="online"):
        """Criar uma sala de jogo"""
        # Criar o jogador
        self.client.player = Player(self.client.player_name, self.client.player_balance, str(uuid.uuid4()))
        
        # Criar o jogo
        self.game = Game()
        self.game.initialize_game(self.client.player)
        
        # Gerar ID da sala
        self.room_id = str(uuid.uuid4())[:8]
        
        # Inicializar P2P manager como host
        self.p2p_manager = P2PManager(host=True, local_network=mode=="local")
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
        
        # Registrar a sala no serviço de matchmaking
        if mode == "online":
            success, server_room_id = self.client.matchmaking_service.create_room(
                self.client.player_name,
                room_name,
                password,
                self.p2p_manager.get_host_address()
            )
            
            if success:
                self.room_id = server_room_id
            else:
                return False, "Erro ao registrar sala no servidor"
        else:
            # Sala local não precisa de registro no servidor central
            success = self.client.matchmaking_service.broadcast_local_game(
                self.room_id,
                self.client.player_name,
                room_name,
                password is not None and len(password) > 0,
                self.p2p_manager.get_host_address()
            )
            
            if not success:
                return False, "Erro ao anunciar sala na rede local"
        
        # Adicionar o host à lista de jogadores
        self.player_list = [self.client.player_name]
        self.host_mode = True
        
        # Atualizar a tela para o lobby
        self.client.current_view = "lobby"
        return True, "Sala criada com sucesso"
        
    def join_room(self, room_id, host_address, password=""):
        """Entrar em uma sala existente"""
        # Criar o jogador
        self.client.player = Player(self.client.player_name, self.client.player_balance, str(uuid.uuid4()))
        
        # Configurar conexão P2P como cliente
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
        
        # Conectar ao host
        connect_success, connection_message = self.p2p_manager.connect_to_host(host_address)
        if not connect_success:
            return False, f"Erro ao conectar ao host: {connection_message}"
        
        # Enviar solicitação para entrar na sala
        join_message = Message.create_join_request(
            self.client.player.player_id,
            self.client.player.name,
            password=password
        )
        self.p2p_manager.send_message(join_message)
        
        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        self.host_mode = False
        return True, "Conectando à sala..."
        
    def leave_lobby(self):
        """Sair da sala atual"""
        # Enviar mensagem de saída se estiver conectado
        if self.p2p_manager:
            if not self.host_mode:
                # Cliente enviando mensagem de saída para o host
                leave_message = Message.create_leave_game(self.client.player.player_id)
                self.p2p_manager.send_message(leave_message)
            else:
                # Host enviando mensagem para todos que a sala foi fechada
                close_message = Message.create_game_closed("O host fechou a sala")
                self.p2p_manager.send_message(close_message)
                
                # Remover a sala do serviço de matchmaking
                if self.room_id:
                    self.client.matchmaking_service.close_room(self.room_id)
            
            # Fechar conexões
            self.p2p_manager.close()
            self.p2p_manager = None
        
        # Limpar dados da sala
        self.game = None
        self.room_id = ""
        self.player_list = []
        self.host_mode = False
        
        # Voltar para o menu principal
        self.client.current_view = "menu"
        
    def start_game(self):
        """Iniciar o jogo (apenas para o host)"""
        if not self.host_mode or not self.game:
            return False
            
        # Verificar se há pelo menos dois jogadores
        if len(self.player_list) < 2:
            return False
            
        # Iniciar o jogo
        self.game.start_game()
        
        # Enviar mensagem para iniciar o jogo
        start_message = Message.create_game_start(self.game.game_id)
        self.p2p_manager.send_message(start_message)
        
        # Enviar estado inicial do jogo
        state_message = Message.create_game_state_update(self.game.get_game_state())
        self.p2p_manager.send_message(state_message)
        
        # Atualizar a tela para o jogo
        self.client.current_view = "game"
        return True
        
    def on_message_received(self, sender_id, message):
        """Processar mensagens recebidas"""
        if message.msg_type == MessageType.JOIN_REQUEST:
            self.handle_join_request(sender_id, message)
        elif message.msg_type == MessageType.JOIN_RESPONSE:
            self.handle_join_response(message)
        elif message.msg_type == MessageType.PLAYER_LEFT:
            self.handle_player_left(message)
        elif message.msg_type == MessageType.GAME_CLOSED:
            self.handle_game_closed(message)
        elif message.msg_type == MessageType.GAME_START:
            self.handle_game_start(message)
        elif message.msg_type == MessageType.GAME_STATE:
            self.handle_game_state(message)
        elif message.msg_type == MessageType.GAME_ACTION:
            self.handle_game_action(sender_id, message)
            
    def handle_join_request(self, sender_id, message):
        """Processar solicitação de entrada em sala (apenas host)"""
        if not self.host_mode:
            return
            
        player_id = message.content.get("player_id")
        player_name = message.content.get("player_name")
        password = message.content.get("password", "")
        
        # Verificar senha se necessário
        room_password = self.client.password_input if hasattr(self.client, "password_input") else ""
        if room_password and room_password != password:
            # Senha incorreta
            response = Message.create_join_response(False, "Senha incorreta")
            self.p2p_manager.send_message(response, sender_id)
            return
            
        # Adicionar jogador ao jogo
        new_player = Player(player_name, 1000, player_id)
        success, result = self.game.add_player(new_player)
        
        if success:
            # Adicionar à lista de jogadores
            self.player_list.append(player_name)
            
            # Enviar resposta positiva
            players_data = [{"name": p} for p in self.player_list]
            response = Message.create_join_response(True, "Bem-vindo ao jogo!", {
                "game_id": self.game.game_id,
                "host_name": self.client.player_name,
                "players": players_data,
                "room_name": self.client.room_name_input
            })
            self.p2p_manager.send_message(response, sender_id)
            
            # Notificar outros jogadores
            player_joined = Message.create_player_joined(player_name)
            for pid in self.p2p_manager.connections.keys():
                if pid != sender_id:
                    self.p2p_manager.send_message(player_joined, pid)
        else:
            # Enviar resposta negativa
            response = Message.create_join_response(False, result)
            self.p2p_manager.send_message(response, sender_id)
            
    def handle_join_response(self, message):
        """Processar resposta à solicitação de entrada"""
        success = message.content.get("success", False)
        
        if success:
            # Atualizar dados da sala
            game_data = message.content.get("game_data", {})
            self.game = Game(game_data.get("game_id"))
            
            # Atualizar lista de jogadores
            players = game_data.get("players", [])
            self.player_list = [p.get("name") for p in players]
            
            # Atualizar tela para o lobby
            self.client.current_view = "lobby"
        else:
            # Mostrar mensagem de erro
            error_message = message.content.get("message", "Erro ao entrar na sala")
            self.client.error_message = error_message
            self.client.message_timer = pygame.time.get_ticks()
            
            # Fechar conexão
            if self.p2p_manager:
                self.p2p_manager.close()
                self.p2p_manager = None
                
            # Voltar para o menu
            self.client.current_view = "menu"
            
    def handle_player_left(self, message):
        """Processar saída de jogador"""
        player_id = message.content.get("player_id")
        
        # Remover jogador do jogo se for o host
        if self.host_mode and self.game:
            for i, player in enumerate(self.game.state_manager.players):
                if player.player_id == player_id:
                    # Remover da lista de jogadores
                    player_name = player.name
                    if player_name in self.player_list:
                        self.player_list.remove(player_name)
                    
                    # Se o jogo já começou, tratar a saída do jogador
                    if self.game.state_manager.state != "WAITING_FOR_PLAYERS":
                        # Implementar lógica para tratar saída durante o jogo
                        pass
                    break
                    
    def handle_game_closed(self, message):
        """Processar fechamento da sala"""
        if not self.host_mode:
            # Mostrar mensagem
            reason = message.content.get("reason", "O host fechou a sala")
            self.client.error_message = reason
            self.client.message_timer = pygame.time.get_ticks()
            
            # Fechar conexão
            if self.p2p_manager:
                self.p2p_manager.close()
                self.p2p_manager = None
                
            # Voltar para o menu
            self.client.current_view = "menu"
            
    def handle_game_start(self, message):
        """Processar início do jogo"""
        game_id = message.content.get("game_id")
        
        # Se não é o host, atualizar o ID do jogo
        if not self.host_mode:
            self.game = Game(game_id)
            
        # Atualizar a tela para o jogo
        self.client.current_view = "game"
        
    def handle_game_state(self, message):
        """Processar atualização do estado do jogo"""
        game_state = message.content.get("game_state", {})
        
        # Atualizar o estado do jogo
        self.client.game_state = game_state
        
        # Se estamos no jogo, processar atualizações específicas
        if self.client.current_view == "game":
            # Implementar lógica para processar estado do jogo
            pass
            
    def handle_game_action(self, sender_id, message):
        """Processar ação de jogo (apenas host)"""
        if not self.host_mode or not self.game:
            return
            
        action = message.content.get("action")
        player_id = message.content.get("player_id")
        
        # Processar a ação no jogo
        if action == ActionType.HIT:
            success, result = self.game.hit(player_id)
        elif action == ActionType.STAND:
            success, result = self.game.stand(player_id)
        elif action == ActionType.PLACE_BET:
            amount = message.content.get("amount", 0)
            success, result = self.game.place_bet(player_id, amount)
        else:
            return
            
        # Enviar atualização do estado do jogo para todos
        state_message = Message.create_game_state_update(self.game.get_game_state())
        self.p2p_manager.send_message(state_message)
        
    def on_player_connected(self, player_id, data):
        """Callback para quando um jogador se conecta"""
        print(f"Jogador conectado: {player_id}")
        
    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")
        
        # Se é o host, remover o jogador do jogo
        if self.host_mode and self.game:
            for player in self.game.state_manager.players:
                if player.player_id == player_id:
                    player_name = player.name
                    if player_name in self.player_list:
                        self.player_list.remove(player_name)
                    break 