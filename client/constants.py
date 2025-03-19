# Cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 128, 0)
DARK_GREEN = (0, 100, 0)
LIGHT_GREEN = (144, 238, 144)
BLUE = (0, 0, 255)
LIGHT_BLUE = (173, 216, 230)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
ORANGE = (255, 165, 0)

# Tamanho da tela
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# FPS
FPS = 60

# Tempos (em milissegundos)
MESSAGE_DISPLAY_TIME = 3000  # 3 segundos
CARD_ANIMATION_TIME = 500    # 0.5 segundos
DEALER_PAUSE_TIME = 1000     # 1 segundo

# Valores das cartas
CARD_VALUES = {
    'A': 11,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    '10': 10,
    'J': 10,
    'Q': 10,
    'K': 10
}

# Configurações do jogo
INITIAL_BALANCE = 1000       # Saldo inicial
DEFAULT_BET = 50             # Aposta padrão
MIN_BET = 10                 # Aposta mínima
MAX_BET = 500                # Aposta máxima

# Configurações de rede
MATCHMAKING_HOST = "localhost"
MATCHMAKING_PORT = 5000
LOCAL_DISCOVERY_PORT = 5001 