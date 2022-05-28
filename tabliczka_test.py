#!/usr/bin/python3

# tabliczka: a program for learning multiplication table
# Copyright 2021-2022 Marcin Owsiany <marcin@owsiany.pl>

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


class TestFrequency(unittest.TestCase):

    def test_frequency(self):
        quick = tabliczka._FREQ_QUICK
        slow = tabliczka._FREQ_MAX
        table = [
            (-10**10, quick),
            (-10, quick),
            (-1, quick),
            (-0.01, quick),
            (0, quick),
            (0.01, quick),
            (tabliczka._ANSWER_SEC_QUICK, quick),
            (tabliczka._ANSWER_SEC_QUICK + 0.01, 1.1237499999999974),
            ((tabliczka._ANSWER_SEC_QUICK + tabliczka._ANSWER_SEC_MAX) / 2, (quick + slow) / 2),
            (tabliczka._ANSWER_SEC_MAX - 0.01, 99.87625),
            (tabliczka._ANSWER_SEC_MAX, slow),
            (tabliczka._ANSWER_SEC_MAX + 0.01, slow),
            (tabliczka._ANSWER_SEC_MAX + 10, slow),
            (tabliczka._ANSWER_SEC_MAX + 10**10, slow),
        ]
    
        for index, data in enumerate(table):
          delay, expected_frequency = data
          self.assertEqual(tabliczka.frequency(delay), expected_frequency, index)


if __name__ == '__main__':
    unittest.main()
