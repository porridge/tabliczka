#!/usr/bin/python3

import argparse
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
_QUICK_ANSWER_SEC = 5
_STATE = os.path.expanduser("~/.tabliczka")  # TODO: use XDG_...


class QuitException(Exception):
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', choices=['cli', 'gui'])
    parser.add_argument('--dump', action='store_true', help='Just show the saved state and quit.')
    args = parser.parse_args()

    if args.dump:
        State().dump()
        return

    with get_ui_class(args.ui)() as ui:
        try:
            run(ui)
        except QuitException:
            pass


def get_ui_class(ui_name):
    return CLI if ui_name == 'cli' else GUI


def run(ui):
    state = State()
    while True:
        problem = state.generate_problem()
        ui.solve_problem(problem)
        state.update_from(problem)
        state.save()


class State:

    def __init__(self):
        try:
            with open(_STATE, "rb") as state_file:
                self._frequency_map = pickle.load(state_file)
                try:
                    self._correct_count = pickle.load(state_file)
                    self._error_count = pickle.load(state_file)
                except Exception:
                    self._correct_count = 0
                    self._error_count = 0
        except Exception as e:
            logging.warning('Failed to load state, creating empty state: %s' % e)
            self._frequency_map = dict((q, _FREQ_UNKNOWN) for q in itertools.product(_NUMBERS, _NUMBERS))
    
    def update_from(self, problem):
        q = problem._question()
        # TODO: take historical data into account as well
        if not problem.answered_correctly():
            self._frequency_map[q] = _FREQ_UNKNOWN
            self._error_count += 1
        elif problem.answer_delay() <= _QUICK_ANSWER_SEC:
            self._frequency_map[q] = _FREQ_QUICK
            self._correct_count += 1
        else:
            self._frequency_map[q] = _FREQ_SLOW
            self._correct_count += 1

    def save(self):
        with open(_STATE, "wb") as state_file:
            pickle.dump(self._frequency_map, state_file, protocol=-1)
            pickle.dump(self._correct_count, state_file, protocol=-1)
            pickle.dump(self._error_count, state_file, protocol=-1)

    def generate_problem(self):
        repetitions = (itertools.repeat(e[0], e[1]) for e in self._frequency_map.items())
        questions = list(i for i in (itertools.chain(*repetitions)))
        return Problem(*random.choice(questions))

    def dump(self):
        print('Frequency map:')
        print('   |', *[('%2d' % j) for j in _NUMBERS])
        print('---+', '-'*30, sep='')
        for i in _NUMBERS:
            print('%2d |' % i, *[('%2d' % self._frequency_map[(i, j)]) for j in _NUMBERS])
        print('Correct:', self._correct_count)
        print('Errors:', self._error_count)


class CLI:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def solve_problem(self, problem):
        print("%s [%s]" % (problem, ", ".join(str(k) for k in self.answers())))
        asked_time = time.time()
        problem.answered(input(), asked_time)
        print(":-)" if problem.answered_correctly() else ":-(")


class GUI:

    def __init__(self):
        self._font_size = 80

    def __enter__(self):
        pygame.init()
        self._font = pygame.font.SysFont("monospace", self._font_size)
        self._digit_size = self._font.size('J')
        self._screen_size = (self._font.size(' 100  10 * 10 = ?  100 ')[0], self._digit_size[1] * 7)
        self._screen = pygame.display.set_mode(self._screen_size)
        pygame.display.flip()
        return self

    def __exit__(self, *exc):
        pygame.quit()

    def solve_problem(self, problem):
        self._screen.fill(pygame.Color('white'))
        text_color = pygame.Color('black')
        question = self._font.render(str(problem), 1, text_color)
        screen_center = self._screen.get_rect().center
        question_rect = question.get_rect(center=screen_center)
        pygame.draw.rect(self._screen, pygame.Color('lightskyblue'), question_rect)
        self._screen.blit(question, question_rect)

        answers = problem.answers()

        answer_up = self._font.render(answers[0], 1, text_color)
        self._screen.blit(answer_up, answer_up.get_rect(center=(screen_center[0], int(1.5*self._digit_size[1]))))

        answer_right = self._font.render(answers[1], 1, text_color)
        self._screen.blit(answer_right, answer_up.get_rect(center=(int(21*self._digit_size[0]), screen_center[1])))

        answer_down = self._font.render(answers[2], 1, text_color)
        self._screen.blit(answer_down, answer_down.get_rect(center=(screen_center[0], int(5.5*self._digit_size[1]))))

        answer_left = self._font.render(answers[3], 1, text_color)
        self._screen.blit(answer_left, answer_up.get_rect(center=(int(3*self._digit_size[0]), screen_center[1])))

        pygame.display.flip()
        asked_time = time.time()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise QuitException()
                if event.type == pygame.KEYDOWN and event.unicode and event.unicode in 'wdsa':
                    problem.answered(answers['wdsa'.index(event.unicode)], asked_time)
                    # TODO: provide feedback
                    return


class Problem:
    
    def __init__(self, a, b):
        self._a = a
        self._b = b

    def __str__(self):
        return "%(a)s * %(b)s = ?" % dict(a=self._a, b=self._b)

    def _question(self):
        return (self._a, self._b)

    def correct_answer(self):
        return str(self._a * self._b)

    def answers(self):
        answers = list(random.sample(self.wrong_answers().keys(), 3)) + [self.correct_answer()]
        random.shuffle(answers)
        return answers

    def wrong_answers(self):
        # TODO: also generate correct_answer+1, +2, -1, -2, ...
        closest_as = closest_ns(self._a)
        closest_bs = closest_ns(self._b)
        closest_problems = dict((str(p[0]*p[1]), p) for p in itertools.product(closest_as, closest_bs))
        del closest_problems[self.correct_answer()]
        if len(closest_problems) >= 3:
            return closest_problems
        close_as = close_ns(self._a)
        close_bs = close_ns(self._b)
        close_problems = dict((str(p[0]*p[1]), p) for p in itertools.product(close_as, close_bs))
        del close_problems[self.correct_answer()]
        return close_problems

    def answered(self, answer_text, asked_time):
        self._answer_text = answer_text.strip()
        self._answer_delay = time.time() - asked_time

    def answer_delay(self):
        return self._answer_delay

    def answered_correctly(self):
        return self._answer_text == self.correct_answer()


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



if __name__ == '__main__':
    main()
