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
        self.music_volume = 50  # Volume da música (0-100)
        
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
        
        # Configurações para slider de volume da música
        self.music_title_pos = (SCREEN_WIDTH // 2, 350)
        
        # Slider da música
        slider_width = 300
        slider_height = 20
        self.slider_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - slider_width // 2,
            400,
            slider_width,
            slider_height
        )
        
        # Botão do slider (para arrastar)
        self.slider_button_width = 20
        self.slider_button_rect = pygame.Rect(
            self.slider_rect.x + int(self.slider_rect.width * (self.music_volume / 100)) - self.slider_button_width // 2,
            self.slider_rect.y - 10,
            self.slider_button_width,
            self.slider_rect.height + 20
        )
        
        # Variável para controlar se o slider está sendo arrastado
        self.dragging_slider = False
        
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
        music_text = self.title_font.render("Volume da Musga", True, WHITE)
        music_rect = music_text.get_rect(center=self.music_title_pos)
        self.screen.blit(music_text, music_rect)
        
        # Desenhar o slider de volume
        # Fundo do slider
        pygame.draw.rect(self.screen, GRAY, self.slider_rect, border_radius=10)
        
        # Parte preenchida do slider
        filled_width = int(self.slider_rect.width * (self.music_volume / 100))
        filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, filled_width, self.slider_rect.height)
        pygame.draw.rect(self.screen, GOLD, filled_rect, border_radius=10)
        
        # Contorno do slider
        pygame.draw.rect(self.screen, BLACK, self.slider_rect, 2, border_radius=10)
        
        # Botão do slider
        pygame.draw.rect(self.screen, WHITE, self.slider_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, BLACK, self.slider_button_rect, 2, border_radius=10)
        
        # Exibir valor do volume
        volume_text = self.custom_font.render(f"{self.music_volume}%", True, WHITE)
        volume_rect = volume_text.get_rect(center=(self.slider_rect.centerx, self.slider_rect.y - 30))
        self.screen.blit(volume_text, volume_rect)
        
        # Status da música (Ligada/Desligada)
        status_text = self.custom_font.render("Ligada" if self.music_volume > 0 else "Desligada", True, 
                                           GOLD if self.music_volume > 0 else RED)
        status_rect = status_text.get_rect(center=(self.slider_rect.centerx, self.slider_rect.y + 50))
        self.screen.blit(status_text, status_rect)
        
        # Botão "Voltar"
        pygame.draw.rect(self.screen, GOLD, self.back_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.back_button, 4, border_radius=10)  # Contorno preto
        back_text = self.custom_font.render("Voltar", True, BLACK)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    def update_slider_position(self, x_pos):
        """Atualiza a posição do slider baseado na posição do mouse"""
        # Calcula a posição relativa dentro do slider (0 a width)
        rel_x = max(0, min(x_pos - self.slider_rect.x, self.slider_rect.width))
        
        # Converte para valor de volume (0-100)
        self.music_volume = int((rel_x / self.slider_rect.width) * 100)
        
        # Atualiza a posição do botão do slider
        self.slider_button_rect.x = self.slider_rect.x + rel_x - self.slider_button_width // 2
        
        # Atualiza o estado de habilitação da música
        self.music_enabled = self.music_volume > 0 