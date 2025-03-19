import pygame
import sys
from .constants import WHITE, GREEN, BLACK, RED, BLUE, YELLOW

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