"""Raspberry Pi IoT and hardware management module.

Provides:
- GPIO pin control and automation
- Hardware interfaces (I2C, SPI, UART)
- Camera module integration
- Sensor reading (temperature, humidity, motion, etc.)
- Display control (LCD, OLED)
- IoT gateway configuration
- Kiosk mode setup
- Performance tuning (overclocking)
- Home automation features
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class RaspberryPiModule(Module):
    """Raspberry Pi IoT and hardware management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "setup_gpio")

        if action == "setup_gpio":
            return await self._setup_gpio(connector, kwargs)
        elif action == "control_pin":
            return await self._control_pin(connector, kwargs)
        elif action == "read_sensor":
            return await self._read_sensor(connector, kwargs)
        elif action == "setup_camera":
            return await self._setup_camera(connector, kwargs)
        elif action == "capture_image":
            return await self._capture_image(connector, kwargs)
        elif action == "enable_interface":
            return await self._enable_interface(connector, kwargs)
        elif action == "setup_kiosk":
            return await self._setup_kiosk(connector, kwargs)
        elif action == "setup_iot_gateway":
            return await self._setup_iot_gateway(connector, kwargs)
        elif action == "monitor_system":
            return await self._monitor_system(connector, kwargs)
        elif action == "overclock":
            return await self._overclock(connector, kwargs)
        elif action == "control_display":
            return await self._control_display(connector, kwargs)
        elif action == "setup_automation":
            return await self._setup_automation(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown Raspberry Pi action: {action}",
            )

    async def _setup_gpio(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup GPIO library and permissions."""
        # Install RPi.GPIO or pigpio
        library = params.get("library", "RPi.GPIO")

        if library == "RPi.GPIO":
            install_cmd = "pip3 install RPi.GPIO"
        elif library == "pigpio":
            install_cmd = "apt-get install -y pigpio python3-pigpio && systemctl enable pigpiod && systemctl start pigpiod"
        elif library == "gpiozero":
            install_cmd = "pip3 install gpiozero"
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported GPIO library: {library}",
            )

        result = await connector.run_command(install_cmd, sudo=True)

        if result.success:
            # Add user to gpio group
            user = params.get("user", "pi")
            await connector.run_command(f"usermod -a -G gpio {user}", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"GPIO setup complete with {library}",
                details={"library": library, "user": user},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="GPIO setup failed",
                details={"error": result.stderr},
            )

    async def _control_pin(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Control GPIO pin."""
        pin = params.get("pin", "")
        state = params.get("state", "high")  # high/low/toggle
        mode = params.get("mode", "out")  # in/out/pwm

        if not pin:
            return ModuleResult(
                changed=False,
                success=False,
                message="Pin number required",
            )

        # Create Python script to control pin
        gpio_script = f"""
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin = {pin}

if "{mode}" == "out":
    GPIO.setup(pin, GPIO.OUT)
    if "{state}" == "high":
        GPIO.output(pin, GPIO.HIGH)
        print(f"Pin {{pin}} set to HIGH")
    elif "{state}" == "low":
        GPIO.output(pin, GPIO.LOW)
        print(f"Pin {{pin}} set to LOW")
    elif "{state}" == "toggle":
        current = GPIO.input(pin)
        GPIO.output(pin, not current)
        print(f"Pin {{pin}} toggled")
elif "{mode}" == "in":
    GPIO.setup(pin, GPIO.IN)
    value = GPIO.input(pin)
    print(f"Pin {{pin}} reading: {{value}}")
elif "{mode}" == "pwm":
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 1000)  # 1kHz
    duty_cycle = {params.get('duty_cycle', 50)}
    pwm.start(duty_cycle)
    time.sleep(0.1)
    pwm.stop()
    print(f"PWM on pin {{pin}} at {{duty_cycle}}%")

GPIO.cleanup(pin)
"""

        # Write and execute script
        await connector.run_command(
            f"cat > /tmp/gpio_control.py << 'EOL'\n{gpio_script}\nEOL",
            sudo=True,
        )

        result = await connector.run_command("python3 /tmp/gpio_control.py", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Pin {pin} controlled: {state}",
                details={"pin": pin, "state": state, "mode": mode, "output": result.stdout},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Pin control failed",
                details={"error": result.stderr},
            )

    async def _read_sensor(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Read from sensor."""
        sensor_type = params.get("sensor_type", "")
        pin = params.get("pin", "")

        sensors = {
            "dht22": "pip3 install Adafruit_DHT",
            "bme280": "pip3 install smbus2 bme280",
            "ds18b20": "",  # Uses 1-wire, no install needed
            "pir": "",  # Motion sensor, simple GPIO
            "ultrasonic": "",  # HC-SR04, uses GPIO
        }

        if sensor_type not in sensors:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported sensor: {sensor_type}",
            )

        # Install sensor library if needed
        if sensors[sensor_type]:
            await connector.run_command(sensors[sensor_type], sudo=True)

        # Read based on sensor type
        if sensor_type == "dht22":
            script = f"""
import Adafruit_DHT
sensor = Adafruit_DHT.DHT22
pin = {pin}
humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
if humidity is not None and temperature is not None:
    print(f"Temperature={{temperature:.1f}}C Humidity={{humidity:.1f}}%")
else:
    print("Failed to read sensor")
"""
        elif sensor_type == "pir":
            script = f"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup({pin}, GPIO.IN)
motion = GPIO.input({pin})
print(f"Motion detected: {{bool(motion)}}")
GPIO.cleanup()
"""
        elif sensor_type == "ds18b20":
            # Temperature sensor using 1-wire
            device_file = params.get("device_file", "/sys/bus/w1/devices/28-*/w1_slave")
            script = f"""
import glob
device_file = glob.glob("{device_file}")[0]
with open(device_file, 'r') as f:
    lines = f.readlines()
temp_str = lines[1].split('t=')[1]
temp = float(temp_str) / 1000.0
print(f"Temperature={{temp:.1f}}C")
"""
        else:
            script = "print('Sensor reading not implemented')"

        await connector.run_command(f"cat > /tmp/sensor_read.py << 'EOL'\n{script}\nEOL", sudo=True)
        result = await connector.run_command("python3 /tmp/sensor_read.py", sudo=True)

        return ModuleResult(
            changed=False,
            success=result.success,
            message=f"Sensor {sensor_type} read",
            details={"sensor_type": sensor_type, "reading": result.stdout.strip()},
        )

    async def _setup_camera(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup Raspberry Pi camera."""
        # Enable camera interface
        await connector.run_command(
            "raspi-config nonint do_camera 0",  # 0 = enable
            sudo=True,
        )

        # Install picamera2 (for Pi Camera V2/V3)
        install_cmd = "pip3 install picamera2"
        result = await connector.run_command(install_cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message="Camera setup complete",
                details={"note": "Reboot may be required for camera to work"},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Camera setup failed",
            )

    async def _capture_image(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Capture image from camera."""
        output = params.get("output", "/tmp/image.jpg")
        resolution = params.get("resolution", "1920x1080")
        rotation = params.get("rotation", "0")

        width, height = resolution.split("x")

        # Use libcamera-still (new method for Bullseye+)
        cmd = f"libcamera-still -o {output} --width {width} --height {height} --rotation {rotation}"

        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Image captured: {output}",
                details={"output": output, "resolution": resolution},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Image capture failed",
                details={"error": result.stderr},
            )

    async def _enable_interface(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Enable hardware interface (I2C, SPI, UART)."""
        interface = params.get("interface", "")

        interface_map = {
            "i2c": "raspi-config nonint do_i2c 0",
            "spi": "raspi-config nonint do_spi 0",
            "uart": "raspi-config nonint do_serial 0",
            "1-wire": "raspi-config nonint do_onewire 0",
        }

        if interface not in interface_map:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown interface: {interface}",
            )

        result = await connector.run_command(interface_map[interface], sudo=True)

        if result.success:
            # Install tools
            if interface == "i2c":
                await connector.run_command("apt-get install -y i2c-tools python3-smbus", sudo=True)
            elif interface == "spi":
                await connector.run_command("pip3 install spidev", sudo=True)

            return ModuleResult(
                changed=True,
                success=True,
                message=f"{interface.upper()} interface enabled",
                details={"interface": interface, "note": "Reboot may be required"},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to enable {interface}",
            )

    async def _setup_kiosk(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup kiosk mode (auto-start browser in fullscreen)."""
        url = params.get("url", "http://localhost")
        browser = params.get("browser", "chromium")

        # Install browser if needed
        if browser == "chromium":
            await connector.run_command("apt-get install -y chromium-browser unclutter", sudo=True)

        # Create autostart file
        autostart_content = f"""
[Desktop Entry]
Type=Application
Name=Kiosk
Exec={browser} --kiosk --noerrdialogs --disable-infobars --no-first-run {url}
X-GNOME-Autostart-enabled=true
"""

        await connector.run_command(
            "mkdir -p /home/pi/.config/autostart",
            sudo=True,
        )

        await connector.run_command(
            f"cat > /home/pi/.config/autostart/kiosk.desktop << 'EOL'\n{autostart_content}\nEOL",
            sudo=True,
        )

        # Disable screen blanking
        await connector.run_command(
            "echo '@xset s off' >> /home/pi/.config/lxsession/LXDE-pi/autostart",
            sudo=True,
        )
        await connector.run_command(
            "echo '@xset -dpms' >> /home/pi/.config/lxsession/LXDE-pi/autostart",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Kiosk mode configured for {url}",
            details={"url": url, "browser": browser},
        )

    async def _setup_iot_gateway(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup as IoT gateway (MQTT broker + Node-RED)."""
        install_mqtt = params.get("install_mqtt", "true") == "true"
        install_nodered = params.get("install_nodered", "true") == "true"

        if install_mqtt:
            # Install Mosquitto MQTT broker
            commands = [
                "apt-get install -y mosquitto mosquitto-clients",
                "systemctl enable mosquitto",
                "systemctl start mosquitto",
            ]

            for cmd in commands:
                await connector.run_command(cmd, sudo=True)

        if install_nodered:
            # Install Node-RED
            install_cmd = "bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered) --confirm-install --confirm-pi"
            await connector.run_command(install_cmd, sudo=True)

            # Enable Node-RED
            await connector.run_command("systemctl enable nodered", sudo=True)
            await connector.run_command("systemctl start nodered", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message="IoT gateway configured",
            details={
                "mqtt": "installed" if install_mqtt else "skipped",
                "nodered": "http://localhost:1880" if install_nodered else "skipped",
            },
        )

    async def _monitor_system(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Monitor Raspberry Pi system stats."""
        # Get temperature
        temp_result = await connector.run_command("vcgencmd measure_temp")
        temp = temp_result.stdout.strip() if temp_result.success else "unknown"

        # Get CPU frequency
        freq_result = await connector.run_command("vcgencmd measure_clock arm")
        freq = freq_result.stdout.strip() if freq_result.success else "unknown"

        # Get voltage
        volt_result = await connector.run_command("vcgencmd measure_volts")
        voltage = volt_result.stdout.strip() if volt_result.success else "unknown"

        # Get memory
        mem_result = await connector.run_command("free -h | grep Mem")
        memory = mem_result.stdout.strip() if mem_result.success else "unknown"

        return ModuleResult(
            changed=False,
            success=True,
            message="System stats collected",
            details={
                "temperature": temp,
                "cpu_frequency": freq,
                "voltage": voltage,
                "memory": memory,
            },
        )

    async def _overclock(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Configure overclocking settings."""
        arm_freq = params.get("arm_freq", "1500")  # MHz
        gpu_freq = params.get("gpu_freq", "500")
        over_voltage = params.get("over_voltage", "2")

        # Backup config
        await connector.run_command("cp /boot/config.txt /boot/config.txt.bak", sudo=True)

        # Add overclock settings
        overclock_config = f"""
# Overclock settings
arm_freq={arm_freq}
gpu_freq={gpu_freq}
over_voltage={over_voltage}
"""

        await connector.run_command(
            f"echo '{overclock_config}' >> /boot/config.txt",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Overclocking configured ({arm_freq}MHz)",
            details={
                "arm_freq": arm_freq,
                "gpu_freq": gpu_freq,
                "over_voltage": over_voltage,
                "note": "Reboot required for changes to take effect",
            },
        )

    async def _control_display(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Control display (HDMI, rotation, resolution)."""
        action = params.get("display_action", "rotate")

        if action == "rotate":
            rotation = params.get("rotation", "0")  # 0, 90, 180, 270
            rotation_map = {"0": "0", "90": "1", "180": "2", "270": "3"}

            await connector.run_command(
                f"echo 'display_rotate={rotation_map.get(rotation, \"0\")}' >> /boot/config.txt",
                sudo=True,
            )

        elif action == "off":
            await connector.run_command("vcgencmd display_power 0", sudo=True)

        elif action == "on":
            await connector.run_command("vcgencmd display_power 1", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Display {action} executed",
        )

    async def _setup_automation(
        self,
        connector: "Connector",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Setup home automation rule."""
        rule_name = params.get("rule_name", "automation")
        trigger_pin = params.get("trigger_pin", "")
        action_pin = params.get("action_pin", "")
        condition = params.get("condition", "high")

        automation_script = f"""#!/usr/bin/env python3
# SimpleInfra Home Automation Rule: {rule_name}
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TRIGGER_PIN = {trigger_pin}
ACTION_PIN = {action_pin}

GPIO.setup(TRIGGER_PIN, GPIO.IN)
GPIO.setup(ACTION_PIN, GPIO.OUT)

print(f"Automation '{rule_name}' running...")

try:
    while True:
        trigger_state = GPIO.input(TRIGGER_PIN)

        if "{condition}" == "high" and trigger_state == GPIO.HIGH:
            GPIO.output(ACTION_PIN, GPIO.HIGH)
            print(f"{{time.strftime('%Y-%m-%d %H:%M:%S')}}: Trigger activated, action ON")
        elif "{condition}" == "low" and trigger_state == GPIO.LOW:
            GPIO.output(ACTION_PIN, GPIO.HIGH)
            print(f"{{time.strftime('%Y-%m-%d %H:%M:%S')}}: Trigger activated, action ON")
        else:
            GPIO.output(ACTION_PIN, GPIO.LOW)

        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
"""

        script_path = f"/usr/local/bin/automation-{rule_name}.py"
        await connector.run_command(
            f"cat > {script_path} << 'EOL'\n{automation_script}\nEOL",
            sudo=True,
        )
        await connector.run_command(f"chmod +x {script_path}", sudo=True)

        # Create systemd service
        service_content = f"""
[Unit]
Description=Home Automation: {rule_name}
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 {script_path}
Restart=always

[Install]
WantedBy=multi-user.target
"""

        await connector.run_command(
            f"cat > /etc/systemd/system/automation-{rule_name}.service << 'EOL'\n{service_content}\nEOL",
            sudo=True,
        )

        await connector.run_command("systemctl daemon-reload", sudo=True)
        await connector.run_command(f"systemctl enable automation-{rule_name}", sudo=True)
        await connector.run_command(f"systemctl start automation-{rule_name}", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Automation rule '{rule_name}' configured",
            details={
                "rule_name": rule_name,
                "trigger_pin": trigger_pin,
                "action_pin": action_pin,
                "script": script_path,
            },
        )
