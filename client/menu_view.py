# file: menu_view.py
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
from client.constants import *

class MenuView:
    def __init__(self, client):
        self.client = client
        # Adicionado para compatibilidade
        self.buttons = [
            ("Jogar Sozinho", self.handle_solo_click),
            ("Jogar Online", self.handle_online_click),
            ("Jogar na Rede Local", self.handle_local_network_click),
            ("Sair", self.handle_exit),
        ]

    def render(self):
        """Renderizar a tela do menu"""
        self.client.screen.fill((0, 100, 0))  # Fundo verde escuro
        self.render_title()
        self.render_name_input()
        self.render_balance()
        self.render_menu_buttons()
        self.render_help_button()
        if self.client.show_tutorial:
            self.render_tutorial_popup()

    def render_title(self):
        """Renderizar o título do menu"""
        title = self.client.title_font.render("Blackjack 21 P2P", True, (240, 240, 240))
        title_shadow = self.client.title_font.render("Blackjack 21 P2P", True, (0, 40, 0))
        title_rect = title.get_rect(center=(self.client.screen.get_width() // 2, 60))
        shadow_rect = title_shadow.get_rect(center=(self.client.screen.get_width() // 2 + 2, 62))
        self.client.screen.blit(title_shadow, shadow_rect)
        self.client.screen.blit(title, title_rect)

    def render_name_input(self):
        """Renderizar o campo de entrada de nome"""
        name_label = self.client.medium_font.render("Nome:", True, WHITE)
        self.client.screen.blit(name_label, (self.client.screen.get_width() // 2 - 150, 150))
        name_input_rect = pygame.Rect(self.client.screen.get_width() // 2 - 90, 150, 180, 30)
        pygame.draw.rect(self.client.screen, WHITE, name_input_rect, border_radius=5)
        border_color = (0, 120, 255) if self.client.name_input_active else (0, 80, 0)
        pygame.draw.rect(self.client.screen, border_color, name_input_rect, 2, border_radius=5)
        name_text = self.client.small_font.render(self.client.player_name or "Player", True, BLACK)
        self.client.screen.blit(name_text, (name_input_rect.x + 10, name_input_rect.y + 8))

    def render_balance(self):
        """Renderizar o saldo do jogador"""
        balance_label = self.client.medium_font.render(f"Saldo: {self.client.player_balance} moedas", True, WHITE)
        self.client.screen.blit(balance_label, (self.client.screen.get_width() // 2 - 150, 220))

    def render_menu_buttons(self):
        """Renderizar os botões do menu"""
        button_width, button_height, button_spacing = 250, 50, 20
        start_y = 280
        
        for i, (text, action) in enumerate(self.buttons):
            # Criar retângulo do botão
            rect = pygame.Rect((self.client.screen.get_width() - button_width) // 2, 
                               start_y + i * (button_height + button_spacing), 
                               button_width, button_height)
            
            # Verificar se o mouse está sobre o botão
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            
            # Definir cores do botão
            button_color = (0, 120, 0) if is_hover else (0, 80, 0)  # Verde mais escuro/claro
            border_color = (0, 200, 0) if is_hover else (0, 150, 0)  # Verde mais claro
            text_color = (255, 255, 255)  # Branco
            
            # Desenhar sombra do botão (deslocada levemente)
            shadow_rect = rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(self.client.screen, (0, 60, 0), shadow_rect, border_radius=10)
            
            # Desenhar botão principal
            pygame.draw.rect(self.client.screen, button_color, rect, border_radius=10)
            pygame.draw.rect(self.client.screen, border_color, rect, 2, border_radius=10)
            
            # Desenhar texto
            label = self.client.medium_font.render(text, True, text_color)
            self.client.screen.blit(label, label.get_rect(center=rect.center))
            
            # Efeito de brilho quando hover
            if is_hover:
                # Desenhar um pequeno indicador de seleção
                pygame.draw.circle(self.client.screen, (255, 255, 150), 
                                  (rect.left - 10, rect.centery), 5)
                pygame.draw.circle(self.client.screen, (255, 255, 150), 
                                  (rect.right + 10, rect.centery), 5)

    def render_help_button(self):
        """Renderizar o botão de ajuda"""
        help_button = pygame.Rect(self.client.screen.get_width() - 50, 20, 40, 40)
        pygame.draw.rect(self.client.screen, (0, 80, 160), help_button, border_radius=20)
        help_text = self.client.medium_font.render("?", True, WHITE)
        self.client.screen.blit(help_text, help_text.get_rect(center=help_button.center))

    def render_tutorial_popup(self):
        """Renderizar o pop-up de tutorial"""
        popup_rect = pygame.Rect(self.client.screen.get_width() // 2 - 250, self.client.screen.get_height() // 2 - 200, 500, 400)
        pygame.draw.rect(self.client.screen, (0, 80, 0), popup_rect, border_radius=10)
        pygame.draw.rect(self.client.screen, WHITE, popup_rect, 3, border_radius=10)
        title = self.client.medium_font.render("Como Jogar Blackjack", True, WHITE)
        self.client.screen.blit(title, title.get_rect(midtop=(popup_rect.centerx, popup_rect.y + 20)))
        
    # Métodos de manipulação de eventos adicionados para melhorar a interação
    def handle_solo_click(self):
        self.client.handle_solo_click()
        
    def handle_online_click(self):
        if hasattr(self.client, 'online_client'):
            self.client.online_client.handle_online_click()
            
    def handle_local_network_click(self):
        if hasattr(self.client, 'online_client'):
            self.client.online_client.handle_local_network_click()
            
    def handle_exit(self):
        self.client.exit_game()
        
    def handle_event(self, event):
        """Manipular eventos da tela de menu"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões do menu principal
            button_width, button_height, button_spacing = 250, 50, 20
            start_y = 280
            
            for i, (text, action) in enumerate(self.buttons):
                rect = pygame.Rect((self.client.screen.get_width() - button_width) // 2, 
                                   start_y + i * (button_height + button_spacing), 
                                   button_width, button_height)
                if rect.collidepoint(mouse_pos) and not self.client.name_input_active:
                    action()
                    return True
                    
            # Campo de entrada de nome
            name_input_rect = pygame.Rect(self.client.screen.get_width() // 2 - 90, 150, 180, 30)
            if name_input_rect.collidepoint(mouse_pos):
                self.client.name_input_active = True
                if self.client.player_name == "Player" or self.client.player_name == "":
                    self.client.player_name = ""
                return True
            else:
                if self.client.name_input_active:
                    self.client.name_input_active = False
                    if self.client.player_name == "":
                        self.client.player_name = "Player"
                    old_balance = self.client.player_balance
                    self.client.player_balance = get_player_balance(self.client.player_name)
                    print(f"Nome atualizado para: {self.client.player_name}, saldo atualizado de {old_balance} para {self.client.player_balance}")
            
            # Botão de ajuda
            help_button = pygame.Rect(self.client.screen.get_width() - 50, 20, 40, 40)
            if help_button.collidepoint(mouse_pos):
                self.client.show_tutorial = not self.client.show_tutorial
                return True
                
            # Tutorial
            if self.client.show_tutorial:
                tutorial_rect = pygame.Rect(self.client.screen.get_width() // 2 - 250, 
                                           self.client.screen.get_height() // 2 - 200, 500, 400)
                if not tutorial_rect.collidepoint(mouse_pos):
                    self.client.show_tutorial = False
                    return True
                    
        # Entrada de texto
        elif event.type == pygame.KEYDOWN and self.client.name_input_active:
            if event.key == pygame.K_RETURN:
                self.client.name_input_active = False
                if self.client.player_name == "":
                    self.client.player_name = "Player"
                old_balance = self.client.player_balance
                self.client.player_balance = get_player_balance(self.client.player_name)
                print(f"Nome confirmado: {self.client.player_name}, saldo atualizado de {old_balance} para {self.client.player_balance}")
            elif event.key == pygame.K_BACKSPACE:
                self.client.player_name = self.client.player_name[:-1]
            else:
                if len(self.client.player_name) < 20:
                    self.client.player_name += event.unicode
            return True
            
        return False


class OnlineGameClient:
    """Classe para gerenciar jogos online e em rede local"""
    def __init__(self, main_client):
        self.main_client = main_client
        self.p2p_manager = None
        self.matchmaking_service = MatchmakingService()
        self.room_list = []
        self.room_id = ""
        self.room_id_input = ""
        self.room_id_input_active = False
        self.room_name_input = ""
        self.room_name_input_active = False
        self.password_input = ""
        self.password_input_active = False
        self.connection_mode = "online"  # "online" ou "local"
        self.connection_mode_selection = "online"
        self.room_browser_scroll = 0
        self.selected_room_index = -1
        self.error_message = ""
        self.success_message = ""
        self.message_timer = 0
        
    def handle_online_click(self):
        """Manipular clique no botão Jogar Online"""
        # Certifique-se de que o nome não está no modo de edição
        if self.main_client.name_input_active:
            self.main_client.name_input_active = False
            if not self.main_client.player_name:
                self.main_client.player_name = "Player"
            self.main_client.player_balance = get_player_balance(self.main_client.player_name)
        self.connection_mode = "online"
        self.main_client.current_view = "room_browser"
        self.load_room_list(mode="online")

    def handle_local_network_click(self):
        """Manipular clique no botão Jogar em Rede Local"""
        # Certifique-se de que o nome não está no modo de edição
        if self.main_client.name_input_active:
            self.main_client.name_input_active = False
            if not self.main_client.player_name:
                self.main_client.player_name = "Player"
            self.main_client.player_balance = get_player_balance(self.main_client.player_name)
        self.connection_mode = "local"
        self.main_client.current_view = "room_browser"
        self.load_room_list(mode="local")
        
    def load_room_list(self, mode="online"):
        """Carregar lista de salas disponíveis"""
        if mode == "online":
            # Carregar salas online do serviço de matchmaking
            self.room_list = self.matchmaking_service.get_rooms()
        else:
            # Descobrir salas na rede local
            self.room_list = self.matchmaking_service.discover_local_games()
            
    def handle_room_browser_event(self, event):
        """Manipular eventos na tela de navegação de salas"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Botões de ação na parte inferior
            button_width = 180
            button_height = 50
            button_y = self.main_client.screen.get_height() - 100
            
            # Botão Criar Sala
            create_button = pygame.Rect(50, button_y, button_width, button_height)
            if create_button.collidepoint(event.pos):
                self.handle_create_room_click()
                return
                
            # Botão Atualizar
            refresh_button = pygame.Rect(self.main_client.screen.get_width() // 2 - button_width // 2, button_y, button_width, button_height)
            if refresh_button.collidepoint(event.pos):
                self.load_room_list(self.connection_mode)
                return
                
            # Botão Voltar
            back_button = pygame.Rect(self.main_client.screen.get_width() - 50 - button_width, button_y, button_width, button_height)
            if back_button.collidepoint(event.pos):
                self.main_client.current_view = "menu"
                return
                
            # Lista de salas - verificar se clicou em uma sala
            room_list_rect = pygame.Rect(30, 120, self.main_client.screen.get_width() - 60, self.main_client.screen.get_height() - 250)
            if room_list_rect.collidepoint(event.pos):
                # Calcular em qual sala clicou com base na posição do mouse
                room_height = 60
                clicked_index = (event.pos[1] - 120 + self.room_browser_scroll) // room_height
                
                if 0 <= clicked_index < len(self.room_list):
                    self.selected_room_index = clicked_index
                    
                    # Verificar se clicou duas vezes (duplo clique) para entrar na sala
                    curr_time = pygame.time.get_ticks()
                    if hasattr(self, 'last_click_time') and curr_time - self.last_click_time < 500:
                        # Duplo clique, tentar entrar na sala
                        self.join_selected_room()
                    self.last_click_time = curr_time
                    
            # Botão Entrar (na parte inferior da lista de salas)
            join_button = pygame.Rect(self.main_client.screen.get_width() // 2 - 80, room_list_rect.bottom + 20, 160, 40)
            if join_button.collidepoint(event.pos) and self.selected_room_index >= 0:
                self.join_selected_room()
                return
            
            # Botões de alternar modo (online/local)
            tab_width = self.main_client.screen.get_width() // 2
            online_tab = pygame.Rect(0, 80, tab_width, 40)
            local_tab = pygame.Rect(tab_width, 80, tab_width, 40)
            
            if online_tab.collidepoint(event.pos):
                self.connection_mode = "online"
                self.load_room_list("online")
                return
                
            if local_tab.collidepoint(event.pos):
                self.connection_mode = "local"
                self.load_room_list("local")
                return
                
        # Rolar a lista de salas
        elif event.type == pygame.MOUSEWHEEL:
            self.room_browser_scroll = max(0, self.room_browser_scroll - event.y * 30)
            
            # Limitar a rolagem para não passar do final da lista
            max_scroll = max(0, len(self.room_list) * 60 - (self.main_client.screen.get_height() - 250))
            self.room_browser_scroll = min(self.room_browser_scroll, max_scroll)

    def handle_create_room_click(self):
        """Manipular clique no botão Criar Sala"""
        # Certifique-se de que o nome não está no modo de edição
        if self.main_client.name_input_active:
            self.main_client.name_input_active = False
            if not self.main_client.player_name:
                self.main_client.player_name = "Player"
            self.main_client.player_balance = get_player_balance(self.main_client.player_name)
        self.main_client.current_view = "create_room"
        self.password_input = ""
        self.password_input_active = True
        self.room_name_input = f"Sala de {self.main_client.player_name}"
        self.room_name_input_active = False
        self.room_id = self.generate_room_id()
        self.connection_mode_selection = "online"  # Padrão: online

    def generate_room_id(self):
        """Gerar um ID de sala aleatório de 4 dígitos"""
        import random
        return str(random.randint(1000, 9999))
        
    def join_selected_room(self):
        """Entrar na sala selecionada"""
        if self.selected_room_index < 0 or self.selected_room_index >= len(self.room_list):
            return
        
        selected_room = self.room_list[self.selected_room_index]
        room_id = selected_room.get("room_id")
        has_password = selected_room.get("has_password", False)
        
        if has_password:
            # Se a sala tem senha, ir para a tela de entrada
            self.main_client.current_view = "join_room"
            self.room_id_input = room_id
            self.room_id_input_active = False
            self.password_input = ""
            self.password_input_active = True
        else:
            # Se não tem senha, entrar diretamente
            # Criar o jogador
            self.main_client.player = Player(self.main_client.player_name, self.main_client.player_balance, str(uuid.uuid4()))
            
            success = False
            if self.connection_mode == "online":
                success = self.connect_to_online_room(room_id, "")
            else:
                success = self.connect_to_local_room(room_id, "")
            
            if success:
                self.main_client.current_view = "lobby"
                self.main_client.host_mode = False
                self.success_message = "Conectado à sala com sucesso!"
                self.message_timer = pygame.time.get_ticks()
                
    def handle_create_room_event(self, event):
        """Manipular eventos na tela de criação de sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            form_x = self.main_client.screen.get_width() // 2 - 250
            form_y = 150
            
            # Campo Nome da Sala
            name_box = pygame.Rect(form_x + 30, form_y + 70, 440, 40)
            if name_box.collidepoint(mouse_pos):
                self.room_name_input_active = True
                self.password_input_active = False
            
            # Campo Senha
            password_box = pygame.Rect(form_x + 30, form_y + 170, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_name_input_active = False
            
            # Botões de modo de conexão
            y_offset = form_y + 250
            online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
            local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)
            
            if online_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.connection_mode_selection = "local"
            
            # Botão Criar
            button_width = 200
            button_height = 50
            button_y = 500
            create_button = pygame.Rect(self.main_client.screen.get_width() // 2 - button_width - 10, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.create_room()
                return
            
            # Botão Cancelar
            cancel_button = pygame.Rect(self.main_client.screen.get_width() // 2 + 10, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.main_client.current_view = "menu"
                return
                
        # Entrada de teclado para os campos ativos
        elif event.type == pygame.KEYDOWN:
            if self.room_name_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_name_input = self.room_name_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_name_input_active = False
                elif len(self.room_name_input) < 30:
                    if event.unicode.isprintable():
                        self.room_name_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:
                    if event.unicode.isprintable():
                        self.password_input += event.unicode