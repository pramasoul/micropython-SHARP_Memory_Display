# micropython-SHARP_Memory_Display
A [micropython] (http://micropython.org/) driver for [SHARP memory displays] (http://www.sharpmemorylcd.com/aboutmemorylcd.html), including the [SHARP Memory Display Breakout] (https://www.adafruit.com/products/1393) for the [LS013B4DN04] (http://www.sharpmemorylcd.com/1-35-inch-memory-lcd.html) ([application info] (http://www.sharpmemorylcd.com/resources/LS013B4DN04_Application_Info.pdf), [datasheet] (http://www.mouser.com/ds/2/365/LS013B4DN04(3V_FPC)-204284.pdf)) from [AdaFruit] (https://www.adafruit.com/) 

## Example
```python
from sharp_mem_display import SharpMemDisplay
screen = SharpMemDisplay(2, 'Y5', 96, 96)
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
```
