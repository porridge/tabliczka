#!/usr/bin/python3

# tabliczka: a program for learning multiplication table
# Copyright 2021 Marcin Owsiany <marcin@owsiany.pl>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


import argparse
import itertools
import logging
import pickle
import os
import pygame
import random
import time


_NUMBERS = range(1, 11)
_ERROR_FEEDBACK_DELAY_MILLISEC = 2*1000
_FREQ_UNKNOWN = 101
_FREQ_MAX = 100
_ANSWER_SEC_MAX = 10
_FREQ_QUICK = 1
_ANSWER_SEC_QUICK= 2

_KEYS_MINECRAFT_LOWER = 'wdsa'
_KEYS_MINECRAFT_UPPER = 'WDSA'
_KEYS_ARROWS = (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT)

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
    parser.add_argument('--limit', type=int, help='Quit after correctly solving this many questions.')
    parser.add_argument('--show_scores', action='store_true', help='Show scores in main window.')
    parser.add_argument('--show_feedback', action='store_true', help='Show feedback on wrong answers.')
    parser.add_argument('--debug', action='store_true', help='Turn on debug-level logging.')
    args = parser.parse_args()

    logging.basicConfig(
            level=(logging.DEBUG if args.debug else logging.INFO),
            format='%(levelname).1s%(asctime)s.%(msecs)03d] %(message)s',
            datefmt='%m%d %H:%M:%S')

    if args.dump:
        State.load().dump()
        return

    with get_ui_class(args.ui)(args.show_scores, args.show_feedback) as ui:
        try:
            run(ui, args.limit)
        except QuitException:
            pass


def get_ui_class(ui_name):
    return CLI if ui_name == 'cli' else GUI


def run(ui, limit):
    state = State.load()
    while limit is None or limit > 0:
        problem = state.generate_problem()
        ui.solve_problem(problem, state)
        state.update_from(problem)
        if not problem.answered_correctly():
            ui.provide_feedback(problem, state)
        elif limit is not None:
            limit -= 1
        state.save()


def frequency(answer_delay):
    delay_range = _ANSWER_SEC_MAX - _ANSWER_SEC_QUICK
    freq_range = _FREQ_MAX - _FREQ_QUICK
    delay = answer_delay - _ANSWER_SEC_QUICK
    resp = _FREQ_QUICK + (delay / delay_range) * freq_range
    return max(_FREQ_QUICK, min(_FREQ_MAX, resp))


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
        self._last_generated = None  # We do not bother storing this across executions.

    def _update_frequency(self, question, latest_frequency):
        previous = self._frequency_map[question]
        if previous == _FREQ_UNKNOWN:
            new = latest_frequency
        else:
            new = (previous + latest_frequency) / 2
        self._frequency_map[question] = new

    def update_from(self, problem):
        q = problem._question()
        if not problem.answered_correctly():
            self._update_frequency(q, _FREQ_MAX)
            self._error_count += 1
        else:
            self._update_frequency(q, frequency(problem.answer_delay()))
            self._correct_count += 1

    def save(self):
        os.makedirs(_state_home, mode=0o700, exist_ok=True)
        with open(_state_file, "wb") as state_file:
            pickle.dump(self._frequency_map, state_file, protocol=-1)
            pickle.dump(self._correct_count, state_file, protocol=-1)
            pickle.dump(self._error_count, state_file, protocol=-1)

    def generate_problem(self):
        repetitions = (itertools.repeat(e[0], int(e[1])) for e in self._frequency_map.items() if e[0] != self._last_generated)
        questions = list(i for i in (itertools.chain(*repetitions)))
        generated = random.choice(questions)
        self._last_generated = generated
        return Problem(*generated)

    def dump(self):
        print('Frequency map:')
        print('   |', *[('%4d ' % j) for j in _NUMBERS])
        print('---+', '-'*60, sep='')
        for i in _NUMBERS:
            print('%2d |' % i, *[('%5.1f' % self._frequency_map[(i, j)]) for j in _NUMBERS])
        print('Correct:', self._correct_count)
        print('Errors:', self._error_count)

    def correct_count(self):
        return self._correct_count

    def error_count(self):
        return self._error_count


