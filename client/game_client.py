import pygame
import sys
import os
import json
import uuid
import time
from pygame.locals import *

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.player import Player
from shared.models.game import Game
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager
from server.matchmaking import MatchmakingService
from client.card_sprites import CardSprites
from client.player_data import get_player_balance, update_player_balance, check_player_eliminated

# Inicializar pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)

# Configurações da tela
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CARD_WIDTH = 100
CARD_HEIGHT = 150
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50


class BlackjackClient:
    def __init__(self):
        """Inicializar o cliente do jogo"""
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Blackjack P2P")
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_view = "menu"
        self.messages = []
        self.player_name = "Player"
        self.name_input_active = True  # Iniciar com o campo de nome ativo
        self.player_balance = get_player_balance(self.player_name)
        print(f"Saldo carregado inicialmente: {self.player_balance}")
        self.player = None
        self.dealer = None
        self.players = []
        self.my_server = None
        self.client_socket = None
        self.server_address = ""
        self.current_bet = 0
        self.bet_amount = 100  # Valor inicial da aposta
        self.selected_bot_count = 1
        self.selected_bot_strategy = "random"
        self.cursor_visible = True
        self.cursor_timer = 0
        self.p2p_manager = None
        self.matchmaking_service = MatchmakingService()
        self.game = None
        self.game_state = None
        self.host_mode = False

        # Variáveis para o sistema de salas
        self.connection_mode = "online"  # "online" ou "local"
        self.room_list = []
        self.room_id = ""
        self.room_id_input = ""
        self.room_id_input_active = False
        self.room_name_input = ""
        self.room_name_input_active = False
        self.password_input = ""
        self.password_input_active = False
        self.connection_mode_selection = "online"  # Modo selecionado na tela de criação/busca de sala
        self.room_browser_scroll = 0
        self.selected_room_index = -1
        self.error_message = ""
        self.success_message = ""
        self.message_timer = 0

        # Fontes
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        # Carregar sprites das cartas
        self.card_sprites = CardSprites()

        # Adicionar variável para controlar a exibição do pop-up de tutorial
        self.show_tutorial = False

    def start(self):
        """Iniciar o loop principal do jogo"""
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        # Salvar o saldo do jogador antes de sair
        if self.player and hasattr(self.player, 'balance'):
            update_player_balance(self.player_name, self.player.balance)
            print(f"Salvando saldo final: {self.player_name} = {self.player.balance}")
        
        # Fechar conexões se existirem
        if hasattr(self, 'p2p_manager') and self.p2p_manager:
            self.p2p_manager.close()
            
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        """Lidar com eventos de entrada do usuário"""
        if self.current_view == "menu":
            self.handle_menu_event(event)
        elif self.current_view == "lobby":
            self.handle_lobby_event(event)
        elif self.current_view == "game":
            self.handle_game_event(event)
        elif self.current_view == "bot_selection":
            self.handle_bot_selection_event(event)
        elif self.current_view == "create_room":
            self.handle_create_room_event(event)
        elif self.current_view == "join_room":
            self.handle_join_room_event(event)
        elif self.current_view == "room_browser":
            self.handle_room_browser_event(event)

    def handle_menu_event(self, event):
        """Lidar com eventos na tela do menu"""
        # Verificar clique no botão Jogar Sozinho
        play_alone_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_alone_rect.collidepoint(event.pos):
            # Verificar se o campo de nome está ativo antes de prosseguir
            if not self.name_input_active:
                self.handle_solo_click()
                return
        
        # Verificar clique no botão Jogar Online
        play_online_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 50 + 20, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_online_rect.collidepoint(event.pos):
            # Verificar se o campo de nome está ativo antes de prosseguir
            if not self.name_input_active:
                self.handle_online_click()
                return
                
        # Verificar clique no botão Jogar na Rede Local
        play_local_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 2 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_local_rect.collidepoint(event.pos):
            # Verificar se o campo de nome está ativo antes de prosseguir
            if not self.name_input_active:
                self.handle_local_network_click()
                return
                
        # Verificar clique no botão Sair
        exit_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280 + 3 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and exit_rect.collidepoint(event.pos):
            # Salvar o saldo do jogador antes de sair
            update_player_balance(self.player_name, self.player_balance)
            pygame.quit()
            sys.exit()
            
        # Manipular eventos do campo de nome
        name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
        
        # Verifica clique no campo de nome
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Verificar se o clique foi dentro do campo de nome
            if name_input_rect.collidepoint(event.pos):
                # Ativar o campo de nome
                self.name_input_active = True
                if self.player_name == "Player" or self.player_name == "":
                    self.player_name = ""  # Limpar o nome padrão
            else:
                # Se o clique foi fora do campo e o campo estava ativo, desativar e atualizar o saldo
                if self.name_input_active:
                    self.name_input_active = False
                    # Se o nome ficou vazio, voltar para "Player"
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após mudar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(f"Nome atualizado para: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
            
        # Manipular teclas para o campo de nome
        if event.type == pygame.KEYDOWN:
            if self.name_input_active:
                if event.key == pygame.K_RETURN:
                    # Confirmar o nome com a tecla Enter
                    self.name_input_active = False
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após confirmar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(f"Nome confirmado: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
                elif event.key == pygame.K_BACKSPACE:
                    # Apagar o último caractere
                    self.player_name = self.player_name[:-1]
                else:
                    # Limitar o nome a 20 caracteres
                    if len(self.player_name) < 20:
                        self.player_name = self.player_name + event.unicode

        # Verificar clique no botão de ajuda
        help_button = pygame.Rect(SCREEN_WIDTH - 50, 20, 40, 40)
        if event.type == pygame.MOUSEBUTTONDOWN and help_button.collidepoint(event.pos):
            self.show_tutorial = not self.show_tutorial
            return
            
        # Se o tutorial estiver aberto e o usuário clicar fora dele, fechar o tutorial
        if self.show_tutorial and event.type == pygame.MOUSEBUTTONDOWN:
            tutorial_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 150, 400, 300)
            if not tutorial_rect.collidepoint(event.pos):
                self.show_tutorial = False
                return

    def handle_solo_click(self):
        """Manipular clique no botão Jogar Sozinho"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "bot_selection"

    def handle_online_click(self):
        """Manipular clique no botão Jogar Online"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.connection_mode = "online"
        self.current_view = "room_browser"
        self.load_room_list(mode="online")

    def handle_local_network_click(self):
        """Manipular clique no botão Jogar em Rede Local"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.connection_mode = "local"
        self.current_view = "room_browser"
        self.load_room_list(mode="local")

    def handle_create_room_click(self):
        """Manipular clique no botão Criar Sala"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "create_room"
        self.password_input = ""
        self.password_input_active = True
        self.room_name_input = f"Sala de {self.player_name}"
        self.room_name_input_active = False
        self.room_id = self.generate_room_id()
        self.connection_mode_selection = "online"  # Padrão: online

    def handle_find_rooms_click(self):
        """Manipular clique no botão Buscar Salas"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "join_room"
        self.room_id_input = ""
        self.room_id_input_active = True
        self.password_input = ""
        self.password_input_active = False
        self.connection_mode_selection = "online"  # Padrão: online

    def generate_room_id(self):
        """Gerar um ID de sala aleatório de 4 dígitos"""
        import random
        return str(random.randint(1000, 9999))

    def handle_bot_selection_event(self, event):
        """Lidar com eventos na tela de seleção de bots"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões para selecionar o número de bots
            button_width = 300
            button_height = 60
            button_x = SCREEN_WIDTH // 2 - button_width // 2
            
            # Botão para 1 bot
            bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
            if bot1_button.collidepoint(mouse_pos):
                self.start_single_player(1)
                return
                
            # Botão para 2 bots
            bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
            if bot2_button.collidepoint(mouse_pos):
                self.start_single_player(2)
                return
                
            # Botão para 3 bots
            bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
            if bot3_button.collidepoint(mouse_pos):
                self.start_single_player(3)
                return
                
            # Botão para voltar
            back_button = pygame.Rect(button_x, 460, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return

    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de iniciar jogo (só para o host)
            if self.host_mode and 100 <= mouse_pos[0] <= 300 and 600 <= mouse_pos[1] <= 650:
                self.start_game()

            # Botão de voltar
            elif 100 <= mouse_pos[0] <= 300 and 700 <= mouse_pos[1] <= 750:
                self.leave_lobby()

    def handle_game_event(self, event):
        """Lidar com eventos durante o jogo"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verificar se é nossa vez
            is_our_turn = (
                    self.game_state and
                    self.game_state["state"] == "PLAYER_TURN" and
                    self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
            )

            # Botão de voltar ao menu (apenas no modo single player)
            menu_button = pygame.Rect(10, 10, 120, 40)
            if len(self.game_state["players"]) <= 4 and menu_button.collidepoint(mouse_pos):  # Single player mode
                self.current_view = "menu"
                self.game = None
                self.game_state = None
                self.host_mode = False
                return

            # Altura reservada para controles/chat na parte inferior
            FOOTER_HEIGHT = 150
            footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
            
            # Área de controles
            controls_x = 20
            controls_width = SCREEN_WIDTH // 2 - 40
            button_y = footer_start_y + 45

            # Botões de ajuste de aposta (apenas na fase de apostas)
            if self.game_state["state"] == "BETTING":
                # Posição do valor da aposta
                bet_amount_x = controls_x + 120
                bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, WHITE)
                
                # Botão de diminuir aposta
                btn_width = 36
                btn_height = 36
                btn_y = footer_start_y + 12
                
                decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
                if decrease_bet_button.collidepoint(mouse_pos):
                    self.decrease_bet()
                    return

                # Botão de aumentar aposta
                increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
                if increase_bet_button.collidepoint(mouse_pos):
                    self.increase_bet()
                    return

                # Botão principal de aposta
                bet_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                if bet_button.collidepoint(mouse_pos):
                    self.place_bet()
                    return

            elif self.game_state["state"] == "PLAYER_TURN" and is_our_turn:
                # Botões de ação durante o turno
                button_width = (controls_width - 10) // 2
                
                # Botão de Hit
                hit_button = pygame.Rect(controls_x, button_y, button_width, 50)
                if hit_button.collidepoint(mouse_pos):
                    self.hit()
                    return

                # Botão de Stand
                stand_button = pygame.Rect(controls_x + button_width + 10, button_y, button_width, 50)
                if stand_button.collidepoint(mouse_pos):
                    self.stand()
                    return

            elif self.game_state["state"] == "GAME_OVER":
                # Botão de Nova Rodada
                new_round_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                if new_round_button.collidepoint(mouse_pos):
                    self.new_round()
                    return

    def update(self):
        """Atualizar o estado do jogo"""
        # Só atualiza o p2p_manager se ele existir (modo multiplayer)
        if hasattr(self, 'p2p_manager') and self.p2p_manager:
            self.p2p_manager.update()  # Process any pending network messages

        # Atualizar estado do jogo se for o host
        if self.host_mode and self.game:
            # Verificar se todos os jogadores fizeram suas apostas
            if (self.game_state and 
                self.game_state["state"] == "BETTING" and 
                all(player["current_bet"] > 0 for player in self.game_state["players"])):
                self.game._deal_initial_cards()
                self.broadcast_game_state()

            # Bot play logic
            if self.game_state and self.game_state["state"] == "PLAYER_TURN":
                current_player = self.game_state["players"][self.game_state["current_player_index"]]
                if current_player["name"].startswith("Bot"):
                    self.bot_play()
                    
                # Verificar se o jogo acabou implicitamente (todos pararam ou estouraram)
                active_players = [p for p in self.game_state["players"] 
                                if not p["is_busted"] and (p["id"] != self.game_state["players"][self.game_state["current_player_index"]]["id"])]
                if not active_players:
                    # Se não há mais jogadores ativos além do atual, o jogo termina
                    self.check_winner()

        # Atualizar mensagens do jogo
        if self.game_state and "messages" in self.game_state:
            self.messages = self.game_state["messages"]

    def render(self):
        """Renderizar a interface do jogo"""
        self.screen.fill(GREEN)

        if self.current_view == "menu":
            self.render_menu()
        elif self.current_view == "lobby":
            self.render_lobby()
        elif self.current_view == "game":
            self.render_game()
        elif self.current_view == "bot_selection":
            self.render_bot_selection()
        elif self.current_view == "create_room":
            self.render_create_room()
        elif self.current_view == "join_room":
            self.render_join_room()
        elif self.current_view == "room_browser":
            self.render_room_browser()

        # Renderizar mensagens de erro ou sucesso
        if self.error_message and pygame.time.get_ticks() - self.message_timer < 3000:
            self.render_message(self.error_message, RED)
        elif self.success_message and pygame.time.get_ticks() - self.message_timer < 3000:
            self.render_message(self.success_message, (0, 200, 0))

        pygame.display.flip()

    def render_menu(self):
        """Renderizar a tela do menu"""
        # Desenhar o fundo com gradiente
        self.screen.fill((0, 100, 0))  # Verde escuro para o fundo
        
        # Desenhar área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 80, 0), title_bg)
        
        # Desenhar título do jogo
        title = self.title_font.render("Blackjack 21 P2P", True, (240, 240, 240))
        title_shadow = self.title_font.render("Blackjack 21 P2P", True, (0, 40, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        shadow_rect = title_shadow.get_rect(center=(SCREEN_WIDTH // 2 + 2, 62))
        self.screen.blit(title_shadow, shadow_rect)
        self.screen.blit(title, title_rect)
        
        # Não carregar o saldo toda vez - usar o valor já armazenado em self.player_balance
        
        # Campo de nome
        name_label = self.medium_font.render("Nome:", True, WHITE)
        self.screen.blit(name_label, (SCREEN_WIDTH // 2 - 150, 150))
        
        # Desenhar campo de nome com borda que muda de cor baseado no foco
        name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
        mouse_pos = pygame.mouse.get_pos()
        hover_name_input = name_input_rect.collidepoint(mouse_pos)
        
        # Determinar a cor da borda baseado no estado do input
        if self.name_input_active:
            border_color = (0, 120, 255)  # Azul quando ativo
        elif hover_name_input:
            border_color = (100, 180, 255)  # Azul claro quando o mouse está em cima
        else:
            border_color = (0, 80, 0)  # Verde escuro quando inativo
        
        # Desenhar campo de texto com cantos arredondados
        pygame.draw.rect(self.screen, WHITE, name_input_rect, border_radius=5)
        pygame.draw.rect(self.screen, border_color, name_input_rect, 2, border_radius=5)
        
        # Texto dentro do campo
        if self.player_name == "":
            name_text = self.small_font.render("Player", True, GRAY)
            self.screen.blit(name_text, (name_input_rect.x + 10, name_input_rect.y + 8))
        else:
            name_text = self.small_font.render(self.player_name, True, BLACK)
            text_rect = name_text.get_rect(midleft=(name_input_rect.x + 10, name_input_rect.centery))
            self.screen.blit(name_text, text_rect)
        
        # Adicionar cursor piscante quando o campo estiver ativo
        if self.name_input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_pos = name_input_rect.x + 10 + name_text.get_width()
            pygame.draw.line(self.screen, BLACK, 
                            (cursor_pos, name_input_rect.y + 5), 
                            (cursor_pos, name_input_rect.y + 25), 2)
        
        # Texto de ajuda abaixo do campo de nome
        hint_text = self.small_font.render("Clique para mudar seu nome", True, (200, 200, 200))
        self.screen.blit(hint_text, (SCREEN_WIDTH // 2 - 90, 185))
        
        # Exibir saldo do jogador
        balance_label = self.medium_font.render(f"Saldo: {self.player_balance} moedas", True, WHITE)
        self.screen.blit(balance_label, (SCREEN_WIDTH // 2 - 150, 220))
        
        # Aviso de saldo baixo
        if self.player_balance <= 100:
            warning_text = self.small_font.render("Saldo baixo!", True, (255, 100, 100))
            self.screen.blit(warning_text, (SCREEN_WIDTH // 2 + 100, 220))
        
        # Desenhar botões do menu
        self.draw_menu_buttons()
        
        # Botão de ajuda no canto superior direito
        help_button = pygame.Rect(SCREEN_WIDTH - 50, 20, 40, 40)
        mouse_pos = pygame.mouse.get_pos()
        help_color = (0, 120, 200) if help_button.collidepoint(mouse_pos) else (0, 80, 160)
        pygame.draw.rect(self.screen, help_color, help_button, border_radius=20)
        pygame.draw.rect(self.screen, WHITE, help_button, 2, border_radius=20)
        help_text = self.medium_font.render("?", True, WHITE)
        help_rect = help_text.get_rect(center=help_button.center)
        self.screen.blit(help_text, help_rect)
        
        # Exibir tutorial em pop-up se ativado
        if self.show_tutorial:
            self.render_tutorial_popup()
    
    def render_tutorial_popup(self):
        """Renderiza o pop-up de tutorial"""
        # Fundo semi-transparente para destacar o pop-up
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))  # Preto semi-transparente
        self.screen.blit(s, (0, 0))
        
        # Desenhar o pop-up
        popup_rect = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 200, 500, 400)
        pygame.draw.rect(self.screen, (0, 80, 0), popup_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, popup_rect, 3, border_radius=10)
        
        # Título do tutorial
        title = self.medium_font.render("Como Jogar Blackjack", True, WHITE)
        title_rect = title.get_rect(midtop=(popup_rect.centerx, popup_rect.y + 20))
        self.screen.blit(title, title_rect)
        
        # Linha separadora
        pygame.draw.line(self.screen, WHITE, 
                        (popup_rect.x + 20, popup_rect.y + 50), 
                        (popup_rect.x + popup_rect.width - 20, popup_rect.y + 50), 2)
        
        # Texto do tutorial
        tutorial_texts = [
            "Objetivo: Chegue o mais próximo possível de 21 pontos sem passar.",
            "Cartas numéricas valem seu número, figuras (J,Q,K) valem 10,",
            "e Ases podem valer 1 ou 11, conforme for melhor para a mão.",
            "",
            "Ações:",
            "- Hit: Peça mais uma carta.",
            "- Stand: Mantenha sua mão e passe a vez.",
            "- Apostar: Defina o valor da sua aposta no início de cada rodada.",
            "",
            "O dealer pega cartas até atingir pelo menos 17 pontos.",
            "Se você ultrapassar 21, perde automaticamente (estouro).",
            "Se o dealer estourar, você ganha.",
            "Se ninguém estourar, ganha quem tiver o valor mais alto."
        ]
        
        y_pos = popup_rect.y + 60
        for text in tutorial_texts:
            rendered_text = self.small_font.render(text, True, WHITE)
            text_rect = rendered_text.get_rect(topleft=(popup_rect.x + 30, y_pos))
            self.screen.blit(rendered_text, text_rect)
            y_pos += 25
        
        # Botão de fechar
        close_text = self.small_font.render("Clique em qualquer lugar para fechar", True, (200, 200, 200))
        close_rect = close_text.get_rect(midbottom=(popup_rect.centerx, popup_rect.bottom - 15))
        self.screen.blit(close_text, close_rect)
    
    def draw_menu_buttons(self):
        """Desenha os botões do menu principal"""
        # Função auxiliar para desenhar botões
        def draw_menu_button(rect, text, color, hover_color=(0, 120, 255)):
            mouse_pos = pygame.mouse.get_pos()
            button_color = hover_color if rect.collidepoint(mouse_pos) else color
            
            # Desenhar botão com cantos arredondados
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=10)
            
            # Texto do botão
            button_text = self.medium_font.render(text, True, WHITE)
            text_rect = button_text.get_rect(center=rect.center)
            self.screen.blit(button_text, text_rect)
        
        # Posicionamento dos botões
        button_width = 250
        button_height = 50
        button_spacing = 20
        start_y = 280
        
        # Botão Jogar Sozinho
        play_alone_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                      start_y, 
                                      button_width, 
                                      button_height)
        draw_menu_button(play_alone_rect, "Jogar Sozinho", (0, 100, 0), (0, 150, 0))
        
        # Botão Jogar Online
        play_online_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                       start_y + button_height + button_spacing, 
                                       button_width, 
                                       button_height)
        draw_menu_button(play_online_rect, "Jogar Online", (0, 80, 150), (0, 100, 200))
        
        # Botão Jogar na Rede Local
        play_local_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                      start_y + 2 * (button_height + button_spacing), 
                                      button_width, 
                                      button_height)
        draw_menu_button(play_local_rect, "Jogar na Rede Local", (150, 100, 0), (200, 130, 0))
        
        # Botão Sair
        exit_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, 
                                start_y + 3 * (button_height + button_spacing), 
                                button_width, 
                                button_height)
        draw_menu_button(exit_rect, "Sair", (150, 0, 0), (200, 0, 0))

    def render_lobby(self):
        """Renderizar a tela de lobby"""
        # Título
        title = self.title_font.render("Lobby", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        # ID do jogo
        if self.game:
            game_id_text = self.medium_font.render(f"ID do Jogo: {self.game.game_id}", True, WHITE)
            self.screen.blit(game_id_text, (100, 150))

            # Status do host
            host_status = self.medium_font.render(
                "Você é o host" if self.host_mode else "Aguardando o host iniciar",
                True, BLUE if self.host_mode else WHITE
            )
            self.screen.blit(host_status, (100, 200))

        # Lista de jogadores
        players_title = self.large_font.render("Jogadores:", True, WHITE)
        self.screen.blit(players_title, (100, 250))

        y_pos = 300
        if self.game_state:
            for player in self.game_state["players"]:
                player_text = self.medium_font.render(
                    f"{player['name']} - Saldo: {player['balance']} " +
                    ("(Host)" if player['is_host'] else ""),
                    True, WHITE
                )
                self.screen.blit(player_text, (120, y_pos))
                y_pos += 40

        # Botões
        if self.host_mode:
            start_button = pygame.Rect(100, 600, 200, 50)
            pygame.draw.rect(self.screen, BLUE, start_button)
            start_text = self.medium_font.render("Iniciar Jogo", True, WHITE)
            self.screen.blit(start_text, (125, 610))

        back_button = pygame.Rect(100, 700, 200, 50)
        pygame.draw.rect(self.screen, RED, back_button)
        back_text = self.medium_font.render("Voltar", True, WHITE)
        self.screen.blit(back_text, (160, 710))

        # Instruções
        instructions = [
            "Aguardando jogadores...",
            "Mínimo de 2 jogadores para iniciar",
            "O host controla o início do jogo"
        ]

        y_pos = 500
        for instruction in instructions:
            text = self.small_font.render(instruction, True, WHITE)
            self.screen.blit(text, (100, y_pos))
            y_pos += 25

    def render_game(self):
        """Renderizar a tela do jogo"""
        if not self.game_state:
            return

        # Background com gradiente
        self.screen.fill((0, 50, 0))  # Verde base escuro
        
        # Área superior (título)
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 60)
        pygame.draw.rect(self.screen, (0, 80, 0), title_bg)
        pygame.draw.rect(self.screen, (0, 100, 0), title_bg, 2)  # Borda
        
        # Título
        title = self.title_font.render("Blackjack 21", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 10))

        # Botão de Voltar ao Menu (apenas no modo single player)
        if len(self.game_state["players"]) <= 4:  # Single player mode
            menu_button = pygame.Rect(10, 10, 120, 40)
            # Efeito hover
            mouse_pos = pygame.mouse.get_pos()
            menu_color = (220, 0, 0) if menu_button.collidepoint(mouse_pos) else (180, 0, 0)
            pygame.draw.rect(self.screen, menu_color, menu_button, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, menu_button, 2, border_radius=10)
            back_text = self.medium_font.render("Menu", True, WHITE)
            text_rect = back_text.get_rect(center=menu_button.center)
            self.screen.blit(back_text, text_rect)

        # Informações do jogador atual
        current_player = self.game_state["players"][self.game_state["current_player_index"]]
        current_player_text = self.medium_font.render(f"Vez de: {current_player['name']}", True, WHITE)
        self.screen.blit(current_player_text, (20, 70))

        # Estado atual do jogo
        state_text = {
            "BETTING": "Fase de Apostas",
            "DEALING": "Distribuindo Cartas",
            "PLAYER_TURN": "Turno dos Jogadores",
            "GAME_OVER": "Fim da Rodada"
        }.get(self.game_state["state"], self.game_state["state"])
        
        state_colors = {
            "BETTING": (0, 100, 200),
            "DEALING": (0, 150, 150),
            "PLAYER_TURN": (0, 150, 0),
            "GAME_OVER": (150, 0, 0)
        }
        
        state_color = state_colors.get(self.game_state["state"], WHITE)
        state_display = self.medium_font.render(state_text, True, state_color)
        state_rect = state_display.get_rect(topright=(SCREEN_WIDTH - 20, 70))
        self.screen.blit(state_display, state_rect)

        # Layout modificado - Divisão da tela em áreas
        # Nova distribuição de espaço:
        # - Área central mais ampla para as cartas
        # - Chat e controles na parte inferior, mais compactos
        # - Posicionamento melhor para evitar sobreposições
        
        # Altura reservada para controles/chat na parte inferior
        FOOTER_HEIGHT = 150
        
        # Área central do jogo (maior, sem bordas invasivas)
        game_area_height = SCREEN_HEIGHT - 100 - FOOTER_HEIGHT
        game_area = pygame.Rect(10, 100, SCREEN_WIDTH - 20, game_area_height)
        # Sem desenhar retângulo preenchido, apenas uma borda sutil
        pygame.draw.rect(self.screen, (0, 100, 0), game_area, 2, border_radius=5)

        # Renderizar cartas e informações de cada jogador
        player_count = len(self.game_state["players"])
        
        # Identificar o jogador humano
        human_player_index = next((i for i, p in enumerate(self.game_state["players"]) 
                                 if not p["name"].startswith("Bot")), 0)
        
        # Definir posições dos jogadores - mais espaço para evitar sobreposições
        # Jogador humano agora está mais acima para evitar sobreposição com os controles
        if player_count == 2:
            player_positions = [
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (SCREEN_WIDTH // 2, 230)                                   # Bot (cima, mais baixo)
            ]
        elif player_count == 3:
            player_positions = [
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (SCREEN_WIDTH // 4, 230),                                  # Bot 1 (esquerda, mais baixo)
                (3 * SCREEN_WIDTH // 4, 230)                               # Bot 2 (direita, mais baixo)
            ]
        elif player_count == 4:
            player_positions = [
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (SCREEN_WIDTH // 4, 230),                                  # Bot 1 (esquerda, mais baixo)
                (SCREEN_WIDTH // 2, 180),                                  # Bot 2 (cima)
                (3 * SCREEN_WIDTH // 4, 230)                               # Bot 3 (direita, mais baixo)
            ]
        else:
            player_positions = [
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - FOOTER_HEIGHT - 120),
                (SCREEN_WIDTH // 2, 230)                                   # Bot mais baixo
            ]
        
        # Tamanho das cartas (maior para o jogador humano)
        HUMAN_CARD_WIDTH = 120
        HUMAN_CARD_HEIGHT = 180
        BOT_CARD_WIDTH = 90
        BOT_CARD_HEIGHT = 135
        
        for i, player in enumerate(self.game_state["players"]):
            x, y = player_positions[i]
            is_human = not player["name"].startswith("Bot")
            
            # Evitar desenhar retângulos de fundo grandes - apenas um painel de informações compacto
            info_height = 70
            info_panel = pygame.Rect(x - 150, y - info_height - 20, 300, info_height)
            
            # Desenhar apenas um fundo sutil para as informações do jogador
            bg_color = (0, 70, 0)  # Cor mais sutil para todos os jogadores
            info_alpha = pygame.Surface((info_panel.width, info_panel.height), pygame.SRCALPHA)
            info_alpha.fill((0, 70, 0, 180))  # Semi-transparente
            self.screen.blit(info_alpha, info_panel)
            
            # Para o jogador atual, um destaque visual
            if player["id"] == current_player["id"]:
                pygame.draw.rect(self.screen, (255, 215, 0), info_panel, 2, border_radius=5)  # Borda dourada
            else:
                pygame.draw.rect(self.screen, (0, 100, 0), info_panel, 1, border_radius=5)  # Borda sutil
            
            # Nome do jogador
            name_font = self.large_font if is_human else self.medium_font
            player_info = name_font.render(f"{player['name']}", True, WHITE)
            self.screen.blit(player_info, (x - player_info.get_width() // 2, y - info_height - 10))
            
            # Informações do jogador - mais compactas
            info_text = f"Saldo: {player['balance']} | Aposta: {player['current_bet']}"
            if show_value := (is_human or self.game_state["state"] == "GAME_OVER"):
                info_text += f" | Valor: {player['hand_value']}"
                if player['is_busted']:
                    info_text += " (Estouro!)"
            
            info_color = RED if player['is_busted'] else WHITE
            player_info_text = self.small_font.render(info_text, True, info_color)
            self.screen.blit(player_info_text, (x - player_info_text.get_width() // 2, y - info_height + 25))

            # Renderizar cartas do jogador com melhor espaçamento
            if 'hand' in player:
                card_width = HUMAN_CARD_WIDTH if is_human else BOT_CARD_WIDTH
                card_height = HUMAN_CARD_HEIGHT if is_human else BOT_CARD_HEIGHT
                
                # Maior espaçamento para o jogador humano, cartas mais espalhadas
                spacing = 40 if is_human else 30
                
                # Calcular largura total e posição inicial para centralizar
                total_width = (len(player['hand']) - 1) * spacing + card_width
                start_x = x - total_width // 2
                
                for j, card in enumerate(player['hand']):
                    card_x = start_x + j * spacing
                    card_y = y
                    
                    # Desenhar fundo preto para a carta, exatamente do mesmo tamanho
                    # Sem bordas extras, apenas um fundo do tamanho da carta
                    self.render_card_back(card_x, card_y, scale=card_width/CARD_WIDTH)
                    
                    # Mostrar cartas viradas para baixo para bots durante o jogo
                    if not is_human and self.game_state["state"] != "GAME_OVER":
                        self.render_card_back(card_x, card_y, scale=card_width/CARD_WIDTH)
                    else:
                        self.render_card(card, card_x, card_y, scale=card_width/CARD_WIDTH)

        # Footer redesenhado - mais elegante e compacto
        footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
        
        # Fundo do footer com gradiente
        footer_rect = pygame.Rect(0, footer_start_y, SCREEN_WIDTH, FOOTER_HEIGHT)
        footer_gradient = pygame.Surface((SCREEN_WIDTH, FOOTER_HEIGHT))
        for y in range(FOOTER_HEIGHT):
            alpha = min(200, int(y * 1.5))
            pygame.draw.line(footer_gradient, (0, 40, 0, alpha), (0, y), (SCREEN_WIDTH, y))
        self.screen.blit(footer_gradient, footer_rect)
        
        # Linha divisória sutil
        pygame.draw.line(self.screen, (0, 100, 0), (0, footer_start_y), (SCREEN_WIDTH, footer_start_y), 2)

        # Área de mensagens redesenhada - mais à direita
        messages_width = SCREEN_WIDTH // 2 - 40
        messages_area = pygame.Rect(SCREEN_WIDTH // 2 + 20, footer_start_y + 10, messages_width, FOOTER_HEIGHT - 20)
        
        # Título da área de mensagens
        msg_title = self.medium_font.render("Mensagens do Jogo", True, WHITE)
        msg_title_rect = msg_title.get_rect(midtop=(messages_area.centerx, footer_start_y + 5))
        self.screen.blit(msg_title, msg_title_rect)

        # Fundo das mensagens semi-transparente
        msg_bg = pygame.Surface((messages_area.width, messages_area.height), pygame.SRCALPHA)
        msg_bg.fill((0, 0, 0, 80))  # Semi-transparente
        self.screen.blit(msg_bg, messages_area)
        pygame.draw.rect(self.screen, (0, 100, 0), messages_area, 1)  # Borda sutil

        # Mensagens do jogo com melhor formatação
        message_y = footer_start_y + 35
        messages = self.game_state["messages"][-5:]  # Limitar a 5 mensagens
        for msg in messages:
            message_text = self.small_font.render(msg, True, WHITE)
            # Limitar o comprimento da mensagem
            if message_text.get_width() > messages_area.width - 20:
                while message_text.get_width() > messages_area.width - 20:
                    msg = msg[:-1]
                    message_text = self.small_font.render(msg + "...", True, WHITE)
            message_rect = message_text.get_rect(x=messages_area.x + 10, y=message_y)
            self.screen.blit(message_text, message_rect)
            message_y += 20  # Menor espaçamento entre mensagens

        # Área de botões - completamente redesenhada
        controls_x = 20
        controls_width = SCREEN_WIDTH // 2 - 40
        button_y = footer_start_y + 45  # Centralizado no footer
        is_our_turn = (current_player["id"] == self.player.player_id)

        def draw_button(rect, color, hover_color, text, enabled=True):
            """Desenha um botão elegante com efeitos de hover e sombra"""
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos) and enabled
            
            alpha = 255 if enabled else 150
            
            # Sombra sutil
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 100))
            self.screen.blit(shadow, shadow_rect)
            
            # Botão com cor baseada no estado (hover/normal/desabilitado)
            button_color = hover_color if is_hover else color
            if not enabled:
                # Dessaturar cores para botões desabilitados
                r, g, b = button_color
                avg = (r + g + b) // 3
                button_color = (avg, avg, avg)
            
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            
            # Borda mais evidente para botões interativos
            border_color = (255, 255, 255, 150) if is_hover else (255, 255, 255, 100)
            border = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(border, border_color, border.get_rect(), 2, border_radius=10)
            self.screen.blit(border, rect)
            
            # Texto com sombra sutil para maior legibilidade
            text_color = (255, 255, 255, alpha)
            text_surface = self.medium_font.render(text, True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            
            # Sombra leve no texto
            shadow_surf = self.medium_font.render(text, True, (0, 0, 0, 100))
            shadow_rect = shadow_surf.get_rect(center=(text_rect.centerx + 1, text_rect.centery + 1))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Texto principal
            self.screen.blit(text_surface, text_rect)
            
            return is_hover

        # Botões específicos baseados no estado do jogo
        if self.game_state["state"] == "BETTING":
            # Área de apostas redesenhada - mais bonita e clara
            bet_panel = pygame.Rect(controls_x, footer_start_y + 10, controls_width, 30)
            pygame.draw.rect(self.screen, (0, 60, 0), bet_panel, border_radius=5)
            pygame.draw.rect(self.screen, (0, 100, 0), bet_panel, 1, border_radius=5)
            
            # Título da aposta
            bet_title = self.medium_font.render("Sua Aposta:", True, WHITE)
            self.screen.blit(bet_title, (controls_x + 10, footer_start_y + 14))
            
            # Valor da aposta em destaque
            bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, WHITE)
            bet_amount_x = controls_x + 120
            self.screen.blit(bet_amount_text, (bet_amount_x, footer_start_y + 14))
            
            # Botões de ajuste de aposta mais visíveis
            btn_width = 36
            btn_height = 36
            btn_y = footer_start_y + 12
            
            # Botão de diminuir aposta
            decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
            pygame.draw.rect(self.screen, (180, 0, 0), decrease_bet_button, border_radius=18)
            pygame.draw.rect(self.screen, WHITE, decrease_bet_button, 2, border_radius=18)
            
            # Texto centralizado no botão
            decrease_text = self.large_font.render("-", True, WHITE)
            decrease_rect = decrease_text.get_rect(center=decrease_bet_button.center)
            self.screen.blit(decrease_text, decrease_rect)
            
            # Botão de aumentar aposta
            increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
            pygame.draw.rect(self.screen, (0, 180, 0), increase_bet_button, border_radius=18)
            pygame.draw.rect(self.screen, WHITE, increase_bet_button, 2, border_radius=18)
            
            # Texto centralizado no botão
            increase_text = self.large_font.render("+", True, WHITE)
            increase_rect = increase_text.get_rect(center=increase_bet_button.center)
            self.screen.blit(increase_text, increase_rect)

            # Botão principal de aposta
            bet_button = pygame.Rect(controls_x, button_y, controls_width, 50)
            draw_button(bet_button, (0, 100, 180), (0, 140, 220), "Confirmar Aposta")

        elif self.game_state["state"] == "PLAYER_TURN":
            # Botões de ação durante o turno
            button_width = (controls_width - 10) // 2
            
            # Botão de Hit
            hit_button = pygame.Rect(controls_x, button_y, button_width, 50)
            draw_button(hit_button, (0, 100, 180), (0, 140, 220), "Pedir Carta", is_our_turn)

            # Botão de Stand
            stand_button = pygame.Rect(controls_x + button_width + 10, button_y, button_width, 50)
            draw_button(stand_button, (180, 0, 0), (220, 0, 0), "Parar", is_our_turn)
            
            # Se não for a vez do jogador, mostrar de quem é a vez
            if not is_our_turn:
                waiting_text = f"Aguardando {current_player['name']}..."
                waiting_surface = self.medium_font.render(waiting_text, True, WHITE)
                waiting_rect = waiting_surface.get_rect(midtop=(controls_x + controls_width // 2, button_y - 40))
                self.screen.blit(waiting_surface, waiting_rect)

        elif self.game_state["state"] == "GAME_OVER":
            # Botão de Nova Rodada
            new_round_button = pygame.Rect(controls_x, button_y, controls_width, 50)
            draw_button(new_round_button, (0, 150, 0), (0, 180, 0), "Nova Rodada")

    def render_card(self, card, x, y, scale=1.0):
        """Renderizar uma carta de baralho com escala personalizada"""
        # Calcular escala baseada no tamanho desejado da carta
        final_scale = self.card_sprites.CARD_WIDTH / CARD_WIDTH * scale
        
        # Obter a sprite da carta com a escala apropriada
        card_sprite = self.card_sprites.get_card(card["suit"], card["value"], final_scale)
        
        # Desenhar a carta na posição especificada
        self.screen.blit(card_sprite, (x, y))

    def render_card_back(self, x, y, scale=1.0):
        """Renderizar o verso de uma carta com escala personalizada"""
        final_scale = self.card_sprites.CARD_WIDTH / CARD_WIDTH * scale
        card_back = self.card_sprites.get_card_back(final_scale)
        self.screen.blit(card_back, (x, y))

    def create_game(self):
        """Criar um novo jogo como host"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        self.game = Game()
        self.game.initialize_game(self.player)

        # Iniciar o servidor P2P
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

        # Criar lobby no serviço de matchmaking
        success, game_id, lobby = self.matchmaking_service.create_game(self.player_name)
        if success:
            self.game.game_id = game_id
            self.current_view = "lobby"
            self.host_mode = True
            self.game_state = self.game.get_game_state()
        else:
            print(f"Erro ao criar lobby: {lobby}")

    def join_game_screen(self):
        """Mostrar tela para entrar em um jogo existente"""
        # Na implementação real, você pode adicionar uma tela para listar lobbies disponíveis
        # Simplificado para este exemplo
        success, lobbies = self.matchmaking_service.list_games()
        if success and lobbies:
            # Apenas entrar no primeiro lobby disponível para este exemplo
            self.join_game(lobbies[0]["game_id"])
        else:
            print("Nenhum jogo disponível")

    def join_game(self, game_id):
        """Entrar em um jogo existente"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar ao lobby
        success, lobby = self.matchmaking_service.join_game(game_id)
        if not success:
            print(f"Erro ao entrar no lobby: {lobby}")
            return

        # Conectar ao host P2P
        host_address = lobby["host_address"]
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.start()

        connect_success, message = self.p2p_manager.connect_to_host(host_address)
        if connect_success:
            # Enviar mensagem de solicitação para entrar
            join_message = Message.create_join_request(
                self.player.player_id,
                self.player.name
            )
            self.p2p_manager.send_message(join_message)

            self.current_view = "lobby"
            self.host_mode = False
        else:
            print(f"Erro ao conectar ao host: {message}")

    def on_message_received(self, sender_id, message):
        """Callback para mensagens recebidas"""
        if message.msg_type == MessageType.GAME_STATE:
            # Atualizar o estado do jogo
            self.game_state = message.content

            # Se o jogo começou, mudar para a view do jogo
            if self.game_state["state"] not in ["WAITING_FOR_PLAYERS"]:
                self.current_view = "game"

        elif message.msg_type == MessageType.JOIN_REQUEST and self.host_mode:
            # Processar solicitação de entrada (apenas o host)
            player_id = message.content["player_id"]
            player_name = message.content["player_name"]

            # Criar novo jogador e adicionar ao jogo
            new_player = Player(player_name, 1000, player_id)
            success, player_index = self.game.add_player(new_player)

            # Enviar resposta
            response = Message.create_join_response(
                self.player.player_id,
                success,
                self.game.game_id if success else None,
                "Jogo já iniciado" if not success else None
            )
            self.p2p_manager.send_message(response, player_id)

            # Atualizar lobby no matchmaking service
            player_list = [p.name for p in self.game.state_manager.players]
            self.matchmaking_service.update_lobby(self.game.game_id, player_list)

            # Enviar estado atualizado do jogo para todos
            self.broadcast_game_state()

        elif message.msg_type == MessageType.JOIN_RESPONSE and not self.host_mode:
            # Processar resposta de solicitação de entrada
            if message.content["accepted"]:
                print(f"Entrou no jogo {message.content['game_id']}")
            else:
                print(f"Falha ao entrar no jogo: {message.content['reason']}")
                self.current_view = "menu"

        elif message.msg_type == MessageType.PLAYER_ACTION:
            # Processar ação do jogador (apenas o host)
            if self.host_mode:
                self.process_player_action(sender_id, message.content)

    def on_player_connected(self, player_id, player_data):
        """Callback para quando um novo jogador se conecta"""
        print(f"Jogador conectado: {player_id}")

    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")

        # Se somos o host, remover o jogador do jogo
        if self.host_mode and self.game:
            self.game.remove_player(player_id)
            self.broadcast_game_state()

    def process_player_action(self, player_id, action_data):
        """Processar uma ação de jogador (host)"""
        action_type = action_data["action_type"]
        action_data = action_data["action_data"]

        if action_type == ActionType.PLACE_BET:
            success, message = self.game.place_bet(player_id, action_data["amount"])
        elif action_type == ActionType.HIT:
            success, message = self.game.hit(player_id)
        elif action_type == ActionType.STAND:
            success, message = self.game.stand(player_id)
        else:
            success, message = False, "Ação desconhecida"

        # Adicionar mensagem ao jogo
        if success:
            self.game.messages.append(message)

        # Atualizar estado do jogo para todos
        self.broadcast_game_state()

    def broadcast_game_state(self):
        """Enviar o estado atual do jogo para todos os jogadores"""
        if self.host_mode and self.game:
            self.game_state = self.game.get_game_state()
            if hasattr(self, 'p2p_manager') and self.p2p_manager:  # Only send messages in multiplayer mode
                game_state_message = Message.create_game_state_message(
                    self.player.player_id,
                    self.game_state
                )
                self.p2p_manager.send_message(game_state_message)

    def hit(self):
        """Pedir mais uma carta"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            hit_message = Message.create_action_message(
                self.player.player_id,
                ActionType.HIT
            )
            self.p2p_manager.send_message(hit_message)
        else:
            # Host processa diretamente
            success, message = self.game.hit(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def stand(self):
        """Parar de pedir cartas"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            stand_message = Message.create_action_message(
                self.player.player_id,
                ActionType.STAND
            )
            self.p2p_manager.send_message(stand_message)
        else:
            # Host processa diretamente
            success, message = self.game.stand(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def place_bet(self):
        """Colocar uma aposta"""
        # Verificar se o jogador tem saldo suficiente
        if self.player.balance < self.bet_amount:
            self.game.messages.append(f"Saldo insuficiente! Você tem apenas {self.player.balance} moedas.")
            # Ajustar a aposta para o valor máximo disponível
            self.bet_amount = self.player.balance
            self.broadcast_game_state()
            return
            
        if not self.host_mode:
            # Cliente envia solicitação para o host
            bet_message = Message.create_action_message(
                self.player.player_id,
                ActionType.PLACE_BET,
                {"amount": self.bet_amount}
            )
            self.p2p_manager.send_message(bet_message)
        else:
            # Host processa diretamente
            success, message = self.game.place_bet(self.player.player_id, self.bet_amount)
            if success:
                self.game.messages.append(f"{self.player.name} apostou {self.bet_amount}")
            self.broadcast_game_state()

    def start_game(self):
        """Iniciar o jogo (apenas host)"""
        if not self.host_mode:
            return

        success, message = self.game.start_game()
        if success:
            self.game.messages.append("O jogo começou!")
            self.current_view = "game"
            self.broadcast_game_state()
        else:
            print(f"Erro ao iniciar o jogo: {message}")

    def new_round(self):
        """Iniciar uma nova rodada"""
        if not self.game:
            return
            
        # Verificar se o jogador foi eliminado (saldo <= 0)
        human_player = next((p for p in self.game.state_manager.players if p.player_id == self.player.player_id), None)
        if human_player:
            eliminated, new_balance = check_player_eliminated(human_player.name, human_player.balance)
            if eliminated:
                self.game.messages.append(f"{human_player.name} foi eliminado! Saldo resetado para 100.")
                human_player.balance = new_balance
                self.player_balance = new_balance
                update_player_balance(human_player.name, new_balance)

        # Resetar o jogo para uma nova rodada
        success, message = self.game.start_new_round()
        if success:
            self.game.messages.append("Nova rodada iniciada!")
            
            # Fazer apostas iniciais automaticamente
            for player in self.game.state_manager.players:
                # Verificar se o jogador tem saldo suficiente
                if player.balance >= 100:
                    self.game.place_bet(player.player_id, 100)
                else:
                    # Se for o jogador humano com saldo insuficiente
                    if player.player_id == self.player.player_id:
                        # Voltar para o menu
                        self.game.messages.append(f"{player.name} não tem saldo suficiente para apostar!")
                        self.current_view = "menu"
                        return
            
            # Distribuir cartas iniciais
            self.game._deal_initial_cards()
            self.broadcast_game_state()
        else:
            print(f"Erro ao iniciar nova rodada: {message}")

    def leave_lobby(self):
        """Sair do lobby e voltar ao menu"""
        if self.p2p_manager:
            self.p2p_manager.close()
            self.p2p_manager = None

        if self.game and self.game.game_id:
            self.matchmaking_service.leave_game(self.game.game_id)

        self.game = None
        self.game_state = None
        self.current_view = "menu"
        self.host_mode = False

    def increase_bet(self):
        """Aumentar o valor da aposta"""
        self.bet_amount += 10
        if self.bet_amount > self.player.balance:
            self.bet_amount = self.player.balance

    def decrease_bet(self):
        """Diminuir o valor da aposta"""
        self.bet_amount -= 10
        if self.bet_amount < 10:
            self.bet_amount = 10

    def create_bot(self, name, strategy="default"):
        """Criar um bot com a estratégia especificada
        Estratégias:
        - default: Para em 17+, pede em 16-
        - aggressive: Para em 18+, pede em 17-
        - conservative: Para em 15+, pede em 14-
        """
        bot_player = Player(name, 1000, str(uuid.uuid4()))
        bot_player.strategy = strategy
        return bot_player

    def start_single_player(self, num_bots=1):
        """Iniciar jogo single player contra o número selecionado de bots"""
        print(f"Iniciando jogo single player com {self.player_name}, saldo: {self.player_balance}")
        
        # Criar jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Criar novo jogo
        self.game = Game()
        
        # Adicionar jogador humano primeiro (para garantir que começa)
        self.game.initialize_game(self.player)
        
        # Criar e adicionar bots com estratégias diferentes
        bot_names = ["Bot Conservador", "Bot Normal", "Bot Agressivo"]
        bot_strategies = ["conservative", "default", "aggressive"]
        
        # Adicionar apenas o número de bots selecionado
        for i in range(min(num_bots, 3)):
            bot_player = self.create_bot(bot_names[i], bot_strategies[i])
            self.game.add_player(bot_player)
        
        # Configurar como host e iniciar o jogo
        self.host_mode = True
        self.current_view = "game"
        
        # Iniciar o jogo
        self.game.start_game()
        self.game_state = self.game.get_game_state()
        self.game.messages.append(f"Jogo iniciado contra {num_bots} bot(s)!")
        
        # Garantir que as apostas iniciais sejam feitas
        initial_bet = min(100, self.player.balance)  # Não apostar mais do que o jogador tem
        self.game.place_bet(self.player.player_id, initial_bet)  # Aposta inicial do jogador
        
        # Apostas iniciais dos bots
        for player in self.game.state_manager.players:
            if player.player_id != self.player.player_id:
                self.game.place_bet(player.player_id, 100)
        
        # Distribuir cartas iniciais
        self.game._deal_initial_cards()
        self.broadcast_game_state()

    def bot_play(self):
        """Lógica de jogo dos bots"""
        if not self.game_state:
            return

        current_player = self.game_state["players"][self.game_state["current_player_index"]]
        # Verifique se o jogador atual é um bot (nome começa com "Bot")
        if not current_player["name"].startswith("Bot"):
            return

        # Lógica de apostas do bot
        if self.game_state["state"] == "BETTING":
            # Bot sempre aposta 100
            self.game.place_bet(current_player["id"], 100)
            self.game.messages.append(f"{current_player['name']} apostou 100")
            self.broadcast_game_state()
            return

        # Lógica de jogo do bot
        if self.game_state["state"] == "PLAYER_TURN":
            # Verificar se o jogador humano estourou
            human_player = next((p for p in self.game_state["players"] if not p["name"].startswith("Bot")), None)
            if human_player and human_player["is_busted"]:
                # Se o jogador humano estourou, o bot para
                success, message = self.game.stand(current_player["id"])
                if success:
                    self.game.messages.append(f"{current_player['name']} parou")
                self.broadcast_game_state()
                return

            # Esperar um pouco para simular "pensamento"
            time.sleep(0.5)  # Reduzido para manter o jogo fluido com múltiplos bots

            # Encontrar a estratégia do bot atual
            hand_value = current_player["hand_value"]
            bot_player = next((p for p in self.game.state_manager.players if p.player_id == current_player["id"]), None)
            
            if bot_player:
                strategy = getattr(bot_player, "strategy", "default")
                
                # Aplicar estratégia
                limit = 17  # Padrão
                if strategy == "aggressive":
                    limit = 18
                elif strategy == "conservative":
                    limit = 15
                
                if hand_value < limit:
                    success, message = self.game.hit(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} pediu carta")
                else:
                    success, message = self.game.stand(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} parou")

            self.broadcast_game_state()

    def check_winner(self):
        """Verificar o vencedor da rodada"""
        if not self.game_state:
            return

        players = self.game_state["players"]
        
        # Separar jogadores humanos e bots
        human_player = next((p for p in players if not p["name"].startswith("Bot")), None)
        if not human_player:
            return
            
        active_players = [p for p in players if not p["is_busted"]]
        
        # Se todos estouraram, não há vencedor
        if not active_players:
            self.game.messages.append("Todos estouraram! Ninguém ganha.")
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se apenas um jogador não estourou, ele é o vencedor
        if len(active_players) == 1:
            winner = active_players[0]
            self.game.messages.append(f"{winner['name']} venceu! (Único jogador não estourado)")
            
            # Processar resultado (apenas para jogadores humanos)
            if winner["name"] == self.player.name:
                old_balance = self.player.balance
                # Calcular o prêmio (soma de todas as apostas)
                total_pot = sum(p["current_bet"] for p in players)
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance} (ganhou {total_pot})")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
                
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se múltiplos jogadores não estouraram, encontre o maior valor
        max_value = max(p["hand_value"] for p in active_players)
        winners = [p for p in active_players if p["hand_value"] == max_value]
        
        # Anunciar vencedores
        if len(winners) == 1:
            self.game.messages.append(f"{winners[0]['name']} venceu com {max_value} pontos!")
            
            # Processar resultado (apenas para jogadores humanos)
            if winners[0]["name"] == self.player.name:
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
        else:
            winner_names = ", ".join(w["name"] for w in winners)
            self.game.messages.append(f"Empate entre {winner_names} com {max_value} pontos!")
            
            # Verificar se o jogador humano está entre os vencedores
            if any(w["name"] == self.player.name for w in winners):
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} empatou! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
            
        self.game_state["state"] = "GAME_OVER"
        self.broadcast_game_state()

    def render_bot_selection(self):
        """Renderizar a tela de seleção de bots"""
        # Background
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        title = self.title_font.render("Selecione o Número de Bots", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        def draw_selection_button(rect, text, color, hover_color):
            """Desenhar botão de seleção com efeito hover"""
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            
            # Sombra
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pygame.draw.rect(self.screen, (0, 0, 0, 128), shadow_rect, border_radius=15)
            
            # Botão
            current_color = hover_color if is_hover else color
            pygame.draw.rect(self.screen, current_color, rect, border_radius=15)
            
            # Borda
            if is_hover:
                pygame.draw.rect(self.screen, (255, 255, 255, 128), rect, 2, border_radius=15)
            
            # Texto
            text_surface = self.medium_font.render(text, True, (240, 240, 240))
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Botões para selecionar o número de bots
        button_width = 300
        button_height = 60
        button_x = SCREEN_WIDTH // 2 - button_width // 2
        
        # Cores dos botões
        button_colors = [
            ((0, 100, 180), (0, 140, 230)),  # 1 Bot
            ((0, 130, 150), (0, 170, 190)),  # 2 Bots
            ((0, 150, 120), (0, 190, 160)),  # 3 Bots
            ((150, 30, 30), (190, 50, 50))   # Voltar
        ]
        
        # Botão para 1 bot
        bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
        draw_selection_button(bot1_button, "Jogar com 1 Bot", button_colors[0][0], button_colors[0][1])
        
        # Botão para 2 bots
        bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
        draw_selection_button(bot2_button, "Jogar com 2 Bots", button_colors[1][0], button_colors[1][1])
        
        # Botão para 3 bots
        bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
        draw_selection_button(bot3_button, "Jogar com 3 Bots", button_colors[2][0], button_colors[2][1])
        
        # Botão para voltar
        back_button = pygame.Rect(button_x, 460, button_width, button_height)
        draw_selection_button(back_button, "Voltar", button_colors[3][0], button_colors[3][1])
        
        # Descrição dos tipos de bots
        info_y = 550
        info_texts = [
            "Bot Conservador: Para com 15+ pontos",
            "Bot Normal: Para com 17+ pontos",
            "Bot Agressivo: Para com 18+ pontos"
        ]
        
        info_rect = pygame.Rect(SCREEN_WIDTH // 2 - 300, info_y - 20, 600, 150)
        pygame.draw.rect(self.screen, (0, 50, 0), info_rect, border_radius=10)
        pygame.draw.rect(self.screen, (0, 80, 0), info_rect, 2, border_radius=10)
        
        for i, text in enumerate(info_texts):
            info_text = self.small_font.render(text, True, (220, 220, 220))
            text_rect = info_text.get_rect(centerx=SCREEN_WIDTH // 2, y=info_y + i * 30)
            self.screen.blit(info_text, text_rect)

    def render_message(self, message, color):
        """Renderizar uma mensagem temporária na tela"""
        message_surface = self.medium_font.render(message, True, color)
        message_rect = message_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        
        # Fundo semi-transparente
        padding = 10
        bg_rect = pygame.Rect(message_rect.x - padding, message_rect.y - padding, 
                            message_rect.width + padding * 2, message_rect.height + padding * 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 150))
        self.screen.blit(bg_surface, bg_rect)
        
        # Desenhar borda
        pygame.draw.rect(self.screen, color, bg_rect, 2, border_radius=5)
        
        # Desenhar mensagem
        self.screen.blit(message_surface, message_rect)

    def render_create_room(self):
        """Renderizar a tela de criação de sala"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        # Título
        title = self.title_font.render("Criar Sala", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Área central com informações da sala
        form_width = 500
        form_height = 420
        form_x = SCREEN_WIDTH // 2 - form_width // 2
        form_y = 140
        
        form_bg = pygame.Rect(form_x, form_y, form_width, form_height)
        pygame.draw.rect(self.screen, (0, 60, 0), form_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), form_bg, 2, border_radius=10)
        
        y_offset = form_y + 30
        
        # ID da Sala (gerado automaticamente)
        id_label = self.medium_font.render("ID da Sala:", True, WHITE)
        self.screen.blit(id_label, (form_x + 30, y_offset))
        
        id_value = self.large_font.render(self.room_id, True, (255, 220, 0))
        self.screen.blit(id_value, (form_x + 250, y_offset))
        
        id_info = self.small_font.render("(Compartilhe este código com seus amigos)", True, (200, 200, 200))
        self.screen.blit(id_info, (form_x + 30, y_offset + 40))
        
        y_offset += 80
        
        # Nome da Sala
        name_label = self.medium_font.render("Nome da Sala:", True, WHITE)
        self.screen.blit(name_label, (form_x + 30, y_offset))
        
        # Campo de entrada para o nome da sala
        name_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.room_name_input_active:
            name_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            name_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, name_border_color, name_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(name_box.x + 2, name_box.y + 2, 
                                                             name_box.width - 4, name_box.height - 4), border_radius=5)
        
        # Texto do nome da sala
        cursor = "|" if self.room_name_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        name_text = self.medium_font.render(self.room_name_input + cursor, True, (0, 0, 0))
        self.screen.blit(name_text, (name_box.x + 10, name_box.y + 5))
        
        y_offset += 100
        
        # Senha
        password_label = self.medium_font.render("Senha da Sala:", True, WHITE)
        self.screen.blit(password_label, (form_x + 30, y_offset))
        
        # Campo de entrada para a senha
        password_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.password_input_active:
            password_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            password_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, password_border_color, password_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(password_box.x + 2, password_box.y + 2, 
                                                                  password_box.width - 4, password_box.height - 4), border_radius=5)
        
        # Texto da senha (mostrado como asteriscos)
        password_display = "*" * len(self.password_input)
        cursor = "|" if self.password_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        password_text = self.medium_font.render(password_display + cursor, True, (0, 0, 0))
        self.screen.blit(password_text, (password_box.x + 10, password_box.y + 5))
        
        password_info = self.small_font.render("Deixe em branco para sala sem senha", True, (200, 200, 200))
        self.screen.blit(password_info, (form_x + 30, y_offset + 90))
        
        y_offset += 140
        
        # Seleção de modo de conexão
        mode_label = self.medium_font.render("Modo de Conexão:", True, WHITE)
        self.screen.blit(mode_label, (form_x + 30, y_offset))
        
        # Opções de modo
        online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
        local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)
        
        # Destacar a opção selecionada
        if self.connection_mode_selection == "online":
            pygame.draw.rect(self.screen, (0, 120, 210), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 80, 0), local_rect, border_radius=5)
        else:
            pygame.draw.rect(self.screen, (0, 80, 0), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 120, 210), local_rect, border_radius=5)
        
        # Texto dos botões
        online_text = self.medium_font.render("Online", True, WHITE)
        local_text = self.medium_font.render("Rede Local", True, WHITE)
        
        online_text_rect = online_text.get_rect(center=online_rect.center)
        local_text_rect = local_text.get_rect(center=local_rect.center)
        
        self.screen.blit(online_text, online_text_rect)
        self.screen.blit(local_text, local_text_rect)
        
        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 600
        
        # Botão Criar
        create_button = pygame.Rect(SCREEN_WIDTH // 2 - 220, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        create_color = (0, 150, 0) if create_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)
        
        # Botão Cancelar
        cancel_button = pygame.Rect(SCREEN_WIDTH // 2 + 20, button_y, button_width, button_height)
        cancel_color = (150, 0, 0) if cancel_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, cancel_color, cancel_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, cancel_button, 2, border_radius=10)
        cancel_text = self.medium_font.render("Cancelar", True, WHITE)
        cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
        self.screen.blit(cancel_text, cancel_text_rect)
    
    def handle_create_room_event(self, event):
        """Manipular eventos na tela de criação de sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Ativar/desativar campos de entrada
            form_x = SCREEN_WIDTH // 2 - 250
            
            # Campo Nome da Sala
            name_box = pygame.Rect(form_x + 30, 140 + 120, 440, 40)
            if name_box.collidepoint(mouse_pos):
                self.room_name_input_active = True
                self.password_input_active = False
            
            # Campo Senha
            password_box = pygame.Rect(form_x + 30, 140 + 220, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_name_input_active = False
            
            # Botões de modo de conexão
            online_rect = pygame.Rect(form_x + 30, 140 + 320, 200, 40)
            local_rect = pygame.Rect(form_x + 270, 140 + 320, 200, 40)
            
            if online_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "local"
            
            # Botões de ação
            button_width = 200
            button_height = 50
            button_y = 600
            
            # Botão Criar
            create_button = pygame.Rect(SCREEN_WIDTH // 2 - 220, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.create_room()
            
            # Botão Cancelar
            cancel_button = pygame.Rect(SCREEN_WIDTH // 2 + 20, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                
        # Entrada de teclado para os campos ativos
        elif event.type == pygame.KEYDOWN:
            if self.room_name_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_name_input = self.room_name_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_name_input_active = False
                elif len(self.room_name_input) < 30:  # Limitar tamanho do nome
                    if event.unicode.isprintable():
                        self.room_name_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:  # Limitar tamanho da senha
                    if event.unicode.isprintable():
                        self.password_input += event.unicode
    
    def create_room(self):
        """Criar uma sala de jogo"""
        if not self.room_name_input:
            self.error_message = "O nome da sala não pode estar vazio"
            self.message_timer = pygame.time.get_ticks()
            return
        
        # Configurar o modo de conexão
        self.connection_mode = self.connection_mode_selection
        
        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Criar o jogo
        self.game = Game()
        self.game.initialize_game(self.player)
        
        # Definir o ID da sala
        self.game.game_id = self.room_id
        self.game.room_name = self.room_name_input
        self.game.password = self.password_input
        
        # Configurar servidor baseado no modo de conexão
        if self.connection_mode == "online":
            self.setup_online_server()
        else:
            self.setup_local_server()
        
        # Registrar o jogo no serviço de matchmaking
        # (o método será diferente dependendo do modo selecionado)
        if self.connection_mode == "online":
            self.register_online_room()
        else:
            self.register_local_room()
        
        # Exibir mensagem de sucesso
        self.success_message = "Sala criada com sucesso!"
        self.message_timer = pygame.time.get_ticks()
        
        # Mover para o lobby
        self.current_view = "lobby"
        self.host_mode = True
        self.game_state = self.game.get_game_state()
    
    def setup_online_server(self):
        """Configurar servidor para conexão online"""
        # TODO: Implementar servidor online usando sockets
        # Esta configuração deve permitir conexões pela internet
        # usando um servidor intermediário ou conexão direta
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
    
    def setup_local_server(self):
        """Configurar servidor para conexão em rede local"""
        # TODO: Implementar servidor local usando sockets
        # Esta configuração deve descobrir automaticamente 
        # jogadores na mesma rede local
        self.p2p_manager = P2PManager(host=True, local_network=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
    
    def register_online_room(self):
        """Registrar a sala no serviço de matchmaking online"""
        # TODO: Implementar registro no servidor de matchmaking online
        success, game_id, lobby = self.matchmaking_service.create_game(
            self.player_name, 
            room_name=self.room_name_input,
            password=self.password_input
        )
        
        if success:
            self.game.game_id = game_id
        else:
            self.error_message = f"Erro ao criar sala: {lobby}"
            self.message_timer = pygame.time.get_ticks()
    
    def register_local_room(self):
        """Registrar a sala para descoberta na rede local"""
        # TODO: Implementar broadcast na rede local para anunciar a sala
        # Usar sockets UDP para broadcast na rede local
        success, game_id, lobby = self.matchmaking_service.create_local_game(
            self.player_name, 
            room_name=self.room_name_input,
            password=self.password_input
        )

    def render_join_room(self):
        """Renderizar a tela para juntar-se a uma sala específica usando o ID"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        # Título
        title = self.title_font.render("Juntar-se a uma Sala", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Área central
        form_width = 500
        form_height = 300
        form_x = SCREEN_WIDTH // 2 - form_width // 2
        form_y = 150
        
        form_bg = pygame.Rect(form_x, form_y, form_width, form_height)
        pygame.draw.rect(self.screen, (0, 60, 0), form_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), form_bg, 2, border_radius=10)
        
        y_offset = form_y + 30
        
        # ID da Sala
        id_label = self.medium_font.render("ID da Sala:", True, WHITE)
        self.screen.blit(id_label, (form_x + 30, y_offset))
        
        # Campo de entrada para o ID da sala
        id_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.room_id_input_active:
            id_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            id_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, id_border_color, id_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(id_box.x + 2, id_box.y + 2, 
                                                             id_box.width - 4, id_box.height - 4), border_radius=5)
        
        # Texto do ID da sala
        cursor = "|" if self.room_id_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        id_text = self.medium_font.render(self.room_id_input + cursor, True, (0, 0, 0))
        self.screen.blit(id_text, (id_box.x + 10, id_box.y + 5))
        
        y_offset += 100
        
        # Senha
        password_label = self.medium_font.render("Senha da Sala:", True, WHITE)
        self.screen.blit(password_label, (form_x + 30, y_offset))
        
        # Campo de entrada para a senha
        password_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)
        
        # Cor da borda baseada no estado de foco
        if self.password_input_active:
            password_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            password_border_color = (0, 100, 0)  # Verde escuro padrão
        
        pygame.draw.rect(self.screen, password_border_color, password_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(password_box.x + 2, password_box.y + 2, 
                                                                  password_box.width - 4, password_box.height - 4), border_radius=5)
        
        # Texto da senha (mostrado como asteriscos)
        password_display = "*" * len(self.password_input)
        cursor = "|" if self.password_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        password_text = self.medium_font.render(password_display + cursor, True, (0, 0, 0))
        self.screen.blit(password_text, (password_box.x + 10, password_box.y + 5))
        
        password_info = self.small_font.render("Deixe em branco para salas sem senha", True, (200, 200, 200))
        self.screen.blit(password_info, (form_x + 30, y_offset + 90))
        
        y_offset += 120
        
        # Seleção de modo de conexão
        mode_label = self.medium_font.render("Modo de Conexão:", True, WHITE)
        self.screen.blit(mode_label, (form_x + 30, y_offset))
        
        # Opções de modo
        online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
        local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)
        
        # Destacar a opção selecionada
        if self.connection_mode_selection == "online":
            pygame.draw.rect(self.screen, (0, 120, 210), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 80, 0), local_rect, border_radius=5)
        else:
            pygame.draw.rect(self.screen, (0, 80, 0), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 120, 210), local_rect, border_radius=5)
        
        # Texto dos botões
        online_text = self.medium_font.render("Online", True, WHITE)
        local_text = self.medium_font.render("Rede Local", True, WHITE)
        
        online_text_rect = online_text.get_rect(center=online_rect.center)
        local_text_rect = local_text.get_rect(center=local_rect.center)
        
        self.screen.blit(online_text, online_text_rect)
        self.screen.blit(local_text, local_text_rect)
        
        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 500
        
        # Botão Buscar Salas
        browse_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        browse_color = (0, 130, 180) if browse_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, browse_color, browse_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, browse_button, 2, border_radius=10)
        browse_text = self.medium_font.render("Lista de Salas", True, WHITE)
        browse_text_rect = browse_text.get_rect(center=browse_button.center)
        self.screen.blit(browse_text, browse_text_rect)
        
        # Botão Entrar
        join_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, join_color, join_button, border_radius=10)
    
    def render_room_browser(self):
        """Renderizar a tela de navegação de salas disponíveis"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Área do título
        title_bg = pygame.Rect(0, 0, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        # Título
        mode_text = "Online" if self.connection_mode == "online" else "Rede Local"
        title = self.title_font.render(f"Salas Disponíveis ({mode_text})", True, (240, 240, 240))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Botão de Atualizar
        refresh_button = pygame.Rect(SCREEN_WIDTH - 160, 60, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        refresh_color = (0, 130, 200) if refresh_button.collidepoint(mouse_pos) else (0, 100, 170)
        pygame.draw.rect(self.screen, refresh_color, refresh_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, refresh_button, 2, border_radius=10)
        refresh_text = self.small_font.render("Atualizar", True, WHITE)
        refresh_text_rect = refresh_text.get_rect(center=refresh_button.center)
        self.screen.blit(refresh_text, refresh_text_rect)
        
        # Área central com a lista de salas
        list_width = 800
        list_height = 400
        list_x = SCREEN_WIDTH // 2 - list_width // 2
        list_y = 150
        
        list_bg = pygame.Rect(list_x, list_y, list_width, list_height)
        pygame.draw.rect(self.screen, (0, 60, 0), list_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), list_bg, 2, border_radius=10)
        
        # Cabeçalhos da lista
        header_y = list_y + 20
        headers = [
            {"text": "ID", "x": list_x + 50, "width": 100},
            {"text": "Nome da Sala", "x": list_x + 150, "width": 300},
            {"text": "Jogadores", "x": list_x + 470, "width": 100},
            {"text": "Protegida", "x": list_x + 590, "width": 120},
            {"text": "", "x": list_x + 720, "width": 80}  # Coluna para o botão Entrar
        ]
        
        for header in headers:
            text = self.medium_font.render(header["text"], True, (220, 220, 220))
            self.screen.blit(text, (header["x"], header_y))
        
        # Desenhar linha de separação
        pygame.draw.line(self.screen, (0, 100, 0), (list_x + 20, header_y + 40), 
                        (list_x + list_width - 20, header_y + 40), 2)
        
        # Mensagem se não houver salas
        if not self.room_list:
            no_rooms_text = self.medium_font.render("Nenhuma sala disponível", True, (200, 200, 200))
            no_rooms_rect = no_rooms_text.get_rect(center=(list_x + list_width // 2, list_y + list_height // 2))
            self.screen.blit(no_rooms_text, no_rooms_rect)
        else:
            # Lista de salas
            item_height = 50
            visible_items = 6  # Número de itens visíveis na tela
            start_index = self.room_browser_scroll
            end_index = min(start_index + visible_items, len(self.room_list))
            
            for i in range(start_index, end_index):
                room = self.room_list[i]
                item_y = header_y + 60 + (i - start_index) * item_height
                
                # Destacar a sala selecionada
                if i == self.selected_room_index:
                    selection_rect = pygame.Rect(list_x + 10, item_y - 5, list_width - 20, item_height)
                    pygame.draw.rect(self.screen, (0, 80, 0), selection_rect, border_radius=5)
                
                # ID da sala
                id_text = self.medium_font.render(room["id"], True, WHITE)
                self.screen.blit(id_text, (list_x + 50, item_y))
                
                # Nome da sala
                name_text = self.medium_font.render(room["name"], True, WHITE)
                self.screen.blit(name_text, (list_x + 150, item_y))
                
                # Número de jogadores
                players_text = self.medium_font.render(f"{room['player_count']}/8", True, WHITE)
                self.screen.blit(players_text, (list_x + 470, item_y))
                
                # Indicação se tem senha
                has_password = room.get("has_password", False)
                password_text = self.medium_font.render("Sim" if has_password else "Não", True, 
                                                       (255, 150, 150) if has_password else (150, 255, 150))
                self.screen.blit(password_text, (list_x + 590, item_y))
                
                # Botão Entrar
                join_button = pygame.Rect(list_x + 720, item_y - 5, 60, 30)
                join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
                pygame.draw.rect(self.screen, join_color, join_button, border_radius=5)
                pygame.draw.rect(self.screen, WHITE, join_button, 1, border_radius=5)
                join_text = self.small_font.render("Entrar", True, WHITE)
                join_text_rect = join_text.get_rect(center=join_button.center)
                self.screen.blit(join_text, join_text_rect)
            
            # Controles de scroll
            if len(self.room_list) > visible_items:
                # Botão para cima
                up_button = pygame.Rect(list_x + list_width - 40, list_y + 20, 30, 30)
                up_color = (0, 130, 200) if up_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, up_color, up_button, border_radius=5)
                up_text = self.medium_font.render("▲", True, WHITE)
                up_text_rect = up_text.get_rect(center=up_button.center)
                self.screen.blit(up_text, up_text_rect)
                
                # Botão para baixo
                down_button = pygame.Rect(list_x + list_width - 40, list_y + list_height - 50, 30, 30)
                down_color = (0, 130, 200) if down_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, down_color, down_button, border_radius=5)
                down_text = self.medium_font.render("▼", True, WHITE)
                down_text_rect = down_text.get_rect(center=down_button.center)
                self.screen.blit(down_text, down_text_rect)
        
        # Botões de alternância de modo
        mode_y = list_y + list_height + 20
        
        # Botão de modo Online
        online_button = pygame.Rect(SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
        online_color = (0, 120, 210) if self.connection_mode == "online" else (0, 80, 0)
        pygame.draw.rect(self.screen, online_color, online_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, online_button, 2 if self.connection_mode == "online" else 1, border_radius=10)
        online_text = self.medium_font.render("Online", True, WHITE)
        online_text_rect = online_text.get_rect(center=online_button.center)
        self.screen.blit(online_text, online_text_rect)
        
        # Botão de modo Rede Local
        local_button = pygame.Rect(SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
        local_color = (0, 120, 210) if self.connection_mode == "local" else (0, 80, 0)
        pygame.draw.rect(self.screen, local_color, local_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, local_button, 2 if self.connection_mode == "local" else 1, border_radius=10)
        local_text = self.medium_font.render("Rede Local", True, WHITE)
        local_text_rect = local_text.get_rect(center=local_button.center)
        self.screen.blit(local_text, local_text_rect)
        
        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 650
        
        # Botão Criar Sala
        create_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        create_color = (0, 150, 100) if create_button.collidepoint(mouse_pos) else (0, 120, 80)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)
        
        # Botão Entrar com ID
        join_id_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_id_color = (0, 130, 180) if join_id_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, join_id_color, join_id_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, join_id_button, 2, border_radius=10)
        join_id_text = self.medium_font.render("Entrar com ID", True, WHITE)
        join_id_text_rect = join_id_text.get_rect(center=join_id_button.center)
        self.screen.blit(join_id_text, join_id_text_rect)
        
        # Botão Voltar
        back_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        back_color = (150, 0, 0) if back_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, back_color, back_button, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, back_button, 2, border_radius=10)
        back_text = self.medium_font.render("Voltar", True, WHITE)
        back_text_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    def handle_room_browser_event(self, event):
        """Manipular eventos na tela de lista de salas"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botão de Atualizar
            refresh_button = pygame.Rect(SCREEN_WIDTH - 160, 60, 120, 40)
            if refresh_button.collidepoint(mouse_pos):
                self.load_room_list(self.connection_mode)
                return
            
            # Área da lista de salas
            list_width = 800
            list_height = 400
            list_x = SCREEN_WIDTH // 2 - list_width // 2
            list_y = 150
            
            # Verificar clique em salas
            if self.room_list:
                item_height = 50
                visible_items = 6
                start_index = self.room_browser_scroll
                end_index = min(start_index + visible_items, len(self.room_list))
                
                for i in range(start_index, end_index):
                    item_y = list_y + 80 + (i - start_index) * item_height
                    
                    # Seleção da sala
                    selection_area = pygame.Rect(list_x + 10, item_y - 5, list_width - 100, item_height)
                    if selection_area.collidepoint(mouse_pos):
                        self.selected_room_index = i
                    
                    # Botão Entrar
                    join_button = pygame.Rect(list_x + 720, item_y - 5, 60, 30)
                    if join_button.collidepoint(mouse_pos):
                        self.join_selected_room(i)
                        return
            
            # Controles de scroll
            if len(self.room_list) > 6:
                # Botão para cima
                up_button = pygame.Rect(list_x + list_width - 40, list_y + 20, 30, 30)
                if up_button.collidepoint(mouse_pos) and self.room_browser_scroll > 0:
                    self.room_browser_scroll -= 1
                    return
                
                # Botão para baixo
                down_button = pygame.Rect(list_x + list_width - 40, list_y + list_height - 50, 30, 30)
                if down_button.collidepoint(mouse_pos) and self.room_browser_scroll < len(self.room_list) - 6:
                    self.room_browser_scroll += 1
                    return
            
            # Botões de alternância de modo
            mode_y = list_y + list_height + 20
            
            # Botão de modo Online
            online_button = pygame.Rect(SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
            if online_button.collidepoint(mouse_pos) and self.connection_mode != "online":
                self.connection_mode = "online"
                self.load_room_list("online")
                return
            
            # Botão de modo Rede Local
            local_button = pygame.Rect(SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
            if local_button.collidepoint(mouse_pos) and self.connection_mode != "local":
                self.connection_mode = "local"
                self.load_room_list("local")
                return
            
            # Botões de ação
            button_width = 200
            button_height = 50
            button_y = 650
            
            # Botão Criar Sala
            create_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.handle_create_room_click()
                return
            
            # Botão Entrar com ID
            join_id_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
            if join_id_button.collidepoint(mouse_pos):
                self.current_view = "join_room"
                return
            
            # Botão Voltar
            back_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return
    
    def load_room_list(self, mode="online"):
        """Carregar a lista de salas disponíveis"""
        self.connection_mode = mode
        self.selected_room_index = -1
        self.room_browser_scroll = 0
        
        if mode == "online":
            # Buscar salas online
            success, rooms = self.matchmaking_service.list_games()
            if success:
                self.room_list = []
                for room in rooms:
                    self.room_list.append({
                        "id": room["game_id"],
                        "name": room.get("room_name", f"Sala de {room['host_name']}"),
                        "player_count": len(room["players"]),
                        "has_password": room.get("has_password", False),
                        "host_address": room["host_address"],
                        "host_name": room["host_name"]
                    })
            else:
                self.error_message = "Não foi possível buscar as salas online"
                self.message_timer = pygame.time.get_ticks()
        else:
            # Buscar salas na rede local usando broadcast UDP
            success, rooms = self.matchmaking_service.list_local_games()
            if success:
                self.room_list = []
                for room in rooms:
                    self.room_list.append({
                        "id": room["game_id"],
                        "name": room.get("room_name", f"Sala de {room['host_name']}"),
                        "player_count": len(room["players"]),
                        "has_password": room.get("has_password", False),
                        "host_address": room["host_address"],
                        "host_name": room["host_name"]
                    })
            else:
                self.error_message = "Não foi possível buscar as salas na rede local"
                self.message_timer = pygame.time.get_ticks()
    
    def join_selected_room(self, room_index):
        """Entrar na sala selecionada"""
        if not self.room_list or room_index < 0 or room_index >= len(self.room_list):
            return
        
        room = self.room_list[room_index]
        
        # Se a sala tem senha, mostrar tela para digitar a senha
        if room.get("has_password", False):
            self.room_id_input = room["id"]
            self.password_input = ""
            self.password_input_active = True
            self.room_id_input_active = False
            self.current_view = "join_room"
            return
        
        # Se não tem senha, entrar diretamente
        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Conectar à sala
        success = False
        if self.connection_mode == "online":
            success = self.connect_to_online_room(room["id"], "")
        else:
            success = self.connect_to_local_room(room["id"], "")
        
        if success:
            self.current_view = "lobby"
            self.host_mode = False
            self.success_message = "Conectado à sala com sucesso!"
            self.message_timer = pygame.time.get_ticks()
        else:
            self.error_message = "Não foi possível conectar à sala. Tente novamente."
            self.message_timer = pygame.time.get_ticks()

    def connect_to_online_room(self, room_id, password=""):
        """Conectar a uma sala online usando o ID da sala"""
        # Verificar se o ID da sala foi informado
        if not room_id:
            self.error_message = "ID da sala não informado"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter informações da sala do serviço de matchmaking
        success, room_info = self.matchmaking_service.get_room_info(room_id)
        if not success:
            self.error_message = "Sala não encontrada"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Verificar senha se necessário
        if room_info.get("has_password", False) and room_info.get("password") != password:
            self.error_message = "Senha incorreta"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter endereço do host
        host_address = room_info.get("host_address")
        if not host_address:
            self.error_message = "Endereço do host não disponível"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Configurar conexão P2P como cliente
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
        
        # Conectar ao host
        connect_success, connection_message = self.p2p_manager.connect_to_host(host_address)
        if not connect_success:
            self.error_message = f"Erro ao conectar ao host: {connection_message}"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Enviar solicitação para entrar na sala
        join_message = Message.create_join_request(
            self.player.player_id,
            self.player.name,
            password=password
        )
        self.p2p_manager.send_message(join_message)
        
        # Juntar-se ao jogo no serviço de matchmaking
        self.matchmaking_service.join_game(room_id, self.player_name)
        
        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        return True

    def connect_to_local_room(self, room_id, password=""):
        """Conectar a uma sala na rede local usando o ID da sala"""
        # Verificar se o ID da sala foi informado
        if not room_id:
            self.error_message = "ID da sala não informado"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter informações da sala localmente via broadcast UDP
        success, room_info = self.matchmaking_service.get_local_room_info(room_id)
        if not success:
            self.error_message = "Sala não encontrada na rede local"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Verificar senha se necessário
        if room_info.get("has_password", False) and room_info.get("password") != password:
            self.error_message = "Senha incorreta"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Obter endereço do host
        host_address = room_info.get("host_address")
        if not host_address:
            self.error_message = "Endereço do host não disponível"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Configurar conexão P2P como cliente
        self.p2p_manager = P2PManager(host=False, local_network=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()
        
        # Conectar ao host
        connect_success, connection_message = self.p2p_manager.connect_to_host(host_address)
        if not connect_success:
            self.error_message = f"Erro ao conectar ao host: {connection_message}"
            self.message_timer = pygame.time.get_ticks()
            return False
        
        # Enviar solicitação para entrar na sala
        join_message = Message.create_join_request(
            self.player.player_id,
            self.player.name,
            password=password
        )
        self.p2p_manager.send_message(join_message)
        
        # Registrar entrada no jogo local
        self.matchmaking_service.join_local_game(room_id, self.player_name)
        
        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        return True

    def handle_join_room_event(self, event):
        """Manipular eventos na tela de juntar-se a uma sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            form_x = SCREEN_WIDTH // 2 - 250
            form_y = 150
            
            # Ativar/desativar campos de entrada
            # Campo ID da Sala
            id_box = pygame.Rect(form_x + 30, form_y + 70, 440, 40)
            if id_box.collidepoint(mouse_pos):
                self.room_id_input_active = True
                self.password_input_active = False
            
            # Campo Senha
            password_box = pygame.Rect(form_x + 30, form_y + 170, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_id_input_active = False
            
            # Botões de modo de conexão
            y_offset = form_y + 250
            online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
            local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)
            
            if online_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "local"
            
            # Botão Buscar Salas
            button_width = 200
            button_height = 50
            button_y = 500
            browse_button = pygame.Rect(SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if browse_button.collidepoint(mouse_pos):
                self.current_view = "room_browser"
                self.connection_mode = self.connection_mode_selection
                self.load_room_list(mode=self.connection_mode)
                return
            
            # Botão Entrar
            join_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
            if join_button.collidepoint(mouse_pos):
                self.join_room_by_id()
                return
            
            # Botão Cancelar
            cancel_button = pygame.Rect(SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return
                
        # Entrada de teclado para os campos ativos
        elif event.type == pygame.KEYDOWN:
            if self.room_id_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_id_input = self.room_id_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_id_input_active = False
                elif len(self.room_id_input) < 8:  # Limitar tamanho do ID
                    if event.unicode.isdigit():  # Aceitar apenas dígitos
                        self.room_id_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:  # Limitar tamanho da senha
                    if event.unicode.isprintable():
                        self.password_input += event.unicode

    def join_room_by_id(self):
        """Entrar na sala usando o ID digitado"""
        if not self.room_id_input:
            self.error_message = "Digite o ID da sala"
            self.message_timer = pygame.time.get_ticks()
            return
        
        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Conectar à sala baseado no modo selecionado
        success = False
        if self.connection_mode_selection == "online":
            success = self.connect_to_online_room(self.room_id_input, self.password_input)
        else:
            success = self.connect_to_local_room(self.room_id_input, self.password_input)
        
        if success:
            self.current_view = "lobby"
            self.host_mode = False
            self.success_message = "Conectado à sala com sucesso!"
            self.message_timer = pygame.time.get_ticks()
        else:
            # Mensagem de erro será definida pelas funções de conexão
            self.message_timer = pygame.time.get_ticks()

