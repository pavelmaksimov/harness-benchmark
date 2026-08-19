import unittest

from benchmark.eval_deps_hook import _without_eval_framework_requirements


class EvalDepsHookTests(unittest.TestCase):
    def test_filters_pytest_packages_and_preserves_solution_dependencies(self) -> None:
        requirements = (
            "fastapi==0.115.6\n"
            "pytest==8.3.4\n"
            "pytest-cov>=5\n"
            "git+https://example.com/example.git\n"
            "# keep comments\n"
        )

        self.assertEqual(
            _without_eval_framework_requirements(requirements),
            "fastapi==0.115.6\n"
            "git+https://example.com/example.git\n"
            "# keep comments\n",
        )


if __name__ == "__main__":
    unittest.main()
