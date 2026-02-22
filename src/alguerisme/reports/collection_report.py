"""Collection report formatting and presentation."""

from jinja2 import Environment, PackageLoader, select_autoescape

from alguerisme.core.collector.models import (
    CollectionMetrics,
    LetterCollectionResults,
)


class CollectionReport:
    """
    Collection results report with multiple format outputs.

    This class provides formatted output for different notification channels
    using Jinja2 templates. Accepts letter-level results for detailed reporting.
    """

    _jinja_env = Environment(
        loader=PackageLoader("alguerisme.reports", "templates"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def __init__(
        self,
        results: LetterCollectionResults,
        collection_type: str = "new",
    ):
        """
        Initialize collection report.

        Parameters
        ----------
        results : LetterCollectionResults
            LetterCollectionResults instance containing results from each
            letter collection task
        collection_type : str
            Type of collection: "new" or "update_check"
        """
        self.results = results
        self.metrics = CollectionMetrics.from_results(results, collection_type)

    def format_telegram(self) -> str:
        """
        Format report for Telegram.

        Returns
        -------
        str
            Markdown-formatted message for Telegram
        """
        template = self._jinja_env.get_template("telegram_collection_report.jinja2")

        return template.render(
            metrics=self.metrics,
            successful_results=self.results.successful_results,
            failed_results=self.results.failed_results,
        ).strip()

    def format_console(self) -> str:
        """
        Format report for console/logs.

        Returns
        -------
        str
            Plain text summary for logging
        """
        template = self._jinja_env.get_template("console_collection_report.jinja2")

        return template.render(
            metrics=self.metrics,
            failed_letters=self.results.failed_letters,
        ).strip()
