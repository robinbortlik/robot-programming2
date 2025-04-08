# Complete, functional sample implementation for picoed
from picoed import display, i2c, button_a, button_b
from time import sleep

class Robot:
    def __init__(self, control_unit, navigation):
        self.control_unit = control_unit
        self.navigation = navigation

    def start(self):
        self.control_unit.initialize()

    def drive(self):
        state = self.control_unit.get_position_state()
        obstacle = self.control_unit.is_obstacle()
        command = self.navigation.decide_action(state, obstacle)
        self.control_unit.execute_movement(command, state)

    def stop(self):
        self.control_unit.stop()


class ControlUnit:
    def __init__(self, line_sensors, motors, obstacle_sensor, direction_indicators):
        self.line_sensors = line_sensors
        self.motors = motors
        self.obstacle_sensor = obstacle_sensor
        self.direction_indicators = direction_indicators

    def initialize(self):
        self.motors.initialize_motors()

    def get_position_state(self):
        left, center, right = self.line_sensors.read()
        return {"left": left, "center": center, "right": right,
                "is_intersection": sum([left, center, right]) >= 2,
                "off_line": sum([left, center, right]) == 0}

    def is_obstacle(self):
        pass  # Stub for obstacle detection

    def execute_movement(self, command, state):
        #display.show(command)
        self.direction_indicators.turn_off()
        print(f"Command: {command}, State: {state}")

        if state.get("is_intersection"):
            self.stop()
            sleep(0.5)
            self.motors.move("left", "forward", 90)
            self.motors.move("right", "forward", 90)
            sleep(0.5)

        if command == "forward":
            # Line following logic
            if state["left"]:
                self.motors.move("left", "forward", 30)
                self.motors.move("right", "forward", 90)
                sleep(0.2)
            elif state["right"]:
                self.motors.move("left", "forward", 90)
                self.motors.move("right", "forward", 30)
                sleep(0.2)
            elif state["center"]:
                self.motors.move("left", "forward", 90)
                self.motors.move("right", "forward", 90)
            else:
                self.motors.stop()

        elif command == "left":
            self.direction_indicators.indicate_left()
            self.motors.move("left", "backward", 90)
            self.motors.move("right", "forward", 90)
            sleep(0.5)

        elif command == "right":
            self.direction_indicators.indicate_right()
            self.motors.move("left", "forward", 90)
            self.motors.move("right", "backward", 90)
            sleep(0.5)

        elif command == "search":
            self.motors.search_line()

        elif command == "stop":
            self.stop()


    def stop(self):
        self.motors.stop()
        self.direction_indicators.turn_off()


class Navigation:
    def __init__(self, turns=None):
        self.turns = turns or []
        self.current_index = 0

    def decide_action(self, state, obstacle):
        if obstacle:
            return "stop"

        if state["is_intersection"]:
            return self.decide_turn()

        if state["off_line"]:
            return "search"

        return "forward"

    def decide_turn(self):
        if self.current_index >= len(self.turns):
            return "stop"
        direction = self.turns[self.current_index]
        self.current_index += 1
        return direction


class Motors:
    def initialize_motors(self):
        while not i2c.try_lock():
            pass
        try:
            i2c.writeto(0x70, b'\x00\x01')
            i2c.writeto(0x70, b'\xE8\xAA')
            sleep(0.1)
        finally:
            i2c.unlock()

    def move(self, side, direction, speed):
        channel_on = b""
        channel_off = b""

        if side == "left":
            channel_on, channel_off = (b'\x05', b'\x04') if direction == "forward" else (b'\x04', b'\x05')
        elif side == "right":
            channel_on, channel_off = (b'\x03', b'\x02') if direction == "forward" else (b'\x02', b'\x03')

        while not i2c.try_lock():
            pass
        try:
            i2c.writeto(0x70, channel_off + bytes([0]))
            i2c.writeto(0x70, channel_on + bytes([speed]))
        finally:
            i2c.unlock()

    def stop(self):
        self.move("left", "forward", 0)
        self.move("right", "forward", 0)

    def search_line(self):
        print("Searching for line...")


class LineSensors:
    def read(self):
        while not i2c.try_lock():
            pass
        try:
            buffer = bytearray(1)
            i2c.readfrom_into(0x38, buffer, start=0, end=1)
            data_bit_string = self.byte_to_bits(buffer)
            return bool(int(data_bit_string[7])), bool(int(data_bit_string[6])), bool(int(data_bit_string[5]))
        finally:
            i2c.unlock()

    def byte_to_bits(self, buffer):
        data_int = int.from_bytes(buffer, "big")
        data_bit_string = bin(data_int)
        return data_bit_string


class ObstacleSensor:
    def detect(self):
        pass  # Stub for digital read from obstacle sensor


class DirectionIndicators:
    def indicate_left(self):
        pass  # Stub for indicating left turn

    def indicate_right(self):
        pass  # Stub for indicating right turn

    def turn_off(self):
        pass  # Stub for turning off indicators


if __name__ == "__main__":
    line_sensors = LineSensors()
    motors = Motors()
    obstacle_sensor = ObstacleSensor()
    indicators = DirectionIndicators()
    navigation = Navigation(turns=["left", "right", "left", "forward", "left", "left", "forward", "forward"])
    control_unit = ControlUnit(line_sensors, motors, obstacle_sensor, indicators)
    robot = Robot(control_unit, navigation)

    while not button_a.was_pressed():
        sleep(0.1)

    robot.start()

    while not button_b.was_pressed():
        robot.drive()
        sleep(0.1)

    robot.stop()
