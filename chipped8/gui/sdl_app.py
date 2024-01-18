#!/usr/bin/env python

# Copyright 2024 John Schember <john@nachtimwald.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import time

import sdl2.ext

import chipped8

class SDLApp():

    def __init__(self, args):
        sdl2.ext.init()

        self._args = args
        self._screen_buffer = None
        self._color_back = sdl2.ext.color.convert_to_color(args.back_color)
        self._color_fore = sdl2.ext.color.convert_to_color(args.fore_color)

    def _fill_screen_buffer(self, pixels):
        self._prev_screen_buffer = self._screen_buffer
        self._screen_buffer = pixels

    def _blit_screen(self, window):
        if not self._screen_buffer:
            return

        surface = window.get_surface()
        sdl2.ext.draw.fill(surface, self._color_back)

        for i in range(chipped8.SCREEN_HEIGHT):
            for j in range(chipped8.SCREEN_WIDTH):
                idx = i * chipped8.SCREEN_WIDTH + j
                if self._screen_buffer[idx]:
                    sdl2.ext.draw.fill(surface, self._color_fore, (j*self._args.scaling_factor, i*self._args.scaling_factor, self._args.scaling_factor, self._args.scaling_factor))

        window.refresh()

    def _beep(self):
        #os.system("echo -ne '\007'")
        pass

    def run(self):
        cpu = chipped8.cpu.CPU(self._args.hz)
        cpu.set_blit_screen_cb(self._fill_screen_buffer)
        cpu.set_sound_cb(self._beep)

        with open(self._args.in_file, 'rb') as f:
            cpu.load_rom(f.read())

        window = sdl2.ext.Window('Chip-8: {0}'.format(os.path.basename(self._args.in_file)), size=(chipped8.SCREEN_WIDTH*self._args.scaling_factor, chipped8.SCREEN_HEIGHT*self._args.scaling_factor))
        window.show()

        running = True
        process = True
        while running:
            ns = time.perf_counter_ns()

            events = sdl2.ext.get_events()
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    running = False
                    break

                elif event.type == sdl2.SDL_WINDOWEVENT:
                    if event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_GAINED:
                        process = True
                    elif event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
                        process = False

                # keyboard key mapping
                #
                #  1 2 3 C  -> 1 2 3 4
                #  4 5 6 D  -> Q W E R
                #  7 8 9 E  -> A S D F
                #  A 0 B F  -> Z X C V
                #
                elif event.type == sdl2.SDL_KEYDOWN or event.type == sdl2.SDL_KEYUP:
                    state = chipped8.KeyState.down if event.type == sdl2.SDL_KEYDOWN else chipped8.KeyState.up
                    if event.key.keysym.sym == sdl2.SDLK_1:
                        cpu.set_key_state(chipped8.Keys.Key_1, state)
                    if event.key.keysym.sym == sdl2.SDLK_2:
                        cpu.set_key_state(chipped8.Keys.Key_2, state)
                    elif event.key.keysym.sym == sdl2.SDLK_3:
                        cpu.set_key_state(chipped8.Keys.Key_3, state)
                    elif event.key.keysym.sym == sdl2.SDLK_4:
                        cpu.set_key_state(chipped8.Keys.Key_C, state)
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        cpu.set_key_state(chipped8.Keys.Key_4, state)
                    elif event.key.keysym.sym == sdl2.SDLK_w:
                        cpu.set_key_state(chipped8.Keys.Key_5, state)
                    elif event.key.keysym.sym == sdl2.SDLK_e:
                        cpu.set_key_state(chipped8.Keys.Key_6, state)
                    elif event.key.keysym.sym == sdl2.SDLK_r:
                        cpu.set_key_state(chipped8.Keys.Key_D, state)
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        cpu.set_key_state(chipped8.Keys.Key_7, state)
                    elif event.key.keysym.sym == sdl2.SDLK_s:
                        cpu.set_key_state(chipped8.Keys.Key_8, state)
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        cpu.set_key_state(chipped8.Keys.Key_9, state)
                    elif event.key.keysym.sym == sdl2.SDLK_f:
                        cpu.set_key_state(chipped8.Keys.Key_E, state)
                    elif event.key.keysym.sym == sdl2.SDLK_z:
                        cpu.set_key_state(chipped8.Keys.Key_A, state)
                    elif event.key.keysym.sym == sdl2.SDLK_x:
                        cpu.set_key_state(chipped8.Keys.Key_0, state)
                    elif event.key.keysym.sym == sdl2.SDLK_c:
                        cpu.set_key_state(chipped8.Keys.Key_B, state)
                    elif event.key.keysym.sym == sdl2.SDLK_v:
                        cpu.set_key_state(chipped8.Keys.Key_F, state)

            if process:
                cpu.process_frame()
                self._blit_screen(window)

            wait_sec = (16666666 - (time.perf_counter_ns() - ns)) / 1000000000
            if wait_sec > 0:
                time.sleep(wait_sec)

