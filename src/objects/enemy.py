from collections import defaultdict
from random import choices
from typing import Set

from pygame import Vector2

from engine import *

__all__ = ["Enemy", "EnemyBlockAI", "SnakeAI"]


class Enemy(Entity):
    EDGE = 30
    SPEED = 0.5
    SCALE = 2
    INITIAL_LIFE = 50
    POINTS = 10
    COLOR = (255, 255, 255)
    PROBA = 10
    WAVE = 1

    FIRE_DAMAGE = 100

    IMAGE = Assets.Images.enemies(0)

    def __init__(self, pos, ai):
        self.color = self.COLOR
        self.IMAGE.set_palette_at(1, self.color)
        self.IMAGE = auto_crop(self.IMAGE)

        super().__init__(pos, self.IMAGE, size=None, vel=(self.SPEED, 0))
        self.ai = ai
        ai.add(self)
        self.spawning = True

    def fire(self):
        from objects import Bullet

        boost = self.state.game_values.enemy_damage_boost
        self.state.add(Bullet(self.center, self, damage=self.FIRE_DAMAGE * boost, friend=False))

    def script(self):
        initial_vel = self.vel
        self.vel = Vector2()
        spawn_frames = 40
        for i in range(spawn_frames):
            self.opacity = int(chrange(i, (0, spawn_frames - 1), (0, 255)))
            yield
        self.spawning = False
        self.vel = initial_vel

    def logic(self):
        if self.spawning:
            super().logic()
            return

        if self.pos.y > H - self.ai.ROW_HEIGHT * 2 and not isinstance(self.ai, FleeAI):
            self.ai.remove(self)
            self.ai = FleeAI()
        self.ai.logic(self)
        super().logic()
        if randrange(500) == 42:
            self.fire()

    def push_back(self, rows, duration=30):
        @self.add_script_decorator
        def script():
            target = rows * self.ai.ROW_HEIGHT
            k = 3
            scale = exp_impluse_integral(k) * duration
            print(scale)
            for i in range(duration):
                dy = exp_impulse(i / duration, k) / scale * target
                self.pos.y -= dy
                yield

    def on_death(self):
        self.state.particles.add_explosion(self.center)


class Damager(Enemy):
    FIRE_DAMAGE = Enemy.FIRE_DAMAGE * 3
    COLOR = (255, 0, 0)
    POINTS = 30

    PROBA = 4
    WAVE = 3


class Tank(Enemy):
    INITIAL_LIFE = Enemy.INITIAL_LIFE * 4
    COLOR = (182, 3, 252)
    POINTS = 45

    PROBA = 3
    WAVE = 2


class Worthy(Enemy):
    COLOR = (255, 215, 0)
    POINTS = 100
    PROBA = 1
    WAVE = 3


class AI:
    EDGE = 45  # min distance to sides
    ROW_HEIGHT = 30

    def __init__(self):
        # All the enemies controled by the same AI
        self.controled: Set[Enemy] = set()

        # Hack to have the logic called only once per frame
        self.called_on = set()

    def logic(self, enemy):
        self.controled = {e for e in self.controled if e.alive}

    def set_direction(self, x_direction, y_direction):
        for enemy in self.controled:
            enemy.vel = Vector2(enemy.SPEED * x_direction, enemy.SPEED * y_direction)

    def add(self, enemy):
        self.controled.add(enemy)

    def remove(self, enemy):
        try:
            self.controled.remove(enemy)
        except KeyError:
            pass

    def call_once_per_frame(self, enemy) -> bool:
        # The logic will run only when called with an enemy
        # which is in the called_on set, which should mean
        # that it has been called on every enemy in between, and thus
        # it is the next frame.
        if enemy in self.called_on or not self.called_on:
            self.called_on = {enemy}
            return True
        else:
            self.called_on.add(enemy)
            return False


class EnemyBlockAI(AI):
    def __init__(self):
        super().__init__()
        self.go_down_duration = 0

        self.max_controled = 0
        self.direction = 1  # right / -1 left

    def logic(self, enemy):

        if not self.call_once_per_frame(enemy):
            return

        self.max_controled = max(self.max_controled, len(self.controled))

        min_x = min(e.pos.x for e in self.controled)
        max_x = max(e.pos.x + e.size.x for e in self.controled)

        wall_left = min_x < self.EDGE
        wall_right = max_x > W - self.EDGE

        speed_boost = chrange(
            len(self.controled), (0, self.max_controled), (1, 5), power=3, flipped=True
        )

        self.go_down_duration -= 1
        if self.go_down_duration > 0:
            pass
        elif self.go_down_duration == 0:
            self.set_direction(self.direction, 0)
        elif wall_left or wall_right:
            self.direction *= -1  # swap direction for next row
            self.go_down_duration = int(self.ROW_HEIGHT / speed_boost / Enemy.SPEED)
            self.set_direction(0, 1)  # down

        for enemy in self.controled:
            if enemy.vel.length() > 0:
                enemy.vel.scale_to_length(enemy.SPEED * speed_boost)

        # We call super only later, because sometimes the AI logic is called
        # even if the enemy is dead, because it was killed in the same frame
        # and before its logic. This causes a problem for the last enemy.
        # As min() and max() have empty collections.
        super().logic(enemy)

    def spawn(self, rows=4, cols=10, wave=1):
        classes = [c for c in Enemy.__subclasses__() if c.WAVE <= wave] + [Enemy]
        weights = [c.PROBA for c in classes]

        for row in range(rows):
            for col in range(cols):
                x = chrange(col, (0, cols - 1), (self.EDGE * 3, W - self.EDGE * 3))
                y = self.EDGE + row * self.ROW_HEIGHT

                cls = choices(classes, weights)[0]
                yield cls((x, y), self)

    def spawn_wave(self, wave):
        print(wave)
        rows = 4 + wave // 3
        yield from self.spawn(rows, wave=wave)


class SnakeAI(AI):
    def __init__(self):
        super().__init__()
        self.goals = list(self.checkpoints())
        self.current_goals = defaultdict(int)

    def logic(self, enemy):
        super().logic(enemy)

        current = self.current_goals[enemy]

        try:
            if enemy.pos.distance_to(self.goals[current]) < enemy.SPEED:
                self.current_goals[enemy] += 1
            goal = self.goals[current]
        except IndexError:
            # No more goal.
            enemy.alive = False
            return

        self.vel = (goal - enemy.pos).normalize() * (enemy.SPEED)

    def checkpoints(self):
        y = self.EDGE
        while y < H + self.ROW_HEIGHT:
            yield self.EDGE, y
            yield W - self.EDGE, y
            yield W - self.EDGE, y + self.ROW_HEIGHT
            yield self.EDGE, y + self.ROW_HEIGHT
            y += 2 * self.ROW_HEIGHT

    def spawn(self, count):
        for i in range(count):
            pos = self.EDGE, self.EDGE - i * self.ROW_HEIGHT
            yield Enemy(pos, self)

    def add(self, enemy):
        super().add(enemy)


class FleeAI(AI):
    def __init__(self):
        super().__init__()

    def logic(self, enemy):
        super().logic(enemy)
        direction = 1 if enemy.pos.x > W / 2 else -1
        enemy.vel = Vector2(direction * enemy.SPEED * 3, 0)

        if not enemy.rect.colliderect(SCREEN):
            enemy.alive = False
