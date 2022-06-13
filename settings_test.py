#!/usr/bin/python3

# tabliczka: a program for learning multiplication table
# Copyright 2022 Marcin Owsiany <marcin@owsiany.pl>

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

import unittest
import tabliczka


class FakeSettingsFS:

    def read(self):
        pass

    def write(self, settings):
        pass


class NoSettingsFS(FakeSettingsFS):
    pass


class SomeSettingsFS(FakeSettingsFS):

    def __init__(self, settings):
        self._settings = settings

    def read(self):
        return self._settings

    def write(self, settings):
        self._settings.clear()
        self._settings.update(settings)


class TestSettings(unittest.TestCase):

    def test_no_settings(self):
        fs = NoSettingsFS()
        args = tabliczka.get_argument_parser().parse_args([])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, None)
        self.assertEqual(s.show_feedback, True)
        self.assertEqual(s.show_scores, True)
        self.assertEqual(s.score_font, 'monospace')

    def test_settings_from_fs(self):
        fs = SomeSettingsFS(dict(
            limit=1,
            show_feedback=False,
            show_scores=False,
            score_font='dingbats'))
        args = tabliczka.get_argument_parser().parse_args([])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, 1)
        self.assertEqual(s.show_feedback, False)
        self.assertEqual(s.show_scores, False)
        self.assertEqual(s.score_font, 'dingbats')

    def test_settings_from_fs_overridden(self):
        fs = SomeSettingsFS(dict(
            limit=1,
            show_feedback=False,
            show_scores=False,
            score_font='dingbats'))
        args = tabliczka.get_argument_parser().parse_args([
                '--limit', '2',
                '--show-feedback',
                '--show-scores',
                '--score-font=asdf'
            ])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, 2)
        self.assertEqual(s.show_feedback, True)
        self.assertEqual(s.show_scores, True)
        self.assertEqual(s.score_font, 'asdf')

    def test_settings_lifecycle(self):
        settings_backend = dict()
        fs = SomeSettingsFS(settings_backend)
        args = tabliczka.get_argument_parser().parse_args([
                '--limit', '2',
                '--no-show-feedback',
                '--no-show-scores',
                '--score-font=asdf'
            ])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, 2)
        self.assertEqual(s.show_feedback, False)
        self.assertEqual(s.show_scores, False)
        self.assertEqual(s.score_font, 'asdf')
        self.assertDictEqual(settings_backend, dict(
            limit=2,
            show_feedback=False,
            show_scores=False,
            score_font='asdf'))

        args2 = tabliczka.get_argument_parser().parse_args([])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, 2)
        self.assertEqual(s.show_feedback, False)
        self.assertEqual(s.show_scores, False)
        self.assertEqual(s.score_font, 'asdf')
        self.assertDictEqual(settings_backend, dict(
            limit=2,
            show_feedback=False,
            show_scores=False,
            score_font='asdf'))

    def test_settings_lifecycle_partial(self):
        settings_backend = dict()
        fs = SomeSettingsFS(settings_backend)
        args = tabliczka.get_argument_parser().parse_args([
                '--no-show-feedback'
            ])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, None)
        self.assertEqual(s.show_feedback, False)
        self.assertEqual(s.show_scores, True)
        self.assertEqual(s.score_font, 'monospace')
        self.assertDictEqual(settings_backend, dict(show_feedback=False))

        args2 = tabliczka.get_argument_parser().parse_args([])
        s = tabliczka.Settings(fs, args)
        self.assertEqual(s.limit, None)
        self.assertEqual(s.show_feedback, False)
        self.assertEqual(s.show_scores, True)
        self.assertEqual(s.score_font, 'monospace')
        self.assertDictEqual(settings_backend, dict(show_feedback=False))


if __name__ == '__main__':
    unittest.main()

