import pygame
import random

class CardSprite:
    """
    Classe para representar uma carta do baralho com imagem sprite
    Mantém compatibilidade com a classe Card original
    """
    def __init__(self, value, suit, sprite):
        self.value = value
        self.suit = suit
        self.sprite = sprite
        
    def get_numeric_value(self):
        if self.value in ['J', 'Q', 'K']:
            return 10
        elif self.value == 'A':
            return 11  # Ás vale 11 (versão simplificada)
        else:
            return int(self.value)
    
    def __str__(self):
        return f"{self.value} of {self.suit}"

class SpriteSheet:
    """
    Classe para gerenciar o recorte da imagem do baralho em sprites individuais
    """
    def __init__(self, filename):
        # Carrega a imagem completa
        self.sheet = pygame.image.load(filename)
        
        # Dimensões de cada carta
        self.card_width = 180
        self.card_height = 276
        
        # Dicionário para armazenar todas as sprites recortadas
        # Formato: {naipe: {valor: sprite}}
        self.card_sprites = {}
        
        # Recorta todas as sprites
        self._cut_sprite_sheet()
    
    def _cut_sprite_sheet(self):
        """Recorta a imagem em sprites individuais"""
        # Ordem dos naipes na imagem
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        
        # Ordem dos valores das cartas na imagem (da esquerda para a direita)
        # Primeiro é a carta virada, depois A, K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3, 2
        values = ['back', 'A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
        
        # Inicializa dicionários para cada naipe
        for suit in suits:
            self.card_sprites[suit] = {}
        
        # Percorre as linhas (naipes)
        for suit_idx, suit in enumerate(suits):
            # Percorre as colunas (valores)
            for value_idx, value in enumerate(values):
                # Cria um retângulo para recortar a sprite
                rect = pygame.Rect(
                    value_idx * self.card_width,  # posição x
                    suit_idx * self.card_height,  # posição y
                    self.card_width,              # largura
                    self.card_height              # altura
                )
                
                # Recorta a sprite
                image = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                image.blit(self.sheet, (0, 0), rect)
                
                # Armazena a sprite no dicionário
                self.card_sprites[suit][value] = image
    
    def get_sprite(self, suit, value):
        """Retorna a sprite de uma carta específica"""
        if suit in self.card_sprites and value in self.card_sprites[suit]:
            return self.card_sprites[suit][value]
        return None
    
    def get_back_sprite(self):
        """Retorna a sprite do verso da carta"""
        return self.card_sprites['Hearts']['back']  # Usando o verso vermelho

class SpriteDeck:
    """
    Classe para representar um baralho usando as sprites
    Mantém compatibilidade com a classe Deck original
    """
    def __init__(self, sprite_sheet):
        # Inicializa o sprite_sheet se não for fornecido
        if isinstance(sprite_sheet, str):
            self.sprite_sheet = SpriteSheet(sprite_sheet)
        else:
            self.sprite_sheet = sprite_sheet
            
        # Cria o baralho com as mesmas regras da classe Deck original
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        # Cria as cartas com sprites
        self.cards = []
        for suit in suits:
            for value in values:
                sprite = self.sprite_sheet.get_sprite(suit, value)
                self.cards.append(CardSprite(value, suit, sprite))
        
        # Embaralha as cartas
        random.shuffle(self.cards)
    
    def draw(self):
        """Remove e retorna a carta do topo do baralho"""
        if len(self.cards) > 0:
            return self.cards.pop()
        return None

# Função para criar um baralho com sprites
def create_sprite_deck():
    """Cria e retorna um baralho com sprites"""
    sprite_sheet = SpriteSheet("assets/cards.png")
    return SpriteDeck(sprite_sheet)

# Exemplo de uso:
# deck = create_sprite_deck()
# card = deck.draw()
# print(card)  # Exibe o nome da carta
# screen.blit(card.sprite, (x, y))  # Renderiza a sprite na tela 