from pygame import Vector2

from engine import *
import states

__all__ = ["Player", "Bullet"]


class Player(Entity):
    VELOCITY = 4
    SPAWN = W / 2, H - 20
    FIRE_COOLDOWN = 0
    INITIAL_LIFE = 1000
    SIZE = (20, 12)
    FIRE_DAMAGE = 60

    def __init__(self):
        img = pygame.Surface(self.SIZE)
        img.fill(GREEN)
        super().__init__(self.SPAWN, img, size=self.SIZE)
        self.fire_cooldown = Cooldown(self.FIRE_COOLDOWN)
        self.health_bar = HealthBar((0, 0, 30, 1), RED, self)
        self.fire_power = self.FIRE_DAMAGE
        self.bullets = 1
        self.score = 0
        self.coins = 0

        self.hitless = True
        self.kills = 0
        self.bullets_shoot = 0
        self.bullets_well_aimed = 0

    def logic(self):
        super().logic()
        self.fire_cooldown.tick()
        self.health_bar.logic()
        self.health_bar.center = self.center + (0, self.size.y / 2 + 6)

    def draw(self, gfx: "GFX"):
        super(Player, self).draw(gfx)
        self.health_bar.draw(gfx)

        # Score
        r = gfx.blit(scale(image("cup"), 2), topleft=(10, 10))
        t = text(str(int(self.score)), 16, WHITE)
        gfx.blit(t, midleft=r.midright + Vector2(4, 0))

        # Coins
        r = gfx.blit(scale(image("coin"), 2), topleft=(10, r.bottom + 5))
        t = text(str(int(self.coins)), 16, WHITE)
        gfx.blit(t, midleft=r.midright + Vector2(4, 0))

    def move(self, axis):
        self.pos.x += axis.value * self.VELOCITY
        self.pos.x = clamp(self.pos.x, self.size.x / 2, W - self.size.x / 2)

    def fire(self, _button):
        if self.fire_cooldown.fire():
            w = 5 * (self.bullets - 1)
            for i in range(self.bullets):
                if self.bullets > 1:
                    x = chrange(i, (0, self.bullets - 1), (-w / 2, w / 2))
                else:
                    x = 0
                y = abs(i - (self.bullets - 1) / 2) * 3 - 5
                self.state.add(Bullet(self.center + (x, y), self, damage=self.fire_power))
                self.bullets_shoot += 1

    def create_inputs(self):
        motion = Axis(pygame.K_a, pygame.K_d, JoyAxis(JOY_HORIZ_LEFT),).always_call(self.move)

        fire = Button(pygame.K_SPACE, MouseButtonPress(1), JoyButton(0)).on_press_repeated(
            self.fire, 0
        )
        return {
            "player motion": motion,
            "fire": fire,
        }

    def on_death(self):
        self.state.particles.add_explosion(self.center, 200, 1000, "red")

        @self.state.do_later(60)
        def new_game():
            self.state.replace_state(states.GameState())

    def did_hit(self, enemy, bullet):
        self.bullets_well_aimed += 1

    def did_kill(self, enemy: "Enemy", bullet):
        bonus = enemy.POINTS * self.state.game_values.points_bonus
        self.score += bonus
        self.coins += bonus / 10
        self.kills += 1

    def did_hit_by(self, bullet):
        self.hitless = False

    def go_next_level(self):
        self.life = self.max_life
        self.hitless = True


class Bullet(Object):
    VELOCITY = 7
    SIZE = (2, 5)

    def __init__(self, pos, shooter, damage=100, friend=True):
        direction = -self.VELOCITY if friend else self.VELOCITY / 2
        super().__init__(pos, self.SIZE, vel=(0, direction))
        self.shooter = shooter
        self.friend = friend
        self.damage = damage
        play("shoot")

    def logic(self):
        super().logic()
        if not SCREEN.inflate(10, 10).collidepoint(self.pos):
            self.alive = False
            return

        targets = self.state.get_all("Enemy") if self.friend else [self.state.player]

        target: Entity
        for target in targets:
            if not target.alive:
                continue

            if target.rect.colliderect(self.rect):
                play("hit")
                target.damage(self.damage)
                self.alive = False

                if self.friend:
                    self.state.player.did_hit(target, self)
                    if not target.alive:
                        self.state.player.did_kill(target, self)
                else:
                    self.state.player.did_hit_by(self)

                return

        if self.friend:
            for bullet in self.state.get_all(Bullet):
                if not bullet.friend and self.rect.colliderect(bullet.rect.inflate(2, 2)):
                    self.alive = False
                    bullet.alive = False
                    self.state.player.did_hit(bullet, self)
                    self.state.particles.add_explosion(self.center, 30, 100)

    def draw(self, gfx: "GFX"):
        color = "white" if self.friend else "red"
        gfx.rect(*self.rect, color)
