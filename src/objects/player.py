from engine import *
import states

__all__ = ["Player", "Bullet"]


class Player(Object):
    VELOCITY = 4
    SPAWN = W / 2, H - 20
    FIRE_COOLDOWN = 24

    def __init__(self):
        super().__init__(self.SPAWN, (20, 12))
        self.fire_cooldown = Cooldown(self.FIRE_COOLDOWN)

    def logic(self):
        super().logic()
        self.fire_cooldown.tick()

    def draw(self, gfx: "GFX"):
        gfx.rect(*self.rect, GREEN)

    def move(self, axis):
        self.pos.x += axis.value * self.VELOCITY
        self.pos.x = clamp(self.pos.x, self.size.x / 2, W - self.size.x / 2)

    def fire(self, _button):
        if self.fire_cooldown.fire():
            self.state.add(Bullet(self.center))

    def create_inputs(self):
        motion = Axis(
            [pygame.K_a, pygame.K_LEFT],
            [pygame.K_d, pygame.K_RIGHT],
            JoyAxis(JOY_HORIZ_LEFT),
        ).always_call(self.move)

        fire = Button(
            pygame.K_SPACE, MouseButtonPress(1), JoyButton(0)
        ).on_press_repeated(self.fire, 0)
        return {
            "player motion": motion,
            "fire": fire,
        }

    def on_death(self):
        self.state.particles.add_explosion(self.center, 200, 1000, "red")

        @self.state.do_later(60)
        def new_game():
            self.state.replace_state(states.CardTestState())


class Bullet(Object):
    VELOCITY = 7
    SIZE = (2, 5)

    def __init__(self, pos, friend=True):
        direction = -self.VELOCITY if friend else self.VELOCITY / 2
        super().__init__(pos, self.SIZE, vel=(0, direction))
        self.friend = friend

    def logic(self):
        super().logic()
        if not SCREEN.inflate(10, 10).collidepoint(self.pos):
            self.alive = False

        targets = self.state.get_all("Ennemy") if self.friend else [self.state.player]

        for target in targets:
            if target.rect.colliderect(self.rect):
                target.alive = False
                self.alive = False

                if self.friend:
                    # Todo: increase score
                    pass
                return

    def draw(self, gfx: "GFX"):
        color = "white" if self.friend else "red"
        gfx.rect(*self.rect, color, anchor="center")
