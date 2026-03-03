"""Arduino IoT and hardware management module.

Provides:
- Sketch compilation and upload
- Serial communication
- Firmata protocol integration
- Remote pin control
- Sensor data collection
- Automated deployment
- Multi-board support
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class ArduinoModule(Module):
    """Arduino IoT and hardware management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "upload_sketch")

        if action == "install_cli":
            return await self._install_cli(connector, kwargs)
        elif action == "upload_sketch":
            return await self._upload_sketch(connector, kwargs)
        elif action == "compile_sketch":
            return await self._compile_sketch(connector, kwargs)
        elif action == "serial_monitor":
            return await self._serial_monitor(connector, kwargs)
        elif action == "send_serial":
            return await self._send_serial(connector, kwargs)
        elif action == "setup_firmata":
            return await self._setup_firmata(connector, kwargs)
        elif action == "control_pin":
            return await self._control_pin_firmata(connector, kwargs)
        elif action == "read_sensor":
            return await self._read_sensor_firmata(connector, kwargs)
        elif action == "list_boards":
            return await self._list_boards(connector, kwargs)
        elif action == "install_library":
            return await self._install_library(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown Arduino action: {action}",
            )

    async def _install_cli(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Install Arduino CLI."""
        # Download and install Arduino CLI
        version = params.get("version", "0.35.2")

        commands = [
            f"wget https://github.com/arduino/arduino-cli/releases/download/{version}/arduino-cli_{version}_Linux_64bit.tar.gz",
            f"tar -xzf arduino-cli_{version}_Linux_64bit.tar.gz",
            "mv arduino-cli /usr/local/bin/",
            "chmod +x /usr/local/bin/arduino-cli",
            "arduino-cli config init",
            "arduino-cli core update-index",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success and "wget" in cmd:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message="Failed to install Arduino CLI",
                    details={"error": result.stderr},
                )

        # Install common cores
        await connector.run_command("arduino-cli core install arduino:avr", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Arduino CLI {version} installed",
            details={"version": version},
        )

    async def _upload_sketch(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Upload sketch to Arduino board."""
        sketch_path = params.get("sketch_path", "")
        board = params.get("board", "arduino:avr:uno")
        port = params.get("port", "/dev/ttyACM0")

        if not sketch_path:
            return ModuleResult(
                changed=False,
                success=False,
                message="Sketch path is required",
            )

        # Compile sketch
        compile_result = await connector.run_command(
            f"arduino-cli compile --fqbn {board} {sketch_path}",
            sudo=True,
        )

        if not compile_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Sketch compilation failed",
                details={"error": compile_result.stderr},
            )

        # Upload to board
        upload_result = await connector.run_command(
            f"arduino-cli upload -p {port} --fqbn {board} {sketch_path}",
            sudo=True,
        )

        if upload_result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Sketch uploaded to {board}",
                details={
                    "board": board,
                    "port": port,
                    "sketch": sketch_path,
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Upload failed",
                details={"error": upload_result.stderr},
            )

    async def _compile_sketch(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Compile Arduino sketch without uploading."""
        sketch_path = params.get("sketch_path", "")
        board = params.get("board", "arduino:avr:uno")
        output_dir = params.get("output_dir", "/tmp/arduino-build")

        cmd = f"arduino-cli compile --fqbn {board} --output-dir {output_dir} {sketch_path}"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message="Sketch compiled successfully",
                details={"output_dir": output_dir, "board": board},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Compilation failed",
                details={"error": result.stderr},
            )

    async def _serial_monitor(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Read from serial monitor."""
        port = params.get("port", "/dev/ttyACM0")
        baud = params.get("baud", "9600")
        duration = params.get("duration", "5")

        # Use screen or pyserial to read serial data
        cmd = f"timeout {duration}s arduino-cli monitor -p {port} -c baudrate={baud} || true"
        result = await connector.run_command(cmd, sudo=True)

        return ModuleResult(
            changed=False,
            success=True,
            message=f"Serial data from {port}",
            details={"port": port, "baud": baud, "data": result.stdout},
        )

    async def _send_serial(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Send data to Arduino via serial."""
        port = params.get("port", "/dev/ttyACM0")
        baud = params.get("baud", "9600")
        data = params.get("data", "")

        # Use Python to send serial data
        serial_script = f"""
import serial
import time

ser = serial.Serial('{port}', {baud}, timeout=1)
time.sleep(2)  # Wait for Arduino to reset
ser.write(b'{data}\\n')
ser.close()
print('Data sent: {data}')
"""

        # Install pyserial if needed
        await connector.run_command("pip3 install pyserial", sudo=True)

        # Write and execute script
        await connector.run_command(
            f"cat > /tmp/serial_send.py << 'EOL'\n{serial_script}\nEOL",
            sudo=True,
        )

        result = await connector.run_command("python3 /tmp/serial_send.py", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Data sent to {port}",
                details={"port": port, "data": data},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Failed to send serial data",
                details={"error": result.stderr},
            )

    async def _setup_firmata(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Upload StandardFirmata sketch to Arduino."""
        port = params.get("port", "/dev/ttyACM0")
        board = params.get("board", "arduino:avr:uno")

        # Create StandardFirmata sketch
        firmata_sketch = """
// StandardFirmata for SimpleInfra
#include <Firmata.h>

void setup() {
  Firmata.setFirmwareVersion(FIRMATA_FIRMWARE_MAJOR_VERSION, FIRMATA_FIRMWARE_MINOR_VERSION);
  Firmata.attach(ANALOG_MESSAGE, analogWriteCallback);
  Firmata.attach(DIGITAL_MESSAGE, digitalWriteCallback);
  Firmata.attach(REPORT_ANALOG, reportAnalogCallback);
  Firmata.attach(REPORT_DIGITAL, reportDigitalCallback);
  Firmata.attach(SET_PIN_MODE, setPinModeCallback);
  Firmata.begin(57600);
}

void loop() {
  while(Firmata.available()) {
    Firmata.processInput();
  }
}

void analogWriteCallback(byte pin, int value) {
  analogWrite(pin, value);
}

void digitalWriteCallback(byte port, int value) {
  for (byte i = 0; i < 8; i++) {
    byte pinValue = (value >> i) & 0x01;
    if (pinValue)
      digitalWrite(i + port * 8, HIGH);
    else
      digitalWrite(i + port * 8, LOW);
  }
}

void reportAnalogCallback(byte pin, int value) {
  if (value == 0) {
    Firmata.setPinMode(pin, OUTPUT);
  } else {
    Firmata.setPinMode(pin, INPUT);
  }
}

void reportDigitalCallback(byte port, int value) {
}

void setPinModeCallback(byte pin, int mode) {
  Firmata.setPinMode(pin, mode);
}
"""

        # Create sketch directory
        sketch_dir = "/tmp/StandardFirmata"
        await connector.run_command(f"mkdir -p {sketch_dir}", sudo=True)

        # Write sketch
        await connector.run_command(
            f"cat > {sketch_dir}/StandardFirmata.ino << 'EOL'\n{firmata_sketch}\nEOL",
            sudo=True,
        )

        # Upload
        compile_cmd = f"arduino-cli compile --fqbn {board} {sketch_dir}"
        upload_cmd = f"arduino-cli upload -p {port} --fqbn {board} {sketch_dir}"

        compile_result = await connector.run_command(compile_cmd, sudo=True)
        if not compile_result.success:
            return ModuleResult(
                changed=False,
                success=False,
                message="Firmata compilation failed",
                details={"error": compile_result.stderr},
            )

        upload_result = await connector.run_command(upload_cmd, sudo=True)

        if upload_result.success:
            # Install PyFirmata for control
            await connector.run_command("pip3 install pyfirmata", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message="StandardFirmata uploaded successfully",
                details={"port": port, "board": board},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Firmata upload failed",
                details={"error": upload_result.stderr},
            )

    async def _control_pin_firmata(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Control Arduino pin via Firmata protocol."""
        port = params.get("port", "/dev/ttyACM0")
        pin = params.get("pin", "13")
        value = params.get("value", "1")  # 0 or 1 for digital, 0-255 for PWM
        mode = params.get("mode", "digital")  # digital or pwm

        control_script = f"""
from pyfirmata import Arduino, util
import time

board = Arduino('{port}')
pin = {pin}

if '{mode}' == 'digital':
    board.digital[pin].write({value})
    print(f'Digital pin {{pin}} set to {value}')
elif '{mode}' == 'pwm':
    board.digital[pin].mode = 3  # PWM mode
    board.digital[pin].write({float(value) / 255.0})
    print(f'PWM pin {{pin}} set to {value}')

time.sleep(0.1)
board.exit()
"""

        await connector.run_command(
            f"cat > /tmp/firmata_control.py << 'EOL'\n{control_script}\nEOL",
            sudo=True,
        )

        result = await connector.run_command("python3 /tmp/firmata_control.py", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Pin {pin} controlled via Firmata",
                details={"pin": pin, "value": value, "mode": mode},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Pin control failed",
                details={"error": result.stderr},
            )

    async def _read_sensor_firmata(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Read sensor data via Firmata."""
        port = params.get("port", "/dev/ttyACM0")
        pin = params.get("pin", "A0")
        samples = params.get("samples", "10")

        read_script = f"""
from pyfirmata import Arduino, util
import time

board = Arduino('{port}')
it = util.Iterator(board)
it.start()

if '{pin}'.startswith('A'):
    pin_num = int('{pin}'[1:])
    sensor = board.analog[pin_num]
    sensor.enable_reporting()
    time.sleep(1)  # Wait for stable readings

    readings = []
    for i in range({samples}):
        value = sensor.read()
        if value is not None:
            readings.append(value)
        time.sleep(0.1)

    if readings:
        avg = sum(readings) / len(readings)
        print(f'Average reading from {pin}: {{avg:.3f}}')
        print(f'Raw values: {{readings}}')
    else:
        print('No readings obtained')
else:
    # Digital read
    pin_num = int('{pin}')
    value = board.digital[pin_num].read()
    print(f'Digital read from pin {{pin_num}}: {{value}}')

board.exit()
"""

        await connector.run_command(
            f"cat > /tmp/firmata_read.py << 'EOL'\n{read_script}\nEOL",
            sudo=True,
        )

        result = await connector.run_command("python3 /tmp/firmata_read.py", sudo=True)

        return ModuleResult(
            changed=False,
            success=result.success,
            message=f"Sensor reading from {pin}",
            details={"pin": pin, "reading": result.stdout},
        )

    async def _list_boards(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """List connected Arduino boards."""
        result = await connector.run_command("arduino-cli board list", sudo=True)

        return ModuleResult(
            changed=False,
            success=result.success,
            message="Connected boards listed",
            details={"boards": result.stdout},
        )

    async def _install_library(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Install Arduino library."""
        library = params.get("library", "")

        if not library:
            return ModuleResult(
                changed=False,
                success=False,
                message="Library name is required",
            )

        result = await connector.run_command(f"arduino-cli lib install '{library}'", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Library '{library}' installed",
                details={"library": library},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Library installation failed",
                details={"error": result.stderr},
            )
