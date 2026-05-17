"""Takes document in several format and parses them into LLM ingestable format.
-Currently for the demo purpose I am just gonna make ingestor for .pdf files.
-Will add other features later.
"""

import logging 
from langchain_docling.loader import DoclingLoader, ExportType


pdf_path = ""

class Ingestor:

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def load_pdf(self):
        loader = DoclingLoader(
            file_path = self.pdf_path,
            export_type= ExportType.MARKDOWN
        )
        docs = loader.load()
        return docs 