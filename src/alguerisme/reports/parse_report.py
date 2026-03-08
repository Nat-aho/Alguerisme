"""Parse report formatting and presentation."""

from jinja2 import Environment, PackageLoader, select_autoescape

from alguerisme.core.parser.models import LetterParseResults


class ParseReport:
    """
    Parser results report with multiple format outputs.

    This class takes computed results and provides formatted output
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
        results: LetterParseResults,
    ):
        """
        Initialize parse report.

        Parameters
        ----------
        results : LetterParseResults
            LetterParseResults instance containing results from each letter parse task
        """
        self.results = results

    def format_telegram(self) -> str:
        """
        Format report for Telegram.

        Returns
        -------
        str
            Markdown-formatted message for Telegram
        """
        template = self._jinja_env.get_template("telegram_parse_report.jinja2")

        return template.render(
            results=self.results,
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
        template = self._jinja_env.get_template("console_parse_report.jinja2")

        return template.render(
            results=self.results,
            failed_letters=self.results.failed_letters,
        ).strip()
