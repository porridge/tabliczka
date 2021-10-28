#!/usr/bin/python3

import argparse
import itertools
import logging
import pickle
import os
import pygame
import random
import time


_NUMBERS = range(1, 11)
_ERROR_FEEDBACK_DELAY_SEC = 2
_FREQ_UNKNOWN = 50
_FREQ_SLOW = 30
_FREQ_QUICK = 1
_QUICK_ANSWER_SEC = 5

_home = os.path.expanduser('~')
_xdg_state_home = os.environ.get('XDG_STATE_HOME') or os.path.join(_home, '.local', 'state')
_state_home = os.path.join(_xdg_state_home, 'tabliczka')
_state_file = os.path.join(_state_home, 'state.pickle')
_log_file = os.path.join(_state_home, 'log.json')
_LEGACY_STATE = os.path.expanduser("~/.tabliczka")


class QuitException(Exception):
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', choices=['cli', 'gui'])
    parser.add_argument('--dump', action='store_true', help='Just show the saved state and quit.')
    args = parser.parse_args()

    if args.dump:
        State.load().dump()
        return

    with get_ui_class(args.ui)() as ui:
        try:
            run(ui)
        except QuitException:
            pass


def get_ui_class(ui_name):
    return CLI if ui_name == 'cli' else GUI


def run(ui):
    state = State.load()
    while True:
        problem = state.generate_problem()
        ui.solve_problem(problem, state)
        state.update_from(problem)
        if not problem.answered_correctly():
            ui.provide_feedback(problem, state)
        state.save()


class State:

    @classmethod
    def load(cls):
        try:
            try:
                return cls.load_from(_state_file)
            except:
                return cls.load_from(_LEGACY_STATE)
        except Exception as e:
            logging.warning('Failed to load state, creating empty state: %s' % e)
            return cls()

    @classmethod
    def load_from(cls, state_filename):
        with open(state_filename, "rb") as state_file:
            frequency_map = pickle.load(state_file)
            try:
                correct_count = pickle.load(state_file)
                error_count = pickle.load(state_file)
            except Exception:
                correct_count = 0
                error_count = 0
            return cls(frequency_map, correct_count, error_count)

    def __init__(self, frequency_map=None, correct_count=0, error_count=0):
        if frequency_map:
            self._frequency_map = frequency_map
        else:
            self._frequency_map = dict((q, _FREQ_UNKNOWN) for q in itertools.product(_NUMBERS, _NUMBERS))
        self._correct_count = correct_count
        self._error_count = error_count
    
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
        os.makedirs(_state_home, mode=0o700, exist_ok=True)
        with open(_state_file, "wb") as state_file:
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

    def correct_count(self):
        return self._correct_count

    def error_count(self):
        return self._error_count


class CLI:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def solve_problem(self, problem, state):
        print("%s [%s]" % (problem, ", ".join(str(k) for k in self.answers())))
        asked_time = time.time()
        problem.answered(input(), asked_time)
        print(":-)" if problem.answered_correctly() else ":-(")


