# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Pavel Perina
# https://www.pavelp.cz/posts/eng-raspberry-pico-st7567-display/
# MicroPython Sitronix ST7567 128*64 LCD driver
#
# Based on https://www.alldatasheet.com/view.jsp?Searchword=St7567 on some source
# code found on github. Written mostly to avoid GPL licensed code.
# You may need to set electronic volume (contrast) and regulator ratio to drive your
# screen properly.
#
# NOTES:
#
#  * With flipX=True, flipY=False framebuffer start is off by 4 pixels because
#    display memory has 132 columns according to driver datasheet, but display
#    itself has 128 pixels.
#  * One flip is always needed for valid orientation.
#  * Some drivers have staged init issuing several 0x28 commands with 50ms delay.
#  * Display memory has 8 pages, each having 8 lines, each having 8 pixels.
#    so framebuffer is actually 132x512 pixels (64 lines) and allows scrolling by
#    selecting start line.

import time

class ST7567():
    def __init__(self, spi, dc, cs=None, rst=None, contrast=0x00, flipX=False, flipY=True):
        
        dc.init(dc.OUT, value=0)
        self.dc=dc

        if(cs is not None):
            cs.init(cs.OUT, value = 1)      #disable device port
            self.cs=cs

        if(rst is not None):
            rst.init(rst.OUT, value = 0)    #reset device
            self.rst = rst
            time.sleep_ms(1)
            self.rst.value(1)
            time.sleep_ms(1)

        self.spi=spi

        initCommands=[
            0xE2,                           # Software reset
            0xA2|0x01,                      # LCD bias 0:1/9 1:1/7
            0x81,                           # Electronic volume (contrast) mode
            (contrast&0x3f),                # Contrast: 0x00-0x3F (default 0x1F - 0:white screen - 0x3F:black screen)
            0x20|0x03,                      # Voltage regulator ratio: 0x00-0x07 (3.0-6.5V)
            0x28|0x07,                      # Power control: booster+regulator+follower all on
            0xA0|(0x01 if flipX else 0x00), # Segment direction: 0=normal, 1=reversed (flip X)
            0xC0|(0x08 if flipY else 0x00), # Common output direction: 0=normal, 8=reversed (flip Y)
            0x40|0x00,                      # Display start line: 0x40-0x7F (line 0-63)
            0xAE|0x01,                      # Display on/off, 0=off,1=on
        ]

        self.writeCommands(initCommands)

    # Write command(s)
    def writeCommands(self, cmd):
        self.cs.value(0)    # Enable device
        self.dc.value(0)    # Command mode
        self.spi.write(bytearray(cmd))
        self.dc.value(1)    # Disable device 
    
    # Write framebuffer data
    def writeData(self, data):
        self.cs.value(0)
        self.dc.value(1)    # Display data mode
        self.spi.write(data)
        self.dc.value(1)

    # Show framebuffer
    def show(self, buffer):
        self.writeCommands([0x40|0x00])  # Set start line to 0
        for page in range(8):
            self.writeCommands([
                0xB0 | page,    # Set page address (0-7)
                0x10 | 0x00,    # Set column address high nibble
                0x00 | 0x00,    # Set column address low  nibble
            ])
            # Write pages data (8 rows, 128 columns)
            self.writeData(buffer[(128*page):(128*page+128)])
