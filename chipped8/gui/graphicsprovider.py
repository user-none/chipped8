#!/usr/bin/env python

# Copyright 2025 John Schember <john@nachtimwald.com>
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

from pathlib import Path

from PySide6.QtGui import (
        QRhiTexture, QRhiSampler, QRhiShaderStage, QRhiGraphicsPipeline,
        QRhiShaderResourceBinding, QShader, QRhiVertexInputLayout,
        QRhiVertexInputBinding, QRhiVertexInputAttribute, QRhiBuffer, QImage,
        QColor, QRhiDepthStencilClearValue
)
from PySide6.QtWidgets import QRhiWidget
from PySide6.QtCore import Signal, Slot, QSize, Qt

import numpy as np
import chipped8

class GraphicsProvider(QRhiWidget):
    focusChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)

        self._texture = None
        self._sampler = None
        self._srb = None
        self._pipeline = None
        self._vertex_buffer = None
        self._initialized = False

        self._start_time = time.time()

        self._texture_size = QSize(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT)
        self._rbg_buffer = np.zeros((chipped8.SCREEN_HEIGHT, chipped8.SCREEN_WIDTH, 4), dtype=np.uint8)

        self.set_colors()

        # Shader options
        self.enable_scanlines = True
        self.enable_glow = True
        self.enable_barrel = True
        self.enable_chromatic = False
        self.enable_vignette = False
        self.enable_noise = True
        self.enable_flicker = True
        self.enable_quantize = False
        self.enable_interlace = False
        self.enable_mask = False
        self.enable_wrap = True
        self.enable_scan_delay = True
        self.enable_pixel_borders = True
        self.enable_edge_glow = False

    def initialize(self, _ = None):
        rhi = self.rhi()
        if not rhi:
            print('QRhi is not initialized')
            return

        self._texture = rhi.newTexture(QRhiTexture.RGBA8, self._texture_size, 1)
        self._texture.create()

        self._sampler = rhi.newSampler(
            QRhiSampler.Nearest, QRhiSampler.Nearest, QRhiSampler.None_,
            QRhiSampler.ClampToEdge, QRhiSampler.ClampToEdge
        )
        self._sampler.create()

        self._scale_buffer = rhi.newBuffer(QRhiBuffer.Dynamic, QRhiBuffer.UniformBuffer, 2 * 4)
        self._scale_buffer.create()
        self._frag_buffer = rhi.newBuffer(QRhiBuffer.Dynamic, QRhiBuffer.UniformBuffer, 80)
        self._frag_buffer.create()

        self._srb = rhi.newShaderResourceBindings()

        self._srb.setBindings([
            QRhiShaderResourceBinding.sampledTexture(
                0, QRhiShaderResourceBinding.FragmentStage, self._texture, self._sampler
            ),
            QRhiShaderResourceBinding.uniformBuffer(
                1, QRhiShaderResourceBinding.VertexStage, self._scale_buffer
            ),
            QRhiShaderResourceBinding.uniformBuffer(
                2, QRhiShaderResourceBinding.FragmentStage, self._frag_buffer
            )

        ])
        self._srb.create()

        # Load precompiled SPIR-V shaders
        vshader = self.load_shader(os.path.join(Path(__file__).parent, 'shaders', 'texture.vert.qsb'))
        fshader = self.load_shader(os.path.join(Path(__file__).parent, 'shaders', 'retro.frag.qsb'))

        input_layout = QRhiVertexInputLayout()
        binding = QRhiVertexInputBinding()
        binding.setStride(2 * 4)
        input_layout.setBindings([binding])
        input_layout.setAttributes([
            QRhiVertexInputAttribute(0, 0, QRhiVertexInputAttribute.Format.Float2, 0),
            QRhiVertexInputAttribute(0, 1, QRhiVertexInputAttribute.Format.Float3, 8)
        ])

        self._pipeline = rhi.newGraphicsPipeline()
        self._pipeline.setTopology(QRhiGraphicsPipeline.TriangleStrip)
        shader_stages = [
            QRhiShaderStage(QRhiShaderStage.Vertex, vshader),
            QRhiShaderStage(QRhiShaderStage.Fragment, fshader)
        ]
        self._pipeline.setShaderStages(shader_stages)
        self._pipeline.setVertexInputLayout(input_layout)
        self._pipeline.setShaderResourceBindings(self._srb)
        self._pipeline.setRenderPassDescriptor(self.renderTarget().renderPassDescriptor())
        self._pipeline.create()

        self._image = QImage(self._rbg_buffer.data, self._texture_size.width(), self._texture_size.height(), QImage.Format_RGBA8888)

        self._vertex_buffer = rhi.newBuffer(QRhiBuffer.Immutable, QRhiBuffer.VertexBuffer, 4 * 2 * 4)
        self._vertex_buffer.create()
        # Vertex data: 4 vertices, 2 floats each (x,y)
        quad_vertices = np.array([
            [-1.0, -1.0],
            [ 1.0, -1.0],
            [-1.0,  1.0],
            [ 1.0,  1.0]
        ], dtype=np.float32)

        # Upload vertex data using a resource update batch
        update_batch = rhi.nextResourceUpdateBatch()
        update_batch.uploadStaticBuffer(self._vertex_buffer, quad_vertices.tobytes())

        # Store update batch for submission later in render()
        self._vertex_data_update_batch = update_batch

        self._initialized = True

    def load_shader(self, qsb_path):
        try:
            with open(qsb_path, 'rb') as f:
                return QShader.fromSerialized(f.read())
        except Exception as e:
            raise RuntimeError(f'Failed to open shader file: {qsb_path} - {e}')
        raise Exception('Failed to load shaders')

    @Slot(np.ndarray)
    def blitScreen(self, pixel_indices: np.ndarray):
        self._rbg_buffer[:] = self._colors[pixel_indices]
        self.update()

    @Slot()
    def clearScreen(self):
        self._rbg_buffer.fill(0)
        self.update()

    @Slot()
    def update(self):
        if not self.isVisible():
            return
        super().update()

    def _hex_to_rgba(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return [r, g, b, 255]

    def set_colors(self, color_1='#0f052d', color_2='#203671', color_3='#36868f', color_4='#5fc75d'):
        self._colors = np.array([
            self._hex_to_rgba(color_1),
            self._hex_to_rgba(color_2),
            self._hex_to_rgba(color_3),
            self._hex_to_rgba(color_4)
        ], dtype=np.uint8)

    def get_colors(self):
        return [
            '#{:02x}{:02x}{:02x}'.format(r, g, b)
            for r, g, b in self._colors[:, :3]
        ]

    def toggle_effect_scanlines(self, val):
        self.enable_scanlines = val

    def toggle_effect_glow(self, val):
        self.enable_glow = val

    def toggle_effect_barrel(self, val):
        self.enable_barrel = val

    def toggle_effect_chromatic(self, val):
        self.enable_chromatic = val

    def toggle_effect_vignette(self, val):
        self.enable_vignette = val

    def toggle_effect_noise(self, val):
        self.enable_noise = val

    def toggle_effect_flicker(self, val):
        self.enable_flicker = val

    def toggle_effect_quantize(self, val):
        self.enable_quantize = val

    def toggle_effect_interlace(self, val):
        self.enable_interlace = val

    def toggle_effect_mask(self, val):
        self.enable_mask = val

    def toggle_effect_wrap(self, val):
        self.enable_wrap = val

    def toggle_effect_scan_delay(self, val):
        self.enable_scan_delay = val

    def toggle_effect_pixel_borders(self, val):
        self.enable_pixel_borders = val

    def toggle_effect_edge_glow(self, val):
        self.enable_edge_glow = val

    def focusInEvent(self, event):
        self.focusChanged.emit(True)

    def focusOutEvent(self, event):
        self.focusChanged.emit(False)

    def render(self, command_buffer):
        if not self._initialized:
            self.initialize()
            return

        if self._vertex_data_update_batch:
            command_buffer.resourceUpdate(self._vertex_data_update_batch)
            self._vertex_data_update_batch = None

        widget_aspect = self.width() / self.height()
        texture_aspect = self._texture_size.width() / self._texture_size.height()

        if widget_aspect > texture_aspect:
            scale_x = texture_aspect / widget_aspect
            scale_y = 1.0
        else:
            scale_x = 1.0
            scale_y = widget_aspect / texture_aspect

        # Aspect ratio scale (used by vertex shader)
        scale_data = np.array([scale_x, scale_y], dtype=np.float32).tobytes()

        # Time + resolution (used by fragment shader) + feature flags
        current_time = time.time() - self._start_time
        frag_data = np.array([
            current_time,
            0.0,
            self._texture_size.width(),
            self._texture_size.height(),
        ], dtype=np.float32).tobytes()

        flags = np.array([
                1 if self.enable_scanlines else 0,
                1 if self.enable_glow else 0,
                1 if self.enable_barrel else 0,
                1 if self.enable_chromatic else 0,
                1 if self.enable_vignette else 0,
                1 if self.enable_noise else 0,
                1 if self.enable_flicker else 0,
                1 if self.enable_quantize else 0,
                1 if self.enable_interlace else 0,
                1 if self.enable_mask else 0,
                1 if self.enable_wrap else 0,
                1 if self.enable_scan_delay else 0,
                1 if self.enable_pixel_borders else 0,
                1 if self.enable_edge_glow else 0,
            ], dtype=np.int32).tobytes()

        frag_data += flags
        frag_data += bytes(80 - len(frag_data))

        update_batch = self.rhi().nextResourceUpdateBatch()
        update_batch.updateDynamicBuffer(self._scale_buffer, 0, len(scale_data), scale_data)
        update_batch.updateDynamicBuffer(self._frag_buffer, 0, len(frag_data), frag_data)
        update_batch.uploadTexture(self._texture, self._image)

        command_buffer.resourceUpdate(update_batch)

        rt = self.renderTarget()
        if rt:
            # Begin rendering pass
            command_buffer.beginPass(rt, QColor(0, 0, 0, 255), QRhiDepthStencilClearValue())

            command_buffer.setGraphicsPipeline(self._pipeline)
            command_buffer.setVertexInput(0, [(self._vertex_buffer, 0)])
            command_buffer.setShaderResources(self._srb)
            command_buffer.draw(4)

            command_buffer.endPass()
