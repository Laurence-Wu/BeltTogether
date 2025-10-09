# Arduino Makefile for Uno R4 (Renesas RA4M1)

# Board configuration
BOARD = arduino:avr:mega
F_CPU = 48000000UL

# Port configuration - adjust COM port for your system
PORT = COM5
ARDUINO_CLI = arduino-cli

# Build targets
all: compile

compile:
	$(ARDUINO_CLI) compile --fqbn $(BOARD) .

# Flash to Arduino
flash: compile
	$(ARDUINO_CLI) upload --fqbn $(BOARD) --port $(PORT) .

# Clean build files
clean:
	$(ARDUINO_CLI) cache clean
	rm -rf build/
.PHONY: all flash clean