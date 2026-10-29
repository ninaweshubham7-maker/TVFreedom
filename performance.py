"""
Performance - Read-only performance measurements for TV Freedom.

This module provides performance measurement capabilities using
only read-only ADB operations.
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json
import time
import statistics
from datetime import datetime
from enum import Enum

from adb_manager import ADBManager, ADBState


class MeasurementType(Enum):
    """Types of performance measurements."""
    MEMORY = "memory"
    CPU = "cpu"
    STORAGE = "storage"
    NETWORK = "network"
    BOOT_TIME = "boot_time"
    APP_LAUNCH = "app_launch"
    UI_RESPONSIVENESS = "ui_responsiveness"
    BATTERY = "battery"
    THERMAL = "thermal"


@dataclass
class Measurement:
    """Single performance measurement."""
    measurement_id: str
    timestamp: float
    measurement_type: MeasurementType
    name: str
    value: float
    unit: str
    metadata: dict = field(default_factory=dict)
    device_serial: str = ""
    
    def to_dict(self) -> dict:
        return {
            "measurement_id": self.measurement_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "measurement_type": self.measurement_type.value,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata,
            "device_serial": self.device_serial,
        }


@dataclass
class MeasurementSeries:
    """Series of measurements for comparison."""
    series_id: str
    measurement_type: MeasurementType
    name: str
    unit: str
    measurements: list[Measurement] = field(default_factory=list)
    device_serial: str = ""
    baseline_timestamp: Optional[float] = None
    
    def add_measurement(self, measurement: Measurement):
        self.measurements.append(measurement)
        if self.baseline_timestamp is None:
            self.baseline_timestamp = measurement.timestamp
    
    def get_baseline(self) -> Optional[Measurement]:
        if not self.measurements:
            return None
        return min(self.measurements, key=lambda m: m.timestamp)
    
    def get_latest(self) -> Optional[Measurement]:
        if not self.measurements:
            return None
        return max(self.measurements, key=lambda m: m.timestamp)
    
    def get_change_percent(self) -> Optional[float]:
        baseline = self.get_baseline()
        latest = self.get_latest()
        if not baseline or not latest or baseline.value == 0:
            return None
        return ((latest.value - baseline.value) / baseline.value) * 100
    
    def get_statistics(self) -> dict:
        if not self.measurements:
            return {}
        values = [m.value for m in self.measurements]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        }
    
    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "measurement_type": self.measurement_type.value,
            "name": self.name,
            "unit": self.unit,
            "device_serial": self.device_serial,
            "baseline_timestamp": self.baseline_timestamp,
            "measurements": [m.to_dict() for m in self.measurements],
            "statistics": self.get_statistics(),
            "change_percent": self.get_change_percent(),
        }


class PerformanceMonitor:
    """Monitors device performance using read-only operations."""
    
    def __init__(self, adb_manager: ADBManager, data_root: Optional[Path] = None):
        self.adb_manager = adb_manager
        self._series: dict[str, MeasurementSeries] = {}
        
        if data_root is None:
            data_root = Path.home() / "TVFreedom_Performance"
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        
        self._load_data()
    
    def _load_data(self):
        """Load measurement series from disk."""
        data_file = self.data_root / "measurements.json"
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for series_data in data.get("series", []):
                    series = MeasurementSeries(
                        series_id=series_data["series_id"],
                        measurement_type=MeasurementType(series_data["measurement_type"]),
                        name=series_data["name"],
                        unit=series_data["unit"],
                        device_serial=series_data.get("device_serial", ""),
                        baseline_timestamp=series_data.get("baseline_timestamp"),
                    )
                    for m_data in series_data.get("measurements", []):
                        series.measurements.append(Measurement(
                            measurement_id=m_data["measurement_id"],
                            timestamp=m_data["timestamp"],
                            measurement_type=MeasurementType(m_data["measurement_type"]),
                            name=m_data["name"],
                            value=m_data["value"],
                            unit=m_data["unit"],
                            metadata=m_data.get("metadata", {}),
                            device_serial=m_data.get("device_serial", ""),
                        ))
                    self._series[series.series_id] = series
            except Exception:
                pass
    
    def _save_data(self):
        """Save measurement series to disk."""
        data_file = self.data_root / "measurements.json"
        try:
            data = {
                "saved_at": time.time(),
                "series": [s.to_dict() for s in self._series.values()],
            }
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save performance data: {e}")
    
    def _run_safe(self, command: str) -> tuple[bool, str]:
        """Run a safe ADB command."""
        success, stdout, stderr = self.adb_manager.run_shell_command(command)
        return success, stdout.strip() if stdout else stderr.strip()
    
    def measure_memory(self) -> Optional[Measurement]:
        """Measure current memory usage."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        success, output = self._run_safe("cat /proc/meminfo")
        if not success:
            return None
        
        meminfo = {}
        for line in output.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().replace(' kB', '')
                try:
                    meminfo[key] = int(value)
                except ValueError:
                    pass
        
        if "MemTotal" in meminfo and "MemAvailable" in meminfo:
            total_mb = meminfo["MemTotal"] / 1024
            available_mb = meminfo["MemAvailable"] / 1024
            used_mb = total_mb - available_mb
            used_percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            
            return Measurement(
                measurement_id=f"mem_{int(time.time() * 1000)}",
                timestamp=time.time(),
                measurement_type=MeasurementType.MEMORY,
                name="memory_used_percent",
                value=round(used_percent, 1),
                unit="%",
                metadata={
                    "total_mb": round(total_mb, 1),
                    "available_mb": round(available_mb, 1),
                    "used_mb": round(used_mb, 1),
                    "meminfo": meminfo,
                },
                device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
            )
        return None
    
    def measure_cpu(self) -> Optional[Measurement]:
        """Measure CPU usage (approximate from /proc/stat)."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        # Read /proc/stat twice with a delay to calculate CPU usage
        success1, output1 = self._run_safe("cat /proc/stat")
        if not success1:
            return None
        
        time.sleep(0.5)
        
        success2, output2 = self._run_safe("cat /proc/stat")
        if not success2:
            return None
        
        def parse_cpu_stat(output):
            for line in output.split('\n'):
                if line.startswith("cpu "):
                    parts = line.split()
                    if len(parts) >= 8:
                        return {
                            "user": int(parts[1]),
                            "nice": int(parts[2]),
                            "system": int(parts[3]),
                            "idle": int(parts[4]),
                            "iowait": int(parts[5]),
                            "irq": int(parts[6]),
                            "softirq": int(parts[7]),
                        }
            return None
        
        stat1 = parse_cpu_stat(output1)
        stat2 = parse_cpu_stat(output2)
        
        if stat1 and stat2:
            idle1 = stat1["idle"] + stat1["iowait"]
            idle2 = stat2["idle"] + stat2["iowait"]
            
            total1 = sum(stat1.values())
            total2 = sum(stat2.values())
            
            total_delta = total2 - total1
            idle_delta = idle2 - idle1
            
            if total_delta > 0:
                cpu_usage = 100.0 * (1.0 - idle_delta / total_delta)
                return Measurement(
                    measurement_id=f"cpu_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    measurement_type=MeasurementType.CPU,
                    name="cpu_usage_percent",
                    value=round(cpu_usage, 1),
                    unit="%",
                    metadata={
                        "stat1": stat1,
                        "stat2": stat2,
                    },
                    device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
                )
        return None
    
    def measure_storage(self) -> Optional[Measurement]:
        """Measure storage usage."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        success, output = self._run_safe("df /data")
        if not success:
            return None
        
        lines = output.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                total_kb = int(parts[1])
                used_kb = int(parts[2])
                free_kb = int(parts[3])
                use_percent = parts[4].replace('%', '')
                
                return Measurement(
                    measurement_id=f"storage_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    measurement_type=MeasurementType.STORAGE,
                    name="storage_used_percent",
                    value=float(use_percent),
                    unit="%",
                    metadata={
                        "total_gb": round(total_kb / 1024 / 1024, 2),
                        "used_gb": round(used_kb / 1024 / 1024, 2),
                        "free_gb": round(free_kb / 1024 / 1024, 2),
                    },
                    device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
                )
        return None
    
    def measure_uptime(self) -> Optional[Measurement]:
        """Measure device uptime."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        success, output = self._run_safe("cat /proc/uptime")
        if not success:
            return None
        
        try:
            uptime_seconds = float(output.split()[0])
            return Measurement(
                measurement_id=f"uptime_{int(time.time() * 1000)}",
                timestamp=time.time(),
                measurement_type=MeasurementType.BOOT_TIME,
                name="uptime_hours",
                value=round(uptime_seconds / 3600, 2),
                unit="hours",
                metadata={
                    "uptime_seconds": uptime_seconds,
                    "uptime_days": round(uptime_seconds / 86400, 2),
                },
                device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
            )
        except (ValueError, IndexError):
            return None
    
    def measure_thermal(self) -> list[Measurement]:
        """Measure thermal zones."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return []
        
        measurements = []
        success, output = self._run_safe("ls /sys/class/thermal/")
        if not success:
            return measurements
        
        for zone in output.strip().split('\n'):
            zone = zone.strip()
            if zone.startswith("thermal_zone"):
                # Read temperature
                success, temp_output = self._run_safe(f"cat /sys/class/thermal/{zone}/temp")
                if success:
                    try:
                        temp_millicelsius = int(temp_output.strip())
                        temp_celsius = temp_millicelsius / 1000.0
                        
                        # Read type
                        success, type_output = self._run_safe(f"cat /sys/class/thermal/{zone}/type")
                        zone_type = type_output.strip() if success else "unknown"
                        
                        measurements.append(Measurement(
                            measurement_id=f"thermal_{zone}_{int(time.time() * 1000)}",
                            timestamp=time.time(),
                            measurement_type=MeasurementType.THERMAL,
                            name=f"thermal_{zone}",
                            value=round(temp_celsius, 1),
                            unit="°C",
                            metadata={
                                "zone": zone,
                                "type": zone_type,
                            },
                            device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
                        ))
                    except ValueError:
                        pass
        return measurements
    
    def measure_battery(self) -> Optional[Measurement]:
        """Measure battery status."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        success, output = self._run_safe("dumpsys battery")
        if not success:
            return None
        
        battery_info = {}
        for line in output.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                battery_info[key] = value
        
        level = None
        if "level" in battery_info:
            try:
                level = int(battery_info["level"])
            except ValueError:
                pass
        
        if level is not None:
            return Measurement(
                measurement_id=f"battery_{int(time.time() * 1000)}",
                timestamp=time.time(),
                measurement_type=MeasurementType.BATTERY,
                name="battery_level",
                value=level,
                unit="%",
                metadata=battery_info,
                device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
            )
        return None
    
    def measure_app_launch_time(self, package_name: str, 
                                 iterations: int = 3) -> Optional[Measurement]:
        """Measure app launch time (approximate)."""
        if not self.adb_manager.connected_device or \
           self.adb_manager.connection_state != ADBState.CONNECTED:
            return None
        
        launch_times = []
        
        for i in range(iterations):
            # Force stop app first
            self._run_safe(f"am force-stop {package_name}")
            time.sleep(0.5)
            
            # Get launch time using am start -W
            start_time = time.time()
            success, output = self._run_safe(f"am start -W -S {package_name}/.MainActivity 2>&1 | head -20")
            elapsed = (time.time() - start_time) * 1000  # ms
            
            if success and "TotalTime" in output:
                try:
                    for line in output.split('\n'):
                        if "TotalTime" in line:
                            launch_time = int(line.split(":")[1].strip())
                            launch_times.append(launch_time)
                            break
                except (ValueError, IndexError):
                    pass
            
            time.sleep(1)
        
        if launch_times:
            avg_time = statistics.mean(launch_times)
            return Measurement(
                measurement_id=f"launch_{package_name}_{int(time.time() * 1000)}",
                timestamp=time.time(),
                measurement_type=MeasurementType.APP_LAUNCH,
                name=f"app_launch_time_{package_name}",
                value=round(avg_time, 1),
                unit="ms",
                metadata={
                    "package": package_name,
                    "iterations": iterations,
                    "individual_times": launch_times,
                    "min": min(launch_times),
                    "max": max(launch_times),
                },
                device_serial=self.adb_manager.connected_device.serial if self.adb_manager.connected_device else "",
            )
        return None
    
    def record_measurement(self, measurement: Measurement):
        """Record a measurement in the appropriate series."""
        series_key = f"{measurement.measurement_type.value}_{measurement.name}"
        
        if series_key not in self._series:
            self._series[series_key] = MeasurementSeries(
                series_id=series_key,
                measurement_type=measurement.measurement_type,
                name=measurement.name,
                unit=measurement.unit,
                device_serial=measurement.device_serial,
            )
        
        self._series[series_key].add_measurement(measurement)
        self._save_data()
    
    def collect_all_metrics(self) -> dict[str, Measurement]:
        """Collect all available metrics at once."""
        metrics = {}
        
        mem = self.measure_memory()
        if mem:
            metrics["memory"] = mem
            self.record_measurement(mem)
        
        cpu = self.measure_cpu()
        if cpu:
            metrics["cpu"] = cpu
            self.record_measurement(cpu)
        
        storage = self.measure_storage()
        if storage:
            metrics["storage"] = storage
            self.record_measurement(storage)
        
        uptime = self.measure_uptime()
        if uptime:
            metrics["uptime"] = uptime
            self.record_measurement(uptime)
        
        battery = self.measure_battery()
        if battery:
            metrics["battery"] = battery
            self.record_measurement(battery)
        
        thermal = self.measure_thermal()
        for m in thermal:
            metrics[m.name] = m
            self.record_measurement(m)
        
        return metrics
    
    def get_series(self, series_id: str) -> Optional[MeasurementSeries]:
        """Get a measurement series."""
        return self._series.get(series_key)
    
    def get_all_series(self) -> dict[str, MeasurementSeries]:
        """Get all measurement series."""
        return self._series.copy()
    
    def export_series(self, series_id: str, output_path: Path) -> bool:
        """Export a measurement series to JSON."""
        series = self._series.get(series_id)
        if not series:
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(series.to_dict(), f, indent=2)
            return True
        except Exception:
            return False
    
    def export_all(self, output_path: Path) -> bool:
        """Export all measurement series to JSON."""
        try:
            data = {
                "exported_at": time.time(),
                "series": {sid: s.to_dict() for sid, s in self._series.items()},
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    def compare_with_baseline(self, series_id: str) -> Optional[dict]:
        """Compare latest measurement with baseline."""
        series = self._series.get(series_id)
        if not series or len(series.measurements) < 2:
            return None
        
        baseline = series.get_baseline()
        latest = series.get_latest()
        change = series.get_change_percent()
        
        if not baseline or not latest or change is None:
            return None
        
        return {
            "series_id": series_id,
            "name": series.name,
            "unit": series.unit,
            "baseline_value": baseline.value,
            "baseline_time": baseline.timestamp,
            "latest_value": latest.value,
            "latest_time": latest.timestamp,
            "change_percent": round(change, 2),
            "improved": change < 0 if series.measurement_type in (
                MeasurementType.MEMORY, MeasurementType.CPU, MeasurementType.STORAGE
            ) else change > 0,
        }


def create_performance_monitor(adb_manager: ADBManager, 
                                data_root: Optional[Path] = None) -> PerformanceMonitor:
    """Factory function to create a PerformanceMonitor."""
    return PerformanceMonitor(adb_manager, data_root)