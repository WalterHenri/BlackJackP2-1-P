import pygame
import sys
import os
from pygame.locals import *

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.game_client import BlackjackClient

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
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

def show_splash_screen():
    """Mostrar tela de splash com animação"""
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Blackjack 21 P2P - Carregando...")
    clock = pygame.time.Clock()

    # Fontes
    title_font = pygame.font.SysFont("Arial", 72)
    subtitle_font = pygame.font.SysFont("Arial", 36)

    # Textos
    title = title_font.render("Blackjack 21", True, WHITE)
    subtitle = subtitle_font.render("P2P Version", True, WHITE)
    loading = subtitle_font.render("Carregando...", True, WHITE)

    # Posições
    title_pos = (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 3)
    subtitle_pos = (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, SCREEN_HEIGHT // 2)
    loading_pos = (SCREEN_WIDTH // 2 - loading.get_width() // 2, 2 * SCREEN_HEIGHT // 3)

    # Animação de loading
    dots = 0
    start_time = pygame.time.get_ticks()

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        elapsed_time = (current_time - start_time) // 1000  # Segundos

        # Atualizar dots a cada 500ms
        if elapsed_time * 2 > dots:
            dots = elapsed_time * 2
            if dots > 3:
                dots = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Limpar tela
        screen.fill(GREEN)

        # Desenhar textos
        screen.blit(title, title_pos)
        screen.blit(subtitle, subtitle_pos)
        
        # Atualizar texto de loading com dots
        loading_text = subtitle_font.render("Carregando" + "." * dots, True, WHITE)
        screen.blit(loading_text, loading_pos)

        pygame.display.flip()
        clock.tick(60)

        # Sair após 3 segundos
        if elapsed_time >= 3:
            running = False

def main():
    """Função principal"""
    try:
        # Mostrar tela de splash
        show_splash_screen()

        # Iniciar o jogo
        client = BlackjackClient()
        client.start()

    except Exception as e:
        print(f"Erro ao iniciar o jogo: {e}")
        pygame.quit()
        sys.exit(1)

if __name__ == '__main__':
    main()


