"""BatchProcessor module for parallel job execution.

The BatchProcessor class can be used to run code blocks of the program as
separate processes. Multiple pieces of code can be submitted to be executed
in parallel. The number of CPU cores to use is limited at object creation time.
"""

import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Callable, Any, Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class JobInfo:
    """Storage container for batch job related information.

    Contains job id, process id, stdout/stderr data and return value.
    """

    job_id: int
    func: Callable
    tag: Any = None
    pid: Optional[int] = None
    ret_val: Optional[int] = None
    stdout: str = ''
    stderr: str = ''
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)

    @property
    def jobId(self):
        """Alias for Ruby compatibility."""
        return self.job_id

    @property
    def retVal(self):
        """Alias for Ruby compatibility."""
        return self.ret_val


def _worker_function(func, args, kwargs):
    """Worker function that runs in subprocess and returns result."""
    try:
        result = func(*args, **kwargs)
        return (0, result, '', '')
    except Exception as e:
        import traceback
        return (1, None, '', traceback.format_exc())


class BatchProcessor:
    """Run code blocks in parallel processes.

    Submitted jobs are queued and scheduled to the given number of CPUs.
    Usage:
        1. Create a BatchProcessor object with max CPU cores
        2. Use queue() to submit jobs
        3. Use wait() to wait for completion and process results
    """

    def __init__(self, max_cpu_cores: int = None):
        """Create a BatchProcessor object.

        Args:
            max_cpu_cores: Maximum number of simultaneous processes.
                          Defaults to CPU count.
        """
        if max_cpu_cores is None:
            max_cpu_cores = multiprocessing.cpu_count()
        self._max_cpu_cores = max_cpu_cores

        self._to_run_queue: List[JobInfo] = []
        self._running_jobs: Dict[int, JobInfo] = {}
        self._completed_jobs: List[JobInfo] = []

        self._lock = threading.Lock()
        self._jobs_in = 0
        self._jobs_out = 0

        self._executor = None

    @property
    def maxCpuCores(self):
        """Return the maximum number of CPU cores to use."""
        return self._max_cpu_cores

    def queue(self, tag: Any = None, func: Callable = None, *args, **kwargs):
        """Add a new job to the job queue.

        Args:
            tag: Optional data to identify the job upon completion.
            func: The function to execute in a separate process.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.
        """
        with self._lock:
            if self._jobs_out > 0:
                raise RuntimeError("You cannot call queue() while wait() is running!")

            job = JobInfo(
                job_id=self._jobs_in,
                func=func,
                tag=tag,
                args=args,
                kwargs=kwargs
            )
            self._jobs_in += 1
            self._to_run_queue.append(job)

    def wait(self, callback: Callable[[JobInfo], None] = None):
        """Wait for all jobs to complete.

        Args:
            callback: Optional function called with each JobInfo as jobs complete.
        """
        if self._jobs_in == 0:
            return

        # Create executor
        self._executor = ProcessPoolExecutor(max_workers=self._max_cpu_cores)

        try:
            # Submit all jobs
            futures = {}
            for job in self._to_run_queue:
                future = self._executor.submit(
                    _worker_function, job.func, job.args, job.kwargs
                )
                futures[future] = job

            # Wait for completion and process results
            for future in as_completed(futures):
                job = futures[future]
                try:
                    ret_code, result, stdout, stderr = future.result()
                    job.ret_val = ret_code
                    job.stdout = stdout
                    job.stderr = stderr
                except Exception as e:
                    job.ret_val = 1
                    job.stderr = str(e)

                self._jobs_out += 1
                self._completed_jobs.append(job)

                if callback:
                    callback(job)

        finally:
            self._executor.shutdown(wait=True)
            self._executor = None

        # Reset for reuse
        self._to_run_queue.clear()
        self._running_jobs.clear()
        self._completed_jobs.clear()
        self._jobs_in = 0
        self._jobs_out = 0

    def cancel(self):
        """Cancel all pending jobs."""
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None


class ThreadBatchProcessor:
    """Thread-based batch processor for lighter workloads.

    Uses threads instead of processes, suitable for I/O-bound tasks.
    """

    def __init__(self, max_threads: int = None):
        """Create a ThreadBatchProcessor object.

        Args:
            max_threads: Maximum number of simultaneous threads.
                        Defaults to CPU count * 5.
        """
        if max_threads is None:
            max_threads = multiprocessing.cpu_count() * 5
        self._max_threads = max_threads

        self._to_run_queue: List[JobInfo] = []
        self._jobs_in = 0
        self._jobs_out = 0
        self._lock = threading.Lock()
        self._executor = None

    def queue(self, tag: Any = None, func: Callable = None, *args, **kwargs):
        """Add a new job to the job queue."""
        with self._lock:
            job = JobInfo(
                job_id=self._jobs_in,
                func=func,
                tag=tag,
                args=args,
                kwargs=kwargs
            )
            self._jobs_in += 1
            self._to_run_queue.append(job)

    def wait(self, callback: Callable[[JobInfo], None] = None):
        """Wait for all jobs to complete."""
        if self._jobs_in == 0:
            return

        self._executor = ThreadPoolExecutor(max_workers=self._max_threads)

        try:
            futures = {}
            for job in self._to_run_queue:
                future = self._executor.submit(job.func, *job.args, **job.kwargs)
                futures[future] = job

            for future in as_completed(futures):
                job = futures[future]
                try:
                    result = future.result()
                    job.ret_val = 0
                except Exception as e:
                    job.ret_val = 1
                    job.stderr = str(e)

                self._jobs_out += 1

                if callback:
                    callback(job)

        finally:
            self._executor.shutdown(wait=True)
            self._executor = None

        self._to_run_queue.clear()
        self._jobs_in = 0
        self._jobs_out = 0
