import logging
from abc import ABC, abstractmethod
from langchain_docling.loader import DoclingLoader, ExportType
from langchain_community.document_loaders import UnstructuredMarkdownLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BasicDocumentIngestor(ABC):
    @abstractmethod
    def load(self, file_path: str) -> str:  # always returns raw string
        pass


class DoclingIngestor(BasicDocumentIngestor):
    def __init__(self, export_type: ExportType = ExportType.MARKDOWN):
        self.export_type = export_type
        logger.info("Initialized DoclingIngestor with export type MARKDOWN")

    def load(self, file_path: str) -> str:
        logger.info(f"Loading PDF: {file_path}")
        try:
            loader = DoclingLoader(file_path=file_path, export_type=self.export_type)
            docs = loader.load()
            raw_text = "\n\n".join(doc.page_content for doc in docs)
            logger.info("Successfully loaded PDF as markdown text")
            return raw_text
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            return ""


class MarkDownLoader(BasicDocumentIngestor):
    def load(self, file_path: str) -> str:  
        logger.info(f"Loading markdown: {file_path}")
        try:
            loader = UnstructuredMarkdownLoader(file_path=file_path, mode="single")
            docs = loader.load()
            raw_text = "\n\n".join(doc.page_content for doc in docs)
            logger.info("Successfully loaded markdown file")
            return raw_text
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"Error loading markdown: {e}")
            return ""