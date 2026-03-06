"""Composition root - wire dependencies for the application."""

from emagrecimento.application.use_cases.build_report import BuildReportUseCase
from emagrecimento.application.use_cases.extract_pdf import ExtractPdfMetricsUseCase
from emagrecimento.application.use_cases.extract_user_info import ExtractUserInfoFromFiles
from emagrecimento.application.use_cases.extract_zip import ExtractZipDataUseCase
from emagrecimento.infrastructure.pdf_metrics_parser import WithingsPdfMetricsParser
from emagrecimento.infrastructure.pdf_reader import PypdfPdfReader
from emagrecimento.infrastructure.zip_reader import ZipFileZipReader


def create_extract_zip_use_case() -> ExtractZipDataUseCase:
    """Factory for ExtractZipDataUseCase."""
    return ExtractZipDataUseCase(zip_reader=ZipFileZipReader())


def create_extract_pdf_use_case() -> ExtractPdfMetricsUseCase:
    """Factory for ExtractPdfMetricsUseCase."""
    return ExtractPdfMetricsUseCase(
        pdf_reader=PypdfPdfReader(),
        metrics_parser=WithingsPdfMetricsParser(),
    )


def create_build_report_use_case() -> BuildReportUseCase:
    """Factory for BuildReportUseCase."""
    return BuildReportUseCase()


def create_extract_user_info_use_case() -> ExtractUserInfoFromFiles:
    """Factory for ExtractUserInfoFromFiles."""
    return ExtractUserInfoFromFiles()
