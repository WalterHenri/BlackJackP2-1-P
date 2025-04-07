import pygame
import os

class CardSprites:
    def __init__(self):
        # Definir cores para os naipes
        self.CLUB_COLOR = (0, 0, 0)       # Preto
        self.DIAMOND_COLOR = (255, 0, 0)  # Vermelho
        self.HEART_COLOR = (255, 0, 0)    # Vermelho
        self.SPADE_COLOR = (0, 0, 0)      # Preto
        
        # Dimensões das cartas
        self.CARD_WIDTH = 70
        self.CARD_HEIGHT = 100
        
        # Cache para as sprites já renderizadas
        self.sprite_cache = {}
        self.initialized = True
        print("CardSprites inicializado no modo alternativo")

    def get_card(self, suit, value, scale=1.0):
        """Criar uma carta usando formas básicas"""
        # Verificar se a carta já está no cache
        cache_key = (suit, value, scale)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]
            
        # Dimensões da carta
        width = int(self.CARD_WIDTH * scale)
        height = int(self.CARD_HEIGHT * scale)
        
        # Criar uma superfície para a carta
        card = pygame.Surface((width, height))
        card.fill((255, 255, 255))  # Fundo branco
        
        # Desenhar borda
        pygame.draw.rect(card, (0, 0, 0), (0, 0, width, height), 2)
        
        # Selecionar cor do naipe
        if suit == "HEARTS" or suit == "DIAMONDS":
            color = (255, 0, 0)  # Vermelho
        else:
            color = (0, 0, 0)    # Preto
            
        # Desenhar o valor da carta
        font_size = int(24 * scale)
        try:
            font = pygame.font.SysFont("Arial", font_size)
        except:
            font = pygame.font.Font(None, font_size)
            
        # Texto para o valor (transformar em formato mais legível)
        display_value = value
        if value == "ACE":
            display_value = "A"
        elif value == "KING":
            display_value = "K"
        elif value == "QUEEN":
            display_value = "Q"
        elif value == "JACK":
            display_value = "J"
        elif value == "TEN":
            display_value = "10"
        elif value == "NINE":
            display_value = "9"
        elif value == "EIGHT":
            display_value = "8"
        elif value == "SEVEN":
            display_value = "7"
        elif value == "SIX":
            display_value = "6"
        elif value == "FIVE":
            display_value = "5"
        elif value == "FOUR":
            display_value = "4"
        elif value == "THREE":
            display_value = "3"
        elif value == "TWO":
            display_value = "2"
            
        # Renderizar o valor no canto superior esquerdo
        value_text = font.render(display_value, True, color)
        card.blit(value_text, (5, 5))
        
        # Desenhar o símbolo do naipe
        suit_text = ""
        if suit == "HEARTS":
            suit_text = "♥"
        elif suit == "DIAMONDS":
            suit_text = "♦"
        elif suit == "CLUBS":
            suit_text = "♣"
        elif suit == "SPADES":
            suit_text = "♠"
            
        suit_font_size = int(36 * scale)
        try:
            suit_font = pygame.font.SysFont("Arial", suit_font_size)
        except:
            suit_font = pygame.font.Font(None, suit_font_size)
            
        suit_text_rendered = suit_font.render(suit_text, True, color)
        card.blit(suit_text_rendered, (width//2 - suit_text_rendered.get_width()//2, 
                                      height//2 - suit_text_rendered.get_height()//2))
        
        # Renderizar o valor no canto inferior direito (invertido)
        card.blit(pygame.transform.rotate(value_text, 180), 
                 (width - value_text.get_width() - 5, height - value_text.get_height() - 5))
        
        # Armazenar no cache
        self.sprite_cache[cache_key] = card
        return card

    def get_card_back(self, scale=1.0):
        """Criar um verso de carta simples"""
        cache_key = ("BACK", "BACK", scale)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]
            
        # Dimensões da carta
        width = int(self.CARD_WIDTH * scale)
        height = int(self.CARD_HEIGHT * scale)
        
        # Criar uma superfície para o verso da carta
        card_back = pygame.Surface((width, height))
        card_back.fill((50, 50, 200))  # Azul escuro
        
        # Desenhar borda
        pygame.draw.rect(card_back, (0, 0, 0), (0, 0, width, height), 2)
        
        # Desenhar padrão de grade
        for i in range(0, width, 10):
            for j in range(0, height, 10):
                pygame.draw.rect(card_back, (70, 70, 220), (i, j, 5, 5))
        
        # Armazenar no cache
        self.sprite_cache[cache_key] = card_back
        return card_back

    def draw_card(self, surface, suit, value, x, y, scale=1.0):
        """Desenhar uma carta diretamente em uma superfície"""
        try:
            card_sprite = self.get_card(suit, value, scale)
            surface.blit(card_sprite, (x, y))
        except Exception as e:
            print(f"Erro ao desenhar carta {suit} {value}: {e}")
            # Desenhar uma carta simples como fallback
            width = int(self.CARD_WIDTH * scale)
            height = int(self.CARD_HEIGHT * scale)
            pygame.draw.rect(surface, (255, 255, 255), (x, y, width, height))
            pygame.draw.rect(surface, (0, 0, 0), (x, y, width, height), 2)
            
            # Desenhar texto simples
            try:
                font = pygame.font.SysFont("Arial", 14)
            except:
                font = pygame.font.Font(None, 14)
                
            value_text = font.render(str(value), True, (0, 0, 0))
            surface.blit(value_text, (x + width//2 - value_text.get_width()//2, 
                                     y + height//2 - value_text.get_height()//2)) 