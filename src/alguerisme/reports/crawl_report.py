"""Crawl report formatting and presentation."""

from jinja2 import Environment, PackageLoader, select_autoescape

from alguerisme.core.crawler.models import CrawlMetrics, CrawlServiceStats


class CrawlReport:
    """
    Crawler results report with multiple format outputs.

    This class takes computed metrics and provides formatted output
    for different notification channels using Jinja2 templates.
    """

    _jinja_env = Environment(
        loader=PackageLoader("alguerisme.reports", "templates"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def __init__(
        self,
        results: list[CrawlServiceStats],
    ):
        """
        Initialize crawl report.

        Parameters
        ----------
        results : list[CrawlServiceStats]
            List of statistics from each letter crawl task
        template : ReportTemplate, optional
            Template configuration. Uses default if not provided.
        """
        self.metrics = CrawlMetrics.from_results(results)

    def format_telegram(self) -> str:
        """
        Format report for Telegram.

        Returns
        -------
        str
            Markdown-formatted message for Telegram
        """
        template = self._jinja_env.get_template("telegram_crawl_report.jinja2")
        return template.render(
            metrics=self.metrics,
        ).strip()

    def format_console(self) -> str:
        """
        Format report for console/logs.

        Returns
        -------
        str
            Plain text summary for logging
        """
        template = self._jinja_env.get_template("console_crawl_report.jinja2")
        return template.render(metrics=self.metrics).strip()
