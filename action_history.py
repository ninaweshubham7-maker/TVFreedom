"""
Action History - Action logging and undo support for TV Freedom.

This module provides a comprehensive action history system that logs
all device-changing operations with full reversal information.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
import json
import time
from datetime import datetime
from enum import Enum


class ActionStatus(Enum):
    """Status of an action."""
    PENDING = "pending"           # Awaiting confirmation
    CONFIRMED = "confirmed"       # Confirmed, not yet executed
    EXECUTING = "executing"       # Currently executing
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"             # Execution failed
    PARTIAL = "partial"           # Partially completed
    ROLLED_BACK = "rolled_back"   # Reversed


class ActionType(Enum):
    """Type of device action."""
    DISABLE_PACKAGE = "disable_package"
    ENABLE_PACKAGE = "enable_package"
    UNINSTALL_PACKAGE = "uninstall_package"
    CLEAR_PACKAGE_DATA = "clear_package_data"
    CHANGE_SETTING = "change_setting"
    CHANGE_MULTIPLE_SETTINGS = "change_multiple_settings"
    SET_DEFAULT_LAUNCHER = "set_default_launcher"
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"
    CUSTOM = "custom"


@dataclass
class ActionRecord:
    """Record of a device action."""
    action_id: str
    timestamp: float
    action_type: ActionType
    target: str  # Package name, setting key, etc.
    parameters: dict = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    backup_id: Optional[str] = None  # Associated pre-action backup
    device_serial: str = ""
    device_identity: dict = field(default_factory=dict)
    
    # Execution details
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    execution_time_ms: int = 0
    success: bool = False
    error_message: str = ""
    output: str = ""
    
    # Reversal info
    reversal_action: Optional[ActionType] = None
    reversal_parameters: dict = field(default_factory=dict)
    reversal_instructions: str = ""
    can_reverse: bool = False
    reversed_at: Optional[float] = None
    reversed_by: Optional[str] = None  # Action ID of reversal
    
    # User context
    user_confirmed: bool = False
    confirmation_timestamp: Optional[float] = None
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "action_type": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "status": self.status.value,
            "backup_id": self.backup_id,
            "device_serial": self.device_serial,
            "device_identity": self.device_identity,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
            "output": self.output,
            "reversal_action": self.reversal_action.value if self.reversal_action else None,
            "reversal_parameters": self.reversal_parameters,
            "reversal_instructions": self.reversal_instructions,
            "can_reverse": self.can_reverse,
            "reversed_at": self.reversed_at,
            "reversed_by": self.reversed_by,
            "user_confirmed": self.user_confirmed,
            "confirmation_timestamp": self.confirmation_timestamp,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ActionRecord':
        return cls(
            action_id=data["action_id"],
            timestamp=data["timestamp"],
            action_type=ActionType(data["action_type"]),
            target=data["target"],
            parameters=data.get("parameters", {}),
            status=ActionStatus(data["status"]),
            backup_id=data.get("backup_id"),
            device_serial=data.get("device_serial", ""),
            device_identity=data.get("device_identity", {}),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            execution_time_ms=data.get("execution_time_ms", 0),
            success=data.get("success", False),
            error_message=data.get("error_message", ""),
            output=data.get("output", ""),
            reversal_action=ActionType(data["reversal_action"]) if data.get("reversal_action") else None,
            reversal_parameters=data.get("reversal_parameters", {}),
            reversal_instructions=data.get("reversal_instructions", ""),
            can_reverse=data.get("can_reverse", False),
            reversed_at=data.get("reversed_at"),
            reversed_by=data.get("reversed_by"),
            user_confirmed=data.get("user_confirmed", False),
            confirmation_timestamp=data.get("confirmation_timestamp"),
            notes=data.get("notes", ""),
        )


class ActionHistory:
    """Manages action history and undo support."""
    
    def __init__(self, history_root: Optional[Path] = None):
        if history_root is None:
            history_root = Path.home() / "TVFreedom_ActionHistory"
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)
        
        self._actions: dict[str, ActionRecord] = {}
        self._load_history()
    
    def _load_history(self):
        """Load action history from disk."""
        history_file = self.history_root / "actions.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for action_data in data:
                    action = ActionRecord.from_dict(action_data)
                    self._actions[action.action_id] = action
            except Exception:
                pass
    
    def _save_history(self):
        """Save action history to disk."""
        history_file = self.history_root / "actions.json"
        try:
            data = [action.to_dict() for action in self._actions.values()]
            # Sort by timestamp descending
            data.sort(key=lambda x: x["timestamp"], reverse=True)
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save action history: {e}")
    
    def create_action(self, action_type: ActionType, target: str,
                      parameters: dict, device_serial: str,
                      device_identity: dict, reversal_action: ActionType,
                      reversal_parameters: dict, reversal_instructions: str,
                      backup_id: Optional[str] = None) -> ActionRecord:
        """
        Create a new action record (pending confirmation).
        
        Returns:
            ActionRecord for the new action.
        """
        action_id = f"action_{int(time.time() * 1000)}_{action_type.value}_{target[:20]}"
        
        action = ActionRecord(
            action_id=action_id,
            timestamp=time.time(),
            action_type=action_type,
            target=target,
            parameters=parameters,
            status=ActionStatus.PENDING,
            backup_id=backup_id,
            device_serial=device_serial,
            device_identity=device_identity,
            reversal_action=reversal_action,
            reversal_parameters=reversal_parameters,
            reversal_instructions=reversal_instructions,
            can_reverse=bool(reversal_action),
        )
        
        self._actions[action_id] = action
        self._save_history()
        return action
    
    def confirm_action(self, action_id: str) -> bool:
        """Mark action as confirmed by user."""
        if action_id in self._actions:
            action = self._actions[action_id]
            action.status = ActionStatus.CONFIRMED
            action.user_confirmed = True
            action.confirmation_timestamp = time.time()
            self._save_history()
            return True
        return False
    
    def start_execution(self, action_id: str) -> bool:
        """Mark action as executing."""
        if action_id in self._actions:
            action = self._actions[action_id]
            action.status = ActionStatus.EXECUTING
            action.started_at = time.time()
            self._save_history()
            return True
        return False
    
    def complete_action(self, action_id: str, success: bool,
                        output: str = "", error_message: str = "") -> bool:
        """Mark action as completed or failed."""
        if action_id in self._actions:
            action = self._actions[action_id]
            action.completed_at = time.time()
            action.execution_time_ms = int((action.completed_at - action.started_at) * 1000) if action.started_at else 0
            action.success = success
            action.output = output
            action.error_message = error_message
            action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
            self._save_history()
            return True
        return False
    
    def reverse_action(self, action_id: str, success: bool = True) -> bool:
        """Mark action as reversed."""
        if action_id in self._actions:
            action = self._actions[action_id]
            action.status = ActionStatus.ROLLED_BACK
            action.reversed_at = time.time()
            action.reversed_by = f"reversal_{int(time.time() * 1000)}"
            self._save_history()
            return True
        return False
    
    def get_action(self, action_id: str) -> Optional[ActionRecord]:
        """Get a specific action."""
        return self._actions.get(action_id)
    
    def get_all_actions(self, limit: Optional[int] = None,
                        device_serial: Optional[str] = None) -> list[ActionRecord]:
        """Get all actions, optionally filtered."""
        actions = list(self._actions.values())
        
        if device_serial:
            actions = [a for a in actions if a.device_serial == device_serial]
        
        # Sort by timestamp descending
        actions.sort(key=lambda a: a.timestamp, reverse=True)
        
        if limit:
            actions = actions[:limit]
        
        return actions
    
    def get_reversible_actions(self, device_serial: Optional[str] = None) -> list[ActionRecord]:
        """Get actions that can be reversed."""
        actions = []
        for action in self._actions.values():
            if action.can_reverse and action.status == ActionStatus.COMPLETED and action.success:
                if device_serial is None or action.device_serial == device_serial:
                    actions.append(action)
        
        actions.sort(key=lambda a: a.timestamp, reverse=True)
        return actions
    
    def get_actions_for_package(self, package_name: str,
                                 device_serial: Optional[str] = None) -> list[ActionRecord]:
        """Get all actions for a specific package."""
        actions = []
        for action in self._actions.values():
            if action.target == package_name:
                if device_serial is None or action.device_serial == device_serial:
                    actions.append(action)
        
        actions.sort(key=lambda a: a.timestamp, reverse=True)
        return actions
    
    def get_summary(self, device_serial: Optional[str] = None) -> dict:
        """Get summary of action history."""
        actions = self.get_all_actions(device_serial=device_serial)
        
        summary = {
            "total_actions": len(actions),
            "by_status": {},
            "by_type": {},
            "by_device": {},
            "reversible_count": 0,
            "success_rate": 0.0,
        }
        
        completed = [a for a in actions if a.status == ActionStatus.COMPLETED]
        if completed:
            summary["success_rate"] = len([a for a in completed if a.success]) / len(completed)
        
        for action in actions:
            # By status
            status = action.status.value
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # By type
            atype = action.action_type.value
            summary["by_type"][atype] = summary["by_type"].get(atype, 0) + 1
            
            # By device
            dev = action.device_serial or "unknown"
            summary["by_device"][dev] = summary["by_device"].get(dev, 0) + 1
            
            # Reversible
            if action.can_reverse and action.status == ActionStatus.COMPLETED and action.success:
                summary["reversible_count"] += 1
        
        return summary
    
    def export_history(self, output_path: Path, device_serial: Optional[str] = None) -> bool:
        """Export action history to JSON file."""
        try:
            actions = self.get_all_actions(device_serial=device_serial)
            data = {
                "export_time": time.time(),
                "action_count": len(actions),
                "actions": [a.to_dict() for a in actions],
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    def clear_history(self, device_serial: Optional[str] = None) -> int:
        """Clear action history, optionally for a specific device."""
        if device_serial:
            to_remove = [aid for aid, a in self._actions.items() if a.device_serial == device_serial]
            count = len(to_remove)
            for aid in to_remove:
                del self._actions[aid]
        else:
            count = len(self._actions)
            self._actions.clear()
        
        self._save_history()
        return count


def create_action_history(history_root: Optional[Path] = None) -> ActionHistory:
    """Factory function to create an ActionHistory."""
    return ActionHistory(history_root)