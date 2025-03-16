import errno
import fcntl
import multiprocessing
import os
import signal
import sys
import time

from mc_bench.apps.scheduler.config import refresh_settings, settings
from mc_bench.apps.scheduler.loop import scheduler_loop
from mc_bench.util.logging import configure_logging, get_logger

logger = get_logger(__name__)


class SchedulerManager:
    """
    Manager for the scheduler subprocess that handles rotation of the scheduler process.
    Ensures only one scheduler is running at a time and properly handles signal propagation.
    """

    def __init__(self, max_loops=None):
        # Use settings for subprocess configuration
        refresh_settings()  # Ensure we have the latest settings
        self.max_loops = max_loops or settings.MAX_SCHEDULER_LOOPS
        self.graceful_timeout = settings.SUBPROCESS_GRACEFUL_TIMEOUT
        self.force_timeout = settings.SUBPROCESS_FORCE_TIMEOUT
        self.restart_delay = settings.SUBPROCESS_RESTART_DELAY
        self.lockfile_path = settings.SCHEDULER_LOCK_PATH

        self.process = None
        self.running = True
        self.lockfile = None

    def acquire_lock(self):
        """Attempt to acquire an exclusive file lock to ensure only one scheduler is running."""
        try:
            self.lockfile = open(self.lockfile_path, "w")
            fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lockfile.write(str(os.getpid()))
            self.lockfile.flush()
            return True
        except IOError as e:
            if e.errno == errno.EWOULDBLOCK:
                logger.error("Another scheduler process is already running. Exiting.")
                return False
            raise
        except Exception as e:
            logger.exception(f"Error acquiring lock: {e}")
            return False

    def release_lock(self):
        """Release the file lock."""
        if self.lockfile:
            try:
                fcntl.flock(self.lockfile, fcntl.LOCK_UN)
                self.lockfile.close()
                if os.path.exists(self.lockfile_path):
                    os.remove(self.lockfile_path)
            except Exception as e:
                logger.exception(f"Error releasing lock: {e}")

    def start_subprocess(self):
        """Start a new scheduler subprocess."""
        if self.process and self.process.is_alive():
            logger.warning(
                "Attempted to start a subprocess when one is already running"
            )
            return

        # Refresh settings before starting new subprocess to pick up any changes
        refresh_settings()
        # Always use the latest max_loops setting from the database
        current_max_loops = settings.MAX_SCHEDULER_LOOPS

        logger.info(f"Starting scheduler subprocess (max loops: {current_max_loops})")
        self.process = multiprocessing.Process(
            target=scheduler_loop,
            args=(current_max_loops,),
            daemon=False,  # Non-daemon to allow proper cleanup
        )
        self.process.start()
        logger.info(f"Scheduler subprocess started with PID {self.process.pid}")

    def terminate_subprocess(self):
        """Gracefully terminate the subprocess."""
        if self.process and self.process.is_alive():
            logger.info(f"Terminating scheduler subprocess (PID: {self.process.pid})")
            # Send SIGTERM to allow graceful shutdown
            os.kill(self.process.pid, signal.SIGTERM)
            # Give process time to terminate gracefully
            self.process.join(timeout=self.graceful_timeout)
            if self.process.is_alive():
                logger.warning(
                    f"Subprocess didn't terminate within {self.graceful_timeout}s, forcing exit"
                )
                os.kill(self.process.pid, signal.SIGKILL)
                self.process.join(timeout=self.force_timeout)
            logger.info("Scheduler subprocess terminated")
        self.process = None

    def handle_signal(self, signum, frame):
        """Signal handler for graceful termination."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name} ({signum}), initiating shutdown")
        self.running = False
        self.terminate_subprocess()
        self.release_lock()
        logger.info("Scheduler manager shutdown complete")
        sys.exit(0)

    def run(self):
        """Main loop for scheduler manager."""
        if not self.acquire_lock():
            sys.exit(1)

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

        try:
            while self.running:
                # Start new subprocess if not running
                if not self.process or not self.process.is_alive():
                    self.start_subprocess()

                # Wait for subprocess to complete
                self.process.join(
                    timeout=1
                )  # Short timeout to allow for signal handling

                # Check if subprocess has exited, if so, handle restart
                if self.process and not self.process.is_alive():
                    exit_code = self.process.exitcode
                    logger.info(f"Subprocess completed with exit code {exit_code}")
                    if exit_code != 0:
                        logger.warning(
                            f"Subprocess had non-zero exit code, restarting in {self.restart_delay}s"
                        )
                        time.sleep(
                            self.restart_delay
                        )  # Delay before restarting on failure
                    self.process = None  # Clear process reference for next iteration
                else:
                    time.sleep(1)  # Short sleep to prevent busy-waiting

        except Exception as e:
            logger.exception(f"Error in scheduler manager: {e}")
        finally:
            self.terminate_subprocess()
            self.release_lock()
            logger.info("Scheduler manager exited")


def main():
    """
    Main entry point for the scheduler.
    """
    # Configure logger with settings
    configure_logging(
        humanize=settings.HUMANIZE_LOGS,
        level=settings.LOG_LEVEL,
    )

    # Ensure we have the latest settings
    refresh_settings()

    logger.info("Starting scheduler manager")
    logger.info(f"Default max tasks per queue: {settings.DEFAULT_MAX_QUEUED_TASKS}")
    logger.info(f"Scheduler interval: {settings.SCHEDULER_INTERVAL} seconds")
    logger.info(f"Max loops per scheduler process: {settings.MAX_SCHEDULER_LOOPS}")
    logger.info(f"Subprocess graceful timeout: {settings.SUBPROCESS_GRACEFUL_TIMEOUT}s")
    logger.info(f"Subprocess restart delay: {settings.SUBPROCESS_RESTART_DELAY}s")
    logger.info(f"Scheduler lock path: {settings.SCHEDULER_LOCK_PATH}")

    # Start the manager which handles the scheduler subprocess
    manager = SchedulerManager()
    manager.run()
