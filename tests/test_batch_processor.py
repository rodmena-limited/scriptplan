import unittest

from scriptplan.scheduler.batch_processor import BatchProcessor, JobInfo, ThreadBatchProcessor


def simple_add(a, b):
    """Simple function for testing."""
    return a + b


def simple_square(x):
    """Simple function for testing."""
    return x * x


def failing_function():
    """Function that raises an exception."""
    raise ValueError("Test error")


class TestJobInfo(unittest.TestCase):
    def test_job_info_init(self):
        job = JobInfo(job_id=1, func=simple_add, tag="test_tag")
        self.assertEqual(job.job_id, 1)
        self.assertEqual(job.func, simple_add)
        self.assertEqual(job.tag, "test_tag")
        self.assertIsNone(job.pid)
        self.assertIsNone(job.ret_val)
        self.assertEqual(job.stdout, '')
        self.assertEqual(job.stderr, '')

    def test_job_info_aliases(self):
        job = JobInfo(job_id=1, func=simple_add)
        self.assertEqual(job.jobId, 1)
        self.assertIsNone(job.retVal)


class TestBatchProcessor(unittest.TestCase):
    def test_init(self):
        bp = BatchProcessor(max_cpu_cores=4)
        self.assertEqual(bp.maxCpuCores, 4)

    def test_init_default_cores(self):
        bp = BatchProcessor()
        self.assertGreater(bp.maxCpuCores, 0)

    def test_empty_wait(self):
        bp = BatchProcessor(max_cpu_cores=2)
        # Should not raise any exception
        bp.wait()


class TestThreadBatchProcessor(unittest.TestCase):
    def test_init(self):
        bp = ThreadBatchProcessor(max_threads=4)
        self.assertIsNotNone(bp)

    def test_queue_and_wait(self):
        bp = ThreadBatchProcessor(max_threads=2)
        results = []

        def record_result(job):
            results.append(job)

        bp.queue(tag="job1", func=simple_square, x=5)
        bp.queue(tag="job2", func=simple_square, x=10)
        bp.wait(callback=record_result)

        self.assertEqual(len(results), 2)
        for job in results:
            self.assertEqual(job.ret_val, 0)

    def test_queue_with_args(self):
        bp = ThreadBatchProcessor(max_threads=2)
        results = []

        def record_result(job):
            results.append(job)

        bp.queue(tag="add", func=simple_add, a=3, b=4)
        bp.wait(callback=record_result)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ret_val, 0)

    def test_empty_wait(self):
        bp = ThreadBatchProcessor(max_threads=2)
        # Should not raise any exception
        bp.wait()

    def test_reuse(self):
        bp = ThreadBatchProcessor(max_threads=2)

        # First run
        bp.queue(tag="job1", func=simple_square, x=2)
        bp.wait()

        # Second run - should work after reset
        bp.queue(tag="job2", func=simple_square, x=3)
        bp.wait()

    def test_failing_job(self):
        bp = ThreadBatchProcessor(max_threads=2)
        results = []

        def record_result(job):
            results.append(job)

        bp.queue(tag="fail", func=failing_function)
        bp.wait(callback=record_result)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ret_val, 1)
        self.assertIn("Test error", results[0].stderr)


if __name__ == '__main__':
    unittest.main()
