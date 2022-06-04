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


from os import path
import pygame


def _load(file_name):
  return pygame.image.load(path.abspath(path.join(path.dirname(__file__), file_name)))


def correct_image():
  return _load('score-correct-64.png')


def error_image():
  return _load('score-error-64.png')
