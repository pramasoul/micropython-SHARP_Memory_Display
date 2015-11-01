# FIXME: VCOM switching 


from pyb import Pin, SPI, udelay, rng, Timer

class SharpMemDisplay:
    def __init__(self, chan, cs, xdim, ydim):
        self.spi = SPI(chan, SPI.MASTER, baudrate=1000000, polarity=0, phase=0, firstbit=SPI.LSB)
        self.xdim = xdim
        self.ydim = ydim

        # VCOM must alternate at 0.5Hz to 30Hz to prevent damage to the LCD
        # We use a hardware timer to make it more resistant to software failure
        # As written this uses timer 11, and pin Y4. We send the "Frame Inversion Flag",
        # aka VCOM, in every serial transmission
        self.vcom = 2
        def toggle_vcom(l):
            self.vcom ^= 2
        self.timer = t = Timer(11)
        self.timer_ch = t.channel(1, Timer.OC_TOGGLE)
        # To drive EXTCOMIN (terminal 4) on display:
        self.extcom = Pin(Pin.board.Y4, mode=Pin.AF_PP, af=Pin.AF3_TIM11)
        t.callback(toggle_vcom) # For if we don't use hardware VCOM
        t.init(freq=2)          # with OC_TOGGLE results in output at 1Hz

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
        vcom = self.vcom
        syncing = True
        while syncing:
            try:
                ix = changed.pop()
            except KeyError:
                syncing = False
            else:
                set_cs(1)
                usleep(6)          # tsSCS
                send(1 | vcom)
                send(ix+1)
                send(lines[ix])
                send(0)
                usleep(2)          # thSCS
                set_cs(0)
                usleep(2)          # thSCSL

    def setup_hardware_vcom(self):
        def toggle_vcom(l):
            self.vcom ^= 2
        self.timer = t = Timer(11)
        self.timer_ch = t.channel(1, Timer.OC_TOGGLE, pin=Pin.board.Y4)
        t.callback(toggle_vcom) # For if we don't use hardware VCOM
        t.init(freq=2)          # with OC_TOGGLE results in output at 1Hz


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
