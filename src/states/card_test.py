import random
from src.objects.card import Card
from typing import List

from engine import *
from objects import *


class CardTestState(State):
    BG_COLORS = [
        0x134180,
        0x9463AA,
        0x3C926E,
    ]
    FPS = 60

    def __init__(self):
        super().__init__()

        self.player = self.add(Player())
        self.deck = self.add(Deck())
        self.spawn()

    def spawn(self):
        for _ in range(5):
            image = pygame.Surface((80, 120), pygame.SRCALPHA)
            image.fill(random_rainbow_color(60))
            pygame.draw.circle(image, "white", (40, 90), 15, 4)
            self.deck.add_card(Card(image, f=change_fire_rate))

        ai = EnemyBlockAI()
        for e in ai.spawn():
            self.add(e)
