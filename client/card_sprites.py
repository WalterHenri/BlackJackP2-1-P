import pygame
import os

class CardSprites:
    def __init__(self):
        # Carregar a sprite sheet
        sprite_path = os.path.join("client//ui", "cards.png")
        self.sprite_sheet = pygame.image.load(sprite_path)

        # Dimensões de cada carta na sprite sheet
        self.CARD_WIDTH = 79
        self.CARD_HEIGHT = 109
        self.SPACING_X = 1  # Espaço entre cartas na horizontal
        self.SPACING_Y = 1  # Espaço entre cartas na vertical

        # Posição inicial das cartas na sprite sheet
        self.START_X = 0
        self.START_Y = 0

        # Dicionário para mapear valores e naipes para índices
        self.card_map = {
            # Paus (Clubs) - Primeira linha
            ("CLUBS", "ACE"): (0, 0),
            ("CLUBS", "TWO"): (1, 0),
            ("CLUBS", "THREE"): (2, 0),
            ("CLUBS", "FOUR"): (3, 0),
            ("CLUBS", "FIVE"): (4, 0),
            ("CLUBS", "SIX"): (5, 0),
            ("CLUBS", "SEVEN"): (6, 0),
            ("CLUBS", "EIGHT"): (7, 0),
            ("CLUBS", "NINE"): (8, 0),
            ("CLUBS", "TEN"): (9, 0),
            ("CLUBS", "JACK"): (10, 0),
            ("CLUBS", "QUEEN"): (11, 0),
            ("CLUBS", "KING"): (12, 0),

            # Ouros (Diamonds) - Segunda linha
            ("DIAMONDS", "ACE"): (0, 1),
            ("DIAMONDS", "TWO"): (1, 1),
            ("DIAMONDS", "THREE"): (2, 1),
            ("DIAMONDS", "FOUR"): (3, 1),
            ("DIAMONDS", "FIVE"): (4, 1),
            ("DIAMONDS", "SIX"): (5, 1),
            ("DIAMONDS", "SEVEN"): (6, 1),
            ("DIAMONDS", "EIGHT"): (7, 1),
            ("DIAMONDS", "NINE"): (8, 1),
            ("DIAMONDS", "TEN"): (9, 1),
            ("DIAMONDS", "JACK"): (10, 1),
            ("DIAMONDS", "QUEEN"): (11, 1),
            ("DIAMONDS", "KING"): (12, 1),

            # Copas (Hearts) - Terceira linha
            ("HEARTS", "ACE"): (0, 2),
            ("HEARTS", "TWO"): (1, 2),
            ("HEARTS", "THREE"): (2, 2),
            ("HEARTS", "FOUR"): (3, 2),
            ("HEARTS", "FIVE"): (4, 2),
            ("HEARTS", "SIX"): (5, 2),
            ("HEARTS", "SEVEN"): (6, 2),
            ("HEARTS", "EIGHT"): (7, 2),
            ("HEARTS", "NINE"): (8, 2),
            ("HEARTS", "TEN"): (9, 2),
            ("HEARTS", "JACK"): (10, 2),
            ("HEARTS", "QUEEN"): (11, 2),
            ("HEARTS", "KING"): (12, 2),

            # Espadas (Spades) - Quarta linha
            ("SPADES", "ACE"): (0, 3),
            ("SPADES", "TWO"): (1, 3),
            ("SPADES", "THREE"): (2, 3),
            ("SPADES", "FOUR"): (3, 3),
            ("SPADES", "FIVE"): (4, 3),
            ("SPADES", "SIX"): (5, 3),
            ("SPADES", "SEVEN"): (6, 3),
            ("SPADES", "EIGHT"): (7, 3),
            ("SPADES", "NINE"): (8, 3),
            ("SPADES", "TEN"): (9, 3),
            ("SPADES", "JACK"): (10, 3),
            ("SPADES", "QUEEN"): (11, 3),
            ("SPADES", "KING"): (12, 3),
        }

        # Carregar o verso da carta (primeira coluna, quinta linha)
        self.card_back = self.get_card_sprite(1, 4)

        # Cache para as sprites já carregadas
        self.sprite_cache = {}

    def get_card_sprite(self, x, y):
        """Obter uma sprite específica da sprite sheet"""
        # Criar uma nova superfície com o tamanho da carta
        sprite = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT))
        
        # Definir a cor de fundo como transparente
        sprite.set_colorkey((0, 0, 0))
        
        # Copiar a região específica da sprite sheet
        sprite.blit(self.sprite_sheet, (0, 0), (
            self.START_X + x * (self.CARD_WIDTH + self.SPACING_X),
            self.START_Y + y * (self.CARD_HEIGHT + self.SPACING_Y),
            self.CARD_WIDTH,
            self.CARD_HEIGHT
        ))
        
        return sprite

    def get_card(self, suit, value, scale=1.0):
        """Obter a sprite de uma carta específica"""
        # Verificar se a carta já está no cache
        cache_key = (suit, value, scale)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        # Obter os índices da carta no sprite sheet
        if (suit, value) not in self.card_map:
            return self.get_card_back(scale)  # Retornar verso da carta se não encontrada

        x, y = self.card_map[(suit, value)]
        sprite = self.get_card_sprite(x, y)

        # Redimensionar se necessário
        if scale != 1.0:
            new_width = int(self.CARD_WIDTH * scale)
            new_height = int(self.CARD_HEIGHT * scale)
            sprite = pygame.transform.scale(sprite, (new_width, new_height))

        # Armazenar no cache
        self.sprite_cache[cache_key] = sprite
        return sprite

    def get_card_back(self, scale=1.0):
        """Obter a sprite do verso da carta"""
        cache_key = ("BACK", "BACK", scale)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        sprite = self.card_back

        # Redimensionar se necessário
        if scale != 1.0:
            new_width = int(self.CARD_WIDTH * scale)
            new_height = int(self.CARD_HEIGHT * scale)
            sprite = pygame.transform.scale(sprite, (new_width, new_height))

        # Armazenar no cache
        self.sprite_cache[cache_key] = sprite
        return sprite 