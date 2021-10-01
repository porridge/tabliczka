#!/usr/bin/python3

import itertools
import pygame
import random


_NUMBERS = range(1, 11)
_QUESTIONS = list(itertools.product(_NUMBERS, _NUMBERS))


def main():

    ui = start_ui()
    state = load_state()
    while True:
        problem = generate_problem(state)
        answer = ui.show_problem_and_get_answer(problem)
        state.update_from(problem, answer)
        state.save()


def start_ui():
    return CLI().start()


def load_state():
    return State()


def generate_problem(state):
    return Problem(*random.choice(_QUESTIONS))


class State:
    
    def update_from(self, problem, answer):
        pass

    def save(self):
        pass


class CLI:

    def start(self):
        return self

    def show_problem_and_get_answer(self, problem):
        print(problem)
        return Answer(input())


class GUI:

    def __init__(self):
        self._digit_size = (40, 80)
        self._screen_size = (self._digit_size[0] * (2+3+2+7+2+3+2), self._digit_size[1] * 7)
        self._screen = pygame.display.set_mode(self._screen_size)

    def start(self):
        pygame.display.flip()
        return self

    def show_problem_and_get_answer(self, problem):
        return Answer()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            screen.fill((255, 255, 255))
            pygame.draw.circle(screen, (0, 0, random.choice(range(0,255))), (250, 250), 75)
            pygame.display.flip()


class Problem:
    
    def __init__(self, a, b):
        self._a = a
        self._b = b

    def __str__(self):
        return "%(a)s * %(b)s = ? [%(answers)s]" % dict(
                a=self._a,
                b=self._b,
                answers=", ".join(str(k) for k in self.answers()))

    def answer(self):
        return self._a * self._b

    def answers(self):
        return sorted(random.sample(self.wrong_answers().keys(), 3) + [self.answer()])

    def wrong_answers(self):
        closest_as = closest_ns(self._a)
        closest_bs = closest_ns(self._b)
        closest_problems = dict((p[0]*p[1], p) for p in itertools.product(closest_as, closest_bs))
        del closest_problems[self.answer()]
        if len(closest_problems) >= 3:
            return closest_problems
        close_as = close_ns(self._a)
        close_bs = close_ns(self._b)
        close_problems = dict((p[0]*p[1], p) for p in itertools.product(close_as, close_bs))
        del close_problems[self.answer()]
        return close_problems


def closest_ns(n):
    if n == 1:
        return 1, 2
    elif n == 10:
        return 9, 10
    else:
        return n-1, n, n+1


def close_ns(n):
    if n == 1 or n == 2:
        return 1, 2, 3, 4
    elif n == 9 or n == 10:
        return 7, 8, 9, 10
    else:
        return n-2, n-1, n, n+1, n+2


class Answer:
    def __init__(self, text):
        self._text = text


if __name__ == '__main__':
    pygame.init()
    try:
      main()
    finally:
      pygame.quit()

