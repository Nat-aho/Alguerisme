"""Jobs package for Alguerisme application."""

from alguerisme.jobs.crawler_job import run_crawl_job
from alguerisme.jobs.html_collector_job import run_html_collection_job
from alguerisme.jobs.html_update_apply_job import run_html_update_apply_job
from alguerisme.jobs.html_update_check_job import run_html_update_check_job

__all__ = [
    "run_crawl_job",
    "run_html_collection_job",
    "run_html_update_check_job",
    "run_html_update_apply_job",
]
