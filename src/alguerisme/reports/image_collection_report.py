"""Image collection report formatting and presentation."""

from jinja2 import Environment, PackageLoader, select_autoescape

from alguerisme.core.image_collector.models import (
    LetterImageCollectionResults,
)


class ImageCollectionReport:
    """Image collection results report with multiple format outputs.

    This class provides formatted output for different notification channels
    using Jinja2 templates. Accepts letter-level results for detailed reporting.
    """

    _jinja_env = Environment(
        loader=PackageLoader("alguerisme.reports", "templates"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def __init__(self, results: LetterImageCollectionResults):
        """Initialize image collection report.

        Parameters
        ----------
        results : LetterImageCollectionResults
            LetterImageCollectionResults instance containing results from each
            letter image collection task

        """
        self.results = results
        self.total_stats = results.total_stats

    def format_telegram(self) -> str:
        """Format report for Telegram.

        Returns
        -------
        str
            Markdown-formatted message for Telegram

        """
        template = self._jinja_env.get_template(
            "telegram_image_collection_report.jinja2"
        )

        return template.render(
            stats=self.total_stats,
            successful_results=self.results.successful_results,
            failed_results=self.results.failed_results,
            successful_letters=self.results.successful_letters,
            failed_letters=self.results.failed_letters,
        ).strip()

    def format_console(self) -> str:
        """Format report for console/logs.

        Returns
        -------
        str
            Plain text summary for logging

        """
        template = self._jinja_env.get_template(
            "console_image_collection_report.jinja2"
        )

        return template.render(
            stats=self.total_stats,
            failed_letters=self.results.failed_letters,
        ).strip()
