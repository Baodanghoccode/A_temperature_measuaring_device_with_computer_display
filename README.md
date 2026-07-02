## 📖 Project Overview

This project features an embedded system based on the ATmega16 microcontroller that measures ambient temperature in real time and automatically regulates a cooling fan's speed in response. The system reads temperature from a DS18B20 digital sensor over the 1-Wire protocol, drives a DC cooling fan through PWM via an L298N motor driver, and streams live readings over UART to a custom Python/Tkinter desktop GUI for remote monitoring.The system demonstrates core embedded engineering techniques, including 1-Wire communication, Timer-based PWM generation, and multi-threaded serial communication between firmware and a host application.

Academic Context:
- Course: Microprocessors and Microcontrollers 
- Institution: VNU University of Engineering and Technology (UET)

⚙️ System Architecture

![Proteus schematic](docs/proteus-schematic.jpg)

1. Processing Unit: ATmega16 (8 MHz) reads sensor data and executes control logic.
2. Sensor: DS18B20 digital temperature sensor communicates over a single-wire (1-Wire).
3. Actuators: Timer0 generates a Fast-PWM signal, fed into an L298N H-bridge driver that controls a 5010 brushless DC cooling fan.
4. Status Indication: Three LEDs (green/yellow/red) on PC0–PC2 indicate the current temperature band.
5. Host Communication: UART (9600 baud) streams a PC, where a Python GUI parses and displays them live.


🛠 Hardware Specifications

| Component     | Specification                           | Function                                   |
| ------------- | --------------------------------------- | ------------------------------------------ |
|   MCU         | ATmega16                                | Central processing unit                    |
|   Sensor      | DS18B20 (1-Wire)                        | Temperature acquisition                    |
|   Driver      | L298N Dual H-Bridge                     | PWM-based fan speed control                |
|   Actuator    | 5010 Brushless DC Fan (50×50×10mm)      | Active cooling                             |
|   Indicators  | 3x LED (Green/Yellow/Red) + 100Ω resistors | Local temperature-band status           |
|   Interface   | USB-to-UART module                      | Serial link to host PC                     |
|   Power       | 3x 18650 Li-ion                         | Power                                      |

🚀 Key Features

1. Real-Time Temperature Monitoring
Reads 12-bit resolution temperature data (0.0625°C step) from the DS18B20 every 500ms via manually implemented 1-Wire reset/read/write timing.

2. Threshold-Based Fan & LED Control
Fan speed (PWM duty cycle) and LED status are switched across three temperature bands:
| Temperature | LED    | PWM (OCR0) |
| ----------- | ------ | ---------- |
| < 25 °C     | Green  | 0 (off)    |
| 25–30 °C    | Green  | 150        |
| 30–40 °C    | Yellow | 200        |
| ≥ 40 °C     | Red    | 250 (max)  |

3. Live Desktop Monitoring GUI
A multi-threaded Python/Tkinter application connects to the UART stream, parses incoming temperature values with regex, and renders them in a color-coded live terminal view — without blocking the UI thread.

* Desktop GUI

Requires Python 3.8+ and PySerial. Select the COM port of your USB-to-UART module, set the baud rate to 9600, then click 'CONNECT' to start streaming live temperature data.

---
📂 Repository Structure

├── main.c                     # ATmega16 firmware 
├── gui.py                     # Python desktop 
├── docs/            
│   ├── proteus-schematic.jpg  # Circuit diagram (Proteus)
│   └── real-product.jpg       # Assembled hardware
└── README.md                  # Project documentation 
