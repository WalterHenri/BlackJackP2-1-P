from enum import Enum

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 30
CARD_WIDTH = 100
CARD_HEIGHT = 150
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (100, 149, 237)
GOLD = (255, 215, 0)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 100, 0)

# Room server configuration
ROOM_SERVER_HOST = '69.62.103.94'
ROOM_SERVER_PORT = 5001

class GameState(Enum):
    MENU = 0
    WAITING = 1
    PLAYING = 2
    GAME_OVER = 3
    JOIN_SCREEN = 4
    ROOM_LIST = 5
    CREATE_ROOM = 6
    SETTINGS = 7 