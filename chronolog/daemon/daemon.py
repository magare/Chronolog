import os
import sys
import signal
import subprocess
import psutil
from pathlib import Path
from typing import Optional
from ..storage import Storage
from ..watcher import Watcher


class Daemon:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path) if isinstance(base_path, str) else base_path
        self.chronolog_dir = self.base_path / ".chronolog"
        self.pid_file = self.chronolog_dir / "daemon.pid"
        self.log_file = self.chronolog_dir / "daemon.log"
    
    def _write_pid(self, pid: int):
        self.pid_file.write_text(str(pid))
    
    def _read_pid(self) -> Optional[int]:
        if self.pid_file.exists():
            try:
                return int(self.pid_file.read_text().strip())
            except:
                return None
        return None
    
    def _is_process_running(self, pid: int) -> bool:
        try:
            # Check if process exists
            process = psutil.Process(pid)
            # Verify it's a chronolog daemon by checking command line
            cmdline = ' '.join(process.cmdline())
            return 'chronolog' in cmdline and 'daemon' in cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def is_running(self) -> bool:
        pid = self._read_pid()
        if pid:
            return self._is_process_running(pid)
        return False
    
    def start(self):
        if self.is_running():
            print("[ChronoLog] Daemon is already running")
            return
        
        # Use subprocess for all platforms to avoid forking issues
        script = f"""
import sys
sys.path.insert(0, {repr(str(Path(__file__).parent.parent.parent))})
from chronolog.daemon import Daemon
daemon = Daemon({repr(str(self.base_path))})
daemon._run_watcher()
"""
        
        # Start process in background
        kwargs = {}
        if os.name == 'nt':  # Windows
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:  # Unix-like
            kwargs['start_new_session'] = True
        
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=open(self.log_file, 'a'),
            stderr=subprocess.STDOUT,
            **kwargs
        )
        
        print(f"[ChronoLog] Starting daemon (PID: {process.pid})")
        self._write_pid(process.pid)
    
    def _run_watcher(self):
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            storage = Storage(self.chronolog_dir)
            watcher = Watcher(self.base_path, storage)
            watcher.start()
            
            # Keep the daemon running
            if os.name == 'posix':
                # Unix - wait for signals
                import time
                while True:
                    time.sleep(1)
            else:
                # Windows - wait for input
                input()
            
        except Exception as e:
            print(f"[ChronoLog] Daemon error: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        print(f"[ChronoLog] Received signal {signum}, shutting down...")
        sys.exit(0)
    
    def stop(self):
        pid = self._read_pid()
        if not pid:
            print("[ChronoLog] No daemon found")
            return
        
        if not self._is_process_running(pid):
            print("[ChronoLog] Daemon not running (stale PID file)")
            self.pid_file.unlink()
            return
        
        try:
            if os.name == 'posix':
                os.kill(pid, signal.SIGTERM)
            else:
                # Windows
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                             capture_output=True)
            
            print(f"[ChronoLog] Stopped daemon (PID: {pid})")
            self.pid_file.unlink()
            
        except Exception as e:
            print(f"[ChronoLog] Error stopping daemon: {e}")
    
    def status(self):
        if self.is_running():
            pid = self._read_pid()
            print(f"[ChronoLog] Daemon is running (PID: {pid})")
        else:
            print("[ChronoLog] Daemon is not running")