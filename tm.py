#!/usr/bin/python3

import itertools
import logging
import pickle
import os.path
import pygame
import random
import time


_NUMBERS = range(1, 11)
_FREQ_UNKNOWN = 50
_FREQ_SLOW = 30
_FREQ_QUICK = 1
_QUICK_ANSWER_SEC = 3
_STATE = os.path.expanduser("~/.tabliczka")  # TODO: use XDG_...


def main():

    ui = start_ui()
    state = State()
    while True:
        problem = state.generate_problem()
        answer = ui.show_problem_and_get_answer(problem)
        state.update_from(problem, answer)
        state.save()


def start_ui():
    return CLI().start()


class State:

    def __init__(self):
        try:
            with open(_STATE, "rb") as state_file:
                self._frequency_map = pickle.load(state_file)
        except Exception as e:
            logging.warning('Failed to load state, creating empty state: %s' % e)
            self._frequency_map = dict((q, _FREQ_UNKNOWN) for q in itertools.product(_NUMBERS, _NUMBERS))
    
    def update_from(self, problem, answer):
        q = problem._question()
        # TODO: take historical data into account as well
        if not problem.was_correct(answer):
            self._frequency_map[q] = _FREQ_UNKNOWN
        elif answer.delay() <= _QUICK_ANSWER_SEC:
            self._frequency_map[q] = _FREQ_QUICK
        else:
            self._frequency_map[q] = _FREQ_SLOW

    def save(self):
        with open(_STATE, "wb") as state_file:
            pickle.dump(self._frequency_map, state_file)

    def generate_problem(self):
        repetitions = (itertools.repeat(e[0], e[1]) for e in self._frequency_map.items())
        questions = list(i for i in (itertools.chain(*repetitions)))
        return Problem(*random.choice(questions))


class CLI:

    def start(self):
        return self

    def show_problem_and_get_answer(self, problem):
        print(problem)
        asked_time = time.time()
        return Answer(input(), asked_time)


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

    def _question(self):
        return (self._a, self._b)

    def correct_answer(self):
        return self._a * self._b

    def answers(self):
        answers = list(random.sample(self.wrong_answers().keys(), 3)) + [self.correct_answer()]
        random.shuffle(answers)
        return answers

    def wrong_answers(self):
        # TODO: also generate correct_answer+1, +2, -1, -2, ...
        closest_as = closest_ns(self._a)
        closest_bs = closest_ns(self._b)
        closest_problems = dict((p[0]*p[1], p) for p in itertools.product(closest_as, closest_bs))
        del closest_problems[self.correct_answer()]
        if len(closest_problems) >= 3:
            return closest_problems
        close_as = close_ns(self._a)
        close_bs = close_ns(self._b)
        close_problems = dict((p[0]*p[1], p) for p in itertools.product(close_as, close_bs))
        del close_problems[self.correct_answer()]
        return close_problems

    def was_correct(self, answer):
        return self.correct_answer() == answer.number()


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
    def __init__(self, text, asked_time):
        self._text = text
        self._delay = time.time() - asked_time

    def delay(self):
        return self._delay

    def number(self):
        return int(self._text)


if __name__ == '__main__':
    pygame.init()
    try:
      main()
    finally:
      pygame.quit()

