# file: menu_view.py
import pygame
from pygame.locals import *

class MenuView:
    def __init__(self, client):
        self.client = client

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
        name_label = self.client.medium_font.render("Nome:", True, self.client.WHITE)
        self.client.screen.blit(name_label, (self.client.screen.get_width() // 2 - 150, 150))
        name_input_rect = pygame.Rect(self.client.screen.get_width() // 2 - 90, 150, 180, 30)
        pygame.draw.rect(self.client.screen, self.client.WHITE, name_input_rect, border_radius=5)
        border_color = (0, 120, 255) if self.client.name_input_active else (0, 80, 0)
        pygame.draw.rect(self.client.screen, border_color, name_input_rect, 2, border_radius=5)
        name_text = self.client.small_font.render(self.client.player_name or "Player", True, self.client.BLACK)
        self.client.screen.blit(name_text, (name_input_rect.x + 10, name_input_rect.y + 8))

    def render_balance(self):
        """Renderizar o saldo do jogador"""
        balance_label = self.client.medium_font.render(f"Saldo: {self.client.player_balance} moedas", True, self.client.WHITE)
        self.client.screen.blit(balance_label, (self.client.screen.get_width() // 2 - 150, 220))

    def render_menu_buttons(self):
        """Renderizar os botões do menu"""
        button_width, button_height, button_spacing = 250, 50, 20
        start_y = 280
        buttons = [
            ("Jogar Sozinho", self.client.handle_solo_click),
            ("Jogar Online", self.client.handle_online_click),
            ("Jogar na Rede Local", self.client.handle_local_network_click),
            ("Sair", self.client.exit_game),
        ]
        for i, (text, action) in enumerate(buttons):
            rect = pygame.Rect((self.client.screen.get_width() - button_width) // 2, start_y + i * (button_height + button_spacing), button_width, button_height)
            pygame.draw.rect(self.client.screen, (0, 100, 0), rect, border_radius=10)
            label = self.client.medium_font.render(text, True, self.client.WHITE)
            self.client.screen.blit(label, label.get_rect(center=rect.center))

    def render_help_button(self):
        """Renderizar o botão de ajuda"""
        help_button = pygame.Rect(self.client.screen.get_width() - 50, 20, 40, 40)
        pygame.draw.rect(self.client.screen, (0, 80, 160), help_button, border_radius=20)
        help_text = self.client.medium_font.render("?", True, self.client.WHITE)
        self.client.screen.blit(help_text, help_text.get_rect(center=help_button.center))

    def render_tutorial_popup(self):
        """Renderizar o pop-up de tutorial"""
        popup_rect = pygame.Rect(self.client.screen.get_width() // 2 - 250, self.client.screen.get_height() // 2 - 200, 500, 400)
        pygame.draw.rect(self.client.screen, (0, 80, 0), popup_rect, border_radius=10)
        pygame.draw.rect(self.client.screen, self.client.WHITE, popup_rect, 3, border_radius=10)
        title = self.client.medium_font.render("Como Jogar Blackjack", True, self.client.WHITE)
        self.client.screen.blit(title, title.get_rect(midtop=(popup_rect.centerx, popup_rect.y + 20)))