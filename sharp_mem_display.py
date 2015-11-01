# The MIT License (MIT)
#
# Copyright (c) 2015 Tom Soulanille
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


from pyb import Pin, SPI, udelay, rng, Timer
import pyb                      # DEBUG

class HardwareVCOM:
    def __init__(self):
        # VCOM must alternate at 0.5Hz to 30Hz to prevent damage to
        # the LCD We use a hardware timer to make it more resistant to
        # software failure. Once the timer is set up and driving the
        # EXTCOMIN input to the display, we have the necessary
        # hardware signal even if the code crashes (as long as we
        # don't cause a deinit of the timer).  As written this uses
        # timer 11, and pin Y4. We send the "Frame Inversion Flag",
        # aka VCOM, in every serial transmission, so you can also
        # maintain the necessary alternation of VCOM without
        # connecting EXTCOMIN, as long as you sync() the display at
        # least once every period of the timer (every 500ms as
        # written), and don't crash.
        self.vcom = 2
        def toggle_vcom(l):
            self.vcom ^= 2
            pyb.LED(2).toggle() # DEBUG
        self.timer = t = Timer(11)
        # drive the hardware EXTCOMIN (terminal 4 on display):
        self.timer_ch = t.channel(1, Timer.OC_TOGGLE, pin=Pin.board.Y4)
        t.callback(toggle_vcom) # For if we don't use hardware VCOM
        t.init(freq=2)          # with OC_TOGGLE results in output at 1Hz


_hw_vcom = HardwareVCOM()       # Create the singleton immediately
def get_vcom():
    global _hw_vcom
    return _hw_vcom.vcom


class SharpMemDisplay:
    def __init__(self, chan, cs, xdim, ydim):
        self.spi = SPI(chan, SPI.MASTER, baudrate=1000000, polarity=0, phase=0, firstbit=SPI.LSB)
        self.xdim = xdim
        self.ydim = ydim
        if not isinstance(cs, Pin):
            cs = Pin(cs)
        cs.value(0)
        cs.init(Pin.OUT_PP)
        self.cs = cs
        self.usleep = udelay
        self.lines = [bytearray(xdim//8) for i in range(ydim)]
        self.changed = set()

    def clear(self):
        self.set_all(0 for i in range(self.xdim * self.ydim // 8))

    def get_pix(self, x, y):
        return bool(self.lines[y][x//8] & (1 << x%8))

    def set_pix(self, x, y, v):
        byte = x//8
        bitmask = 1 << x%8
        linebuf = self.lines[y]
        linebuf[byte] &= ~bitmask
        if v:
            linebuf[byte] |= bitmask
        self.changed.add(y)

    def set_line(self, line_ix, values):
        b = self.lines[line_ix]
        for i, v in enumerate(values):
            b[i] = v
        self.changed.add(line_ix)

    def set_all(self, values):
        lines = self.lines
        vi = iter(values)
        xbytes = self.xdim // 8
        for ix in range(len(self.lines)):
            b = lines[ix]
            for i, v in zip(range(xbytes), vi):
                b[i] = v
            self.changed.add(ix)

    def sync(self):
        lines = self.lines
        changed = self.changed
        usleep = self.usleep
        send = self.spi.send
        set_cs = self.cs.value
        vcom = get_vcom()
        syncing = True
        while syncing:
            set_cs(1)
            usleep(6)          # tsSCS
            try:
                ix = changed.pop()
            except KeyError:
                syncing = False
                send(0 | vcom)
            else:
                send(1 | vcom)
                send(ix+1)
                send(lines[ix])
            send(0)
            usleep(2)          # thSCS
            set_cs(0)
            usleep(2)          # thSCSL


# A little demo: Brownian motion.
def brown(screen):
    screen.clear()
    xdim = screen.xdim
    ydim = screen.ydim
    x = xdim // 2
    y = ydim // 2
    mls = 255 * xdim // 8
    on = True
    while True:
        if on:
            on = any(sum(line) < mls for line in screen.lines)
        else:
            on = all(sum(line) == 0 for line in screen.lines)
        for i in range(1000):
            x = (x + rng()%3 - 1) % xdim
            y = (y + rng()%3 - 1) % ydim
            screen.set_pix(x, y, on)
            screen.sync()
