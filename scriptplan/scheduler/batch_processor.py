"""BatchProcessor module for parallel job execution.

The BatchProcessor class can be used to run code blocks of the program as
separate processes. Multiple pieces of code can be submitted to be executed
in parallel. The number of CPU cores to use is limited at object creation time.
"""

import multiprocessing
import threading
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class JobInfo:
    """Storage container for batch job related information.

    Contains job id, process id, stdout/stderr data and return value.
    """

    job_id: int
    func: Callable[..., Any]
    tag: Any = None
    pid: Optional[int] = None
    ret_val: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def jobId(self) -> int:
        """Alias for Ruby compatibility."""
        return self.job_id

    @property
    def retVal(self) -> Optional[int]:
        """Alias for Ruby compatibility."""
        return self.ret_val


def _worker_function(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[int, Any, str, str]:
    """Worker function that runs in subprocess and returns result."""
    try:
        result = func(*args, **kwargs)
        return (0, result, "", "")
    except Exception:
        import traceback

        return (1, None, "", traceback.format_exc())


class BatchProcessor:
    """Run code blocks in parallel processes.

    Submitted jobs are queued and scheduled to the given number of CPUs.
    Usage:
        1. Create a BatchProcessor object with max CPU cores
        2. Use queue() to submit jobs
        3. Use wait() to wait for completion and process results
    """

    def __init__(self, max_cpu_cores: Optional[int] = None) -> None:
        """Create a BatchProcessor object.

        Args:
            max_cpu_cores: Maximum number of simultaneous processes.
                          Defaults to CPU count.
        """
        if max_cpu_cores is None:
            max_cpu_cores = multiprocessing.cpu_count()
        self._max_cpu_cores = max_cpu_cores

        self._to_run_queue: list[JobInfo] = []
        self._running_jobs: dict[int, JobInfo] = {}
        self._completed_jobs: list[JobInfo] = []

        self._lock = threading.Lock()
        self._jobs_in = 0
        self._jobs_out = 0

        self._executor: Optional[ProcessPoolExecutor] = None

    @property
    def maxCpuCores(self) -> int:
        """Return the maximum number of CPU cores to use."""
        return self._max_cpu_cores

    def queue(self, tag: Any = None, func: Optional[Callable[..., Any]] = None, *args: Any, **kwargs: Any) -> None:
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

            if func is None:
                raise ValueError("func cannot be None")

            job = JobInfo(job_id=self._jobs_in, func=func, tag=tag, args=args, kwargs=kwargs)
            self._jobs_in += 1
            self._to_run_queue.append(job)

    def wait(self, callback: Optional[Callable[[JobInfo], None]] = None) -> None:
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
            futures: dict[Future[tuple[int, Any, str, str]], JobInfo] = {}
            for job in self._to_run_queue:
                future = self._executor.submit(_worker_function, job.func, job.args, job.kwargs)
                futures[future] = job

            # Wait for completion and process results
            for future in as_completed(futures):
                job = futures[future]
                try:
                    ret_code, _result, stdout, stderr = future.result()
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

    def cancel(self) -> None:
        """Cancel all pending jobs."""
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None


class ThreadBatchProcessor:
    """Thread-based batch processor for lighter workloads.

    Uses threads instead of processes, suitable for I/O-bound tasks.
    """

    def __init__(self, max_threads: Optional[int] = None) -> None:
        """Create a ThreadBatchProcessor object.

        Args:
            max_threads: Maximum number of simultaneous threads.
                        Defaults to CPU count * 5.
        """
        if max_threads is None:
            max_threads = multiprocessing.cpu_count() * 5
        self._max_threads = max_threads

        self._to_run_queue: list[JobInfo] = []
        self._jobs_in = 0
        self._jobs_out = 0
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None

    def queue(self, tag: Any = None, func: Optional[Callable[..., Any]] = None, *args: Any, **kwargs: Any) -> None:
        """Add a new job to the job queue."""
        with self._lock:
            if func is None:
                raise ValueError("func cannot be None")

            job = JobInfo(job_id=self._jobs_in, func=func, tag=tag, args=args, kwargs=kwargs)
            self._jobs_in += 1
            self._to_run_queue.append(job)

    def wait(self, callback: Optional[Callable[[JobInfo], None]] = None) -> None:
        """Wait for all jobs to complete."""
        if self._jobs_in == 0:
            return

        self._executor = ThreadPoolExecutor(max_workers=self._max_threads)

        try:
            futures: dict[Future[Any], JobInfo] = {}
            for job in self._to_run_queue:
                future = self._executor.submit(job.func, *job.args, **job.kwargs)
                futures[future] = job

            for future in as_completed(futures):
                job = futures[future]
                try:
                    future.result()
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
