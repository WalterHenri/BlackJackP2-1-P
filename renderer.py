import pygame
import socket
from constants import *

class GameRenderer:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        
        # Button dimensions for gameplay
        self.hit_button = pygame.Rect(SCREEN_WIDTH // 4 - 50, SCREEN_HEIGHT - 100, 100, 40)
        self.stand_button = pygame.Rect(3 * SCREEN_WIDTH // 4 - 50, SCREEN_HEIGHT - 100, 100, 40)
    
    def draw_card(self, card, position):
        rect = pygame.Rect(position[0], position[1], CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(self.screen, WHITE, rect)
        pygame.draw.rect(self.screen, BLACK, rect, 2)
        
        color = RED if card.suit in ['Hearts', 'Diamonds'] else BLACK
        card_text = self.font.render(f"{card.value}", True, color)
        suit_text = self.font.render(card.suit[0], True, color)
        
        self.screen.blit(card_text, (position[0] + 10, position[1] + 10))
        self.screen.blit(suit_text, (position[0] + 10, position[1] + 40))
    
    def draw_hand(self, player, is_local):
        y_pos = SCREEN_HEIGHT - 350 if is_local else 50
        label = "Your hand:" if is_local else "Opponent's hand:"
        score_text = f"Score: {player.score}"
        status_text = f"Status: {player.status}"
        
        label_surface = self.font.render(label, True, WHITE)
        score_surface = self.font.render(score_text, True, WHITE)
        status_surface = self.font.render(status_text, True, WHITE)
        
        self.screen.blit(label_surface, (50, y_pos - 40))
        self.screen.blit(score_surface, (50, y_pos - 80))
        self.screen.blit(status_surface, (250, y_pos - 80))
        
        for i, card in enumerate(player.hand):
            self.draw_card(card, (50 + i * 30, y_pos))
    
    def draw_buttons(self):
        pygame.draw.rect(self.screen, GREEN, self.hit_button)
        pygame.draw.rect(self.screen, RED, self.stand_button)
        
        hit_text = self.font.render("Hit", True, WHITE)
        stand_text = self.font.render("Stand", True, WHITE)
        
        self.screen.blit(hit_text, (self.hit_button.x + 35, self.hit_button.y + 10))
        self.screen.blit(stand_text, (self.stand_button.x + 20, self.stand_button.y + 10))
    
    def draw_waiting_screen(self, menu):
        self.screen.fill(GREEN)
        waiting_text = self.font.render("Waiting for opponent to connect...", True, WHITE)
        self.screen.blit(waiting_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2))
        
        ip_info = socket.gethostbyname(socket.gethostname())
        ip_text = self.small_font.render(f"Your IP address: {ip_info}", True, WHITE)
        port_text = self.small_font.render(f"Port: 5000", True, WHITE)
        
        self.screen.blit(ip_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(port_text, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 80))
        
        # Back button
        pygame.draw.rect(self.screen, RED, menu.back_button, border_radius=5)
        back_text = self.font.render("Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=menu.back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    def draw_game_over(self, winner_text):
        game_over_text = self.font.render("Game Over!", True, WHITE)
        result_text = self.font.render(winner_text, True, WHITE)
        restart_text = self.small_font.render("Press R to restart or Q to quit", True, WHITE)
        
        self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(result_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50))
    
    def draw_game(self, local_player, remote_player):
        self.screen.fill(GREEN)
        self.draw_hand(local_player, True)
        self.draw_hand(remote_player, False)
        self.draw_buttons() 