class CLI:
    def __init__(self, show_scores, show_feedback):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def solve_problem(self, problem, state):
        print("%s [%s]" % (problem, ", ".join(str(k) for k in problem.answers())))
        asked_time = time.time()
        problem.answered(input(), asked_time)

    def provide_feedback(self, problem, state):
        print(":-)" if problem.answered_correctly() else ":-(")


class GUI:
    _background_color = pygame.Color('white')
    _text_color = pygame.Color('black')
    _score_color = pygame.Color('gray')
    _question_bg_color = pygame.Color('lightskyblue')
    _answer_correct_color = pygame.Color('lightgreen')
    _answer_error_color = pygame.Color(238, 144, 144, 255)

    def __init__(self, show_scores, show_feedback):
        self._font_size = 80
        self._score_font_size = 50
        self._should_show_scores = show_scores
        self._should_show_feedback = show_feedback

    def __enter__(self):
        logging.debug('Initializing pygame.')
        pygame.init()
        logging.debug('Preparing main font.')
        self._font = pygame.font.SysFont("monospace", self._font_size)
        if self._should_show_scores:
            logging.debug('Preparing score font.')
            self._score_font = pygame.font.SysFont("unifont", self._score_font_size)  # TODO: use a picture for portability
        self._digit_size = self._font.size('J')
        self._screen_size = (self._font.size(' 100  10 * 10 = ?  100 ')[0], self._digit_size[1] * 7)
        logging.debug('Setting display mode.')
        self._screen = pygame.display.set_mode(self._screen_size)
        self._clock = pygame.time.Clock()
        logging.debug('Enabling display.')
        pygame.display.flip()
        logging.debug('GUI setup complete.')
        return self

    def __exit__(self, *exc):
        logging.debug('Quitting pygame.')
        pygame.quit()
        logging.debug('GUI teardown complete.')

    def _tick(self):
        self._clock.tick(30) # low framerate is fine for this app

    def solve_problem(self, problem, state):
        answers = self._display_problem(problem, state)

        asked_time = time.time()

        while True:
            self._tick()
            for event in pygame.event.get():
                logging.debug('Processing event %s.', event)
                if event.type == pygame.QUIT:
                    logging.debug('Initiating shutdown.')
                    raise QuitException()
                if event.type == pygame.KEYDOWN:
                    if event.unicode and event.unicode in _KEYS_MINECRAFT_LOWER:
                        answer_index = _KEYS_MINECRAFT_LOWER.index(event.unicode)
                    elif event.unicode and event.unicode in _KEYS_MINECRAFT_UPPER:
                        answer_index = _KEYS_MINECRAFT_UPPER.index(event.unicode)
                    elif event.key in _KEYS_ARROWS:
                        answer_index = _KEYS_ARROWS.index(event.key)
                    else:
                        continue
                    problem.answered(answers[answer_index], asked_time)
                    return

    def provide_feedback(self, problem, state):
        if not self._should_show_feedback:
            return
        self._display_problem(problem, state, reveal_solution=True)
        wait_start = pygame.time.get_ticks()
        wait_end = wait_start + _ERROR_FEEDBACK_DELAY_MILLISEC

        while pygame.time.get_ticks() < wait_end:
            self._tick()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise QuitException()
                # Ignore any other event

    def _display_problem(self, problem, state, reveal_solution=False):
        logging.debug('Displaying %s.' % ('solution' if reveal_solution else 'problem'))
        self._screen.fill(self._background_color)
        if self._should_show_scores:
            self._show_correct_score(state)
            self._show_error_score(state)
        self._show_question(problem)
        answers = problem.answers()
        self._show_answers(problem, answers, reveal_solution=reveal_solution)
        logging.debug('Updating display.')
        pygame.display.flip()
        logging.debug('Problem displayed.')
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
        self._answers = list(random.sample(sorted(self.wrong_answers()), 3)) + [self.correct_answer()]
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