class GUI:
    _background_color = pygame.Color('white')
    _text_color = pygame.Color('black')
    _score_color = pygame.Color('gray')
    _question_bg_color = pygame.Color('lightskyblue')
    _answer_correct_color = pygame.Color('lightgreen')
    _answer_error_color = pygame.Color(238, 144, 144, 255)

    def __init__(self):
        self._font_size = 80
        self._score_font_size = 50

    def __enter__(self):
        pygame.init()
        self._font = pygame.font.SysFont("monospace", self._font_size)
        self._score_font = pygame.font.SysFont("unifont", self._score_font_size)  # TODO: use a picture for portability
        self._digit_size = self._font.size('J')
        self._screen_size = (self._font.size(' 100  10 * 10 = ?  100 ')[0], self._digit_size[1] * 7)
        self._screen = pygame.display.set_mode(self._screen_size)
        pygame.display.flip()
        return self

    def __exit__(self, *exc):
        pygame.quit()

    def solve_problem(self, problem, state):
        answers = self._display_problem(problem, state)

        asked_time = time.time()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise QuitException()
                if event.type == pygame.KEYDOWN and event.unicode and event.unicode in 'wdsa':
                    problem.answered(answers['wdsa'.index(event.unicode)], asked_time)
                    return

    def provide_feedback(self, problem, state):
        self._display_problem(problem, state, reveal_solution=True)
        time.sleep(_ERROR_FEEDBACK_DELAY_SEC) # TODO: is there a better way?

    def _display_problem(self, problem, state, reveal_solution=False):
        self._screen.fill(self._background_color)
        self._show_correct_score(state)
        self._show_error_score(state)
        self._show_question(problem)
        answers = problem.answers()
        self._show_answers(problem, answers, reveal_solution=reveal_solution)
        pygame.display.flip()
        return answers

    def _show_correct_score(self, state):
        screen_bottom_left = self._screen.get_rect().bottomleft
        correct_score = self._score_font.render('✅ %4d' % state.correct_count(), 1, self._score_color)
        correct_score_rect = correct_score.get_rect(bottomleft=screen_bottom_left)
        self._screen.blit(correct_score, correct_score_rect)

    def _show_error_score(self, state):
        screen_bottom_right = self._screen.get_rect().bottomright
        error_score = self._score_font.render('%4d ❌' % state.error_count(), 1, self._score_color)
        error_score_rect = error_score.get_rect(bottomright=screen_bottom_right)
        self._screen.blit(error_score, error_score_rect)

    def _show_question(self, problem):
        screen_center = self._screen.get_rect().center
        question = self._font.render(str(problem), 1, self._text_color)
        question_rect = question.get_rect(center=screen_center)
        pygame.draw.rect(self._screen, self._question_bg_color, question_rect)
        self._screen.blit(question, question_rect)

    def _show_answers(self, problem, answers, reveal_solution=False):
        screen_center = self._screen.get_rect().center

        answer_up = self._font.render(answers[0], 1, self._text_color)
        answer_up_rect = answer_up.get_rect(center=(screen_center[0], int(1.5*self._digit_size[1])))
        pygame.draw.rect(self._screen, self._answer_color(problem, answers[0], reveal_solution), answer_up_rect)
        self._screen.blit(answer_up, answer_up_rect)

        answer_right = self._font.render(answers[1], 1, self._text_color)
        answer_right_rect = answer_right.get_rect(center=(int(21*self._digit_size[0]), screen_center[1]))
        pygame.draw.rect(self._screen, self._answer_color(problem, answers[1], reveal_solution), answer_right_rect)
        self._screen.blit(answer_right, answer_right_rect)

        answer_down = self._font.render(answers[2], 1, self._text_color)
        answer_down_rect = answer_down.get_rect(center=(screen_center[0], int(5.5*self._digit_size[1])))
        pygame.draw.rect(self._screen, self._answer_color(problem, answers[2], reveal_solution), answer_down_rect)
        self._screen.blit(answer_down, answer_down_rect)

        answer_left = self._font.render(answers[3], 1, self._text_color)
        answer_left_rect = answer_left.get_rect(center=(int(3*self._digit_size[0]), screen_center[1]))
        pygame.draw.rect(self._screen, self._answer_color(problem, answers[3], reveal_solution), answer_left_rect)
        self._screen.blit(answer_left, answer_left_rect)


    def _answer_color(self, problem, answer, reveal_solution=False):
        if not reveal_solution:
            return self._background_color
        return self._answer_correct_color if problem.correct_answer() == answer else self._answer_error_color


class Problem:
    
    def __init__(self, a, b):
        self._a = a
        self._b = b
        self._answers = list(random.sample(self.wrong_answers().keys(), 3)) + [self.correct_answer()]
        random.shuffle(self._answers)

    def __str__(self):
        return "%(a)s * %(b)s = ?" % dict(a=self._a, b=self._b)

    def _question(self):
        return (self._a, self._b)

    def correct_answer(self):
        return str(self._a * self._b)

    def answers(self):
        return self._answers

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
