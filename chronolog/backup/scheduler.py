import os
import json
import threading
import schedule
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .backup_manager import BackupManager


class ScheduleFrequency(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class BackupSchedule:
    schedule_id: str
    frequency: ScheduleFrequency
    time: Optional[str]  # For daily/weekly/monthly: "HH:MM"
    day_of_week: Optional[int]  # For weekly: 0-6 (Monday-Sunday)
    day_of_month: Optional[int]  # For monthly: 1-31
    destination: str
    backup_type: str
    compression: str
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def to_dict(self):
        data = asdict(self)
        data['frequency'] = self.frequency.value
        if self.last_run:
            data['last_run'] = self.last_run.isoformat()
        if self.next_run:
            data['next_run'] = self.next_run.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        data['frequency'] = ScheduleFrequency(data['frequency'])
        if data.get('last_run'):
            data['last_run'] = datetime.fromisoformat(data['last_run'])
        if data.get('next_run'):
            data['next_run'] = datetime.fromisoformat(data['next_run'])
        return cls(**data)


class BackupScheduler:
    """Manages scheduled backups for ChronoLog repositories."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.chronolog_dir = repo_path / ".chronolog"
        self.scheduler_dir = self.chronolog_dir / "scheduler"
        self.scheduler_dir.mkdir(exist_ok=True)
        self.config_file = self.scheduler_dir / "schedules.json"
        self.log_file = self.scheduler_dir / "scheduler.log"
        
        self.backup_manager = BackupManager(repo_path)
        self.schedules: Dict[str, BackupSchedule] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.callbacks: List[Callable] = []
        
        self._load_schedules()
    
    def _load_schedules(self):
        """Load schedules from configuration file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for schedule_id, schedule_data in data.items():
                        self.schedules[schedule_id] = BackupSchedule.from_dict(schedule_data)
            except:
                self.schedules = {}
    
    def _save_schedules(self):
        """Save schedules to configuration file."""
        data = {
            schedule_id: schedule.to_dict()
            for schedule_id, schedule in self.schedules.items()
        }
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _log(self, message: str, level: str = "INFO"):
        """Log scheduler events."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(log_entry)
            except:
                pass
    
    def add_schedule(self, frequency: ScheduleFrequency, destination: str,
                    backup_type: str = "full", compression: str = "gzip",
                    time: Optional[str] = None, day_of_week: Optional[int] = None,
                    day_of_month: Optional[int] = None) -> str:
        """
        Add a new backup schedule.
        
        Returns:
            Schedule ID
        """
        # Generate schedule ID
        schedule_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create schedule
        schedule = BackupSchedule(
            schedule_id=schedule_id,
            frequency=frequency,
            time=time,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            destination=destination,
            backup_type=backup_type,
            compression=compression,
            enabled=True
        )
        
        # Calculate next run time
        schedule.next_run = self._calculate_next_run(schedule)
        
        # Save schedule
        self.schedules[schedule_id] = schedule
        self._save_schedules()
        
        self._log(f"Added backup schedule {schedule_id}: {frequency.value}")
        
        # Restart scheduler if running
        if self.running:
            self.stop()
            self.start()
        
        return schedule_id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a backup schedule."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            self._save_schedules()
            self._log(f"Removed backup schedule {schedule_id}")
            
            # Restart scheduler if running
            if self.running:
                self.stop()
                self.start()
            
            return True
        return False
    
    def enable_schedule(self, schedule_id: str, enabled: bool = True):
        """Enable or disable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = enabled
            self._save_schedules()
            self._log(f"{'Enabled' if enabled else 'Disabled'} schedule {schedule_id}")
    
    def _calculate_next_run(self, schedule: BackupSchedule) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.now()
        
        if schedule.frequency == ScheduleFrequency.HOURLY:
            return now + timedelta(hours=1)
        
        elif schedule.frequency == ScheduleFrequency.DAILY:
            if schedule.time:
                hour, minute = map(int, schedule.time.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            else:
                return now + timedelta(days=1)
        
        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            if schedule.day_of_week is not None and schedule.time:
                hour, minute = map(int, schedule.time.split(':'))
                days_ahead = schedule.day_of_week - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run
            else:
                return now + timedelta(weeks=1)
        
        elif schedule.frequency == ScheduleFrequency.MONTHLY:
            if schedule.day_of_month and schedule.time:
                hour, minute = map(int, schedule.time.split(':'))
                next_month = now.replace(day=1) + timedelta(days=32)
                next_month = next_month.replace(day=1)
                
                try:
                    next_run = now.replace(day=schedule.day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run = next_month.replace(day=schedule.day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
                except ValueError:
                    # Day doesn't exist in this month (e.g., Feb 31)
                    next_run = next_month
                
                return next_run
            else:
                return now + timedelta(days=30)
        
        return now + timedelta(hours=1)  # Default fallback
    
    def _run_backup(self, schedule: BackupSchedule):
        """Execute a scheduled backup."""
        self._log(f"Starting scheduled backup {schedule.schedule_id}")
        
        try:
            # Create destination directory
            dest_path = Path(schedule.destination)
            dest_path.mkdir(parents=True, exist_ok=True)
            
            # Determine if incremental
            incremental_from = None
            if schedule.backup_type == "incremental" and schedule.last_run:
                # Find last successful backup
                backups = self.backup_manager.list_backups(dest_path)
                for backup in backups:
                    if backup.timestamp >= schedule.last_run:
                        incremental_from = backup.backup_id
                        break
            
            # Create backup
            backup_id = self.backup_manager.create_backup(
                destination=dest_path,
                backup_type=schedule.backup_type if incremental_from else "full",
                compression=schedule.compression,
                incremental_from=incremental_from
            )
            
            # Update schedule
            schedule.last_run = datetime.now()
            schedule.next_run = self._calculate_next_run(schedule)
            self._save_schedules()
            
            self._log(f"Completed scheduled backup {schedule.schedule_id}: {backup_id}")
            
        except Exception as e:
            self._log(f"Failed scheduled backup {schedule.schedule_id}: {e}", "ERROR")
    
    def _schedule_job(self, schedule: BackupSchedule):
        """Schedule a job based on the schedule configuration."""
        if not schedule.enabled:
            return
        
        job_func = lambda: self._run_backup(schedule)
        
        if schedule.frequency == ScheduleFrequency.HOURLY:
            schedule.every().hour.do(job_func)
        
        elif schedule.frequency == ScheduleFrequency.DAILY:
            if schedule.time:
                schedule.every().day.at(schedule.time).do(job_func)
            else:
                schedule.every().day.do(job_func)
        
        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            if schedule.day_of_week is not None:
                day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                day_name = day_names[schedule.day_of_week]
                if schedule.time:
                    getattr(schedule.every(), day_name).at(schedule.time).do(job_func)
                else:
                    getattr(schedule.every(), day_name).do(job_func)
            else:
                schedule.every().week.do(job_func)
        
        elif schedule.frequency == ScheduleFrequency.MONTHLY:
            # Schedule doesn't support monthly directly, so we'll check daily
            def monthly_check():
                now = datetime.now()
                if schedule.day_of_month and now.day == schedule.day_of_month:
                    if schedule.time:
                        hour, minute = map(int, schedule.time.split(':'))
                        if now.hour == hour and now.minute == minute:
                            job_func()
                    else:
                        job_func()
            
            schedule.every().hour.do(monthly_check)
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self._log(f"Scheduler error: {e}", "ERROR")
    
    def start(self):
        """Start the backup scheduler."""
        if self.running:
            return
        
        self._log("Starting backup scheduler")
        
        # Clear existing jobs
        schedule.clear()
        
        # Schedule all enabled jobs
        for schedule_id, backup_schedule in self.schedules.items():
            if backup_schedule.enabled:
                self._schedule_job(backup_schedule)
        
        # Start scheduler thread
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
    def stop(self):
        """Stop the backup scheduler."""
        if not self.running:
            return
        
        self._log("Stopping backup scheduler")
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
    
    def list_schedules(self) -> List[BackupSchedule]:
        """List all backup schedules."""
        return list(self.schedules.values())
    
    def get_schedule(self, schedule_id: str) -> Optional[BackupSchedule]:
        """Get a specific schedule."""
        return self.schedules.get(schedule_id)
    
    def run_now(self, schedule_id: str):
        """Run a backup immediately for a given schedule."""
        if schedule_id in self.schedules:
            schedule = self.schedules[schedule_id]
            self._log(f"Manually triggering backup for schedule {schedule_id}")
            self._run_backup(schedule)
    
    def add_callback(self, callback: Callable):
        """Add a callback for scheduler events."""
        self.callbacks.append(callback)
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """Get recent scheduler logs."""
        if not self.log_file.exists():
            return []
        
        with open(self.log_file, 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]