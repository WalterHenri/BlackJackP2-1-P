import pygame
from constants import *

class Settings:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        
        # Configurações padrão
        self.sound_enabled = True
        self.music_enabled = True
        
        # Carrega a imagem de fundo
        self.background_image = pygame.image.load("assets/capa2.png")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Carrega a fonte personalizada
        self.custom_font = pygame.font.Font("assets/font-jersey.ttf", 30)
        self.title_font = pygame.font.Font("assets/font-jersey.ttf", 40)
        
        # Dimensões e posições dos botões
        button_width = 100
        button_height = 50
        button_margin = 20
        
        # Botões para o som das cartas
        self.sound_title_pos = (SCREEN_WIDTH // 2, 200)
        
        self.sound_on_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width - button_margin,
            250,
            button_width, 
            button_height
        )
        
        self.sound_off_button = pygame.Rect(
            SCREEN_WIDTH // 2 + button_margin,
            250,
            button_width, 
            button_height
        )
        
        # Botões para música
        self.music_title_pos = (SCREEN_WIDTH // 2, 350)
        
        self.music_on_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width - button_margin,
            400,
            button_width, 
            button_height
        )
        
        self.music_off_button = pygame.Rect(
            SCREEN_WIDTH // 2 + button_margin,
            400,
            button_width, 
            button_height
        )
        
        # Botão voltar
        self.back_button = pygame.Rect(
            50,
            SCREEN_HEIGHT - 100,
            120,
            50
        )
    
    def draw(self):
        # Background com imagem
        self.screen.blit(self.background_image, (0, 0))
        
        # Título "Barulho do Baralho"
        title_text = self.title_font.render("Barulho do Baralho", True, WHITE)
        title_rect = title_text.get_rect(center=self.sound_title_pos)
        self.screen.blit(title_text, title_rect)
        
        # Botões de som (Com/Sem)
        # Botão "Com"
        button_color = GOLD if self.sound_enabled else GRAY
        pygame.draw.rect(self.screen, button_color, self.sound_on_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.sound_on_button, 4, border_radius=10)  # Contorno preto
        on_text = self.custom_font.render("Com", True, BLACK)
        on_text_rect = on_text.get_rect(center=self.sound_on_button.center)
        self.screen.blit(on_text, on_text_rect)
        
        # Botão "Sem"
        button_color = GOLD if not self.sound_enabled else GRAY
        pygame.draw.rect(self.screen, button_color, self.sound_off_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.sound_off_button, 4, border_radius=10)  # Contorno preto
        off_text = self.custom_font.render("Sem", True, BLACK)
        off_text_rect = off_text.get_rect(center=self.sound_off_button.center)
        self.screen.blit(off_text, off_text_rect)
        
        # Título "Musga"
        music_text = self.title_font.render("Musga", True, WHITE)
        music_rect = music_text.get_rect(center=self.music_title_pos)
        self.screen.blit(music_text, music_rect)
        
        # Botões de música (Com/Sem)
        # Botão "Com"
        button_color = GOLD if self.music_enabled else GRAY
        pygame.draw.rect(self.screen, button_color, self.music_on_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.music_on_button, 4, border_radius=10)  # Contorno preto
        on_text = self.custom_font.render("Com", True, BLACK)
        on_text_rect = on_text.get_rect(center=self.music_on_button.center)
        self.screen.blit(on_text, on_text_rect)
        
        # Botão "Sem"
        button_color = GOLD if not self.music_enabled else GRAY
        pygame.draw.rect(self.screen, button_color, self.music_off_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.music_off_button, 4, border_radius=10)  # Contorno preto
        off_text = self.custom_font.render("Sem", True, BLACK)
        off_text_rect = off_text.get_rect(center=self.music_off_button.center)
        self.screen.blit(off_text, off_text_rect)
        
        # Botão "Voltar"
        pygame.draw.rect(self.screen, GOLD, self.back_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.back_button, 4, border_radius=10)  # Contorno preto
        back_text = self.custom_font.render("Voltar", True, BLACK)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect) 