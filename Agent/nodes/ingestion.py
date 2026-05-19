"""Takes document in several format and parses them into LLM ingestable format.
-Currently for the demo purpose I am just gonna make ingestor for .pdf files.
-Will add other features later.
"""

import logging 
from abc import abstractmethod, ABC
from typing import List, Any 
from langchain_docling.loader import DoclingLoader, ExportType

logging.basicConfig(
    level= logging.INFO,
    format= "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

class BasicDocumentIngestor(ABC):
    @abstractmethod
    def load(self, file_path: str) -> List[Any]:
        pass

# Inherit from BasicDocumentIngestor
class DoclingIngestor(BasicDocumentIngestor):
    def __init__(self, export_type: ExportType = ExportType.MARKDOWN):
        self.export_type = export_type
        logger.info("Initialize the Docling Ingestor with Export type MARKDOWN...")

    # Renamed to load to match the ABC
    def load(self, file_path:str) -> List[Any]:
        logger.info(f"Starting to load the pdf document: {file_path}")
        try:
            loader = DoclingLoader(
                file_path = file_path, # Fixed: removed 'self.'
                export_type= self.export_type # Fixed: uses the initialized export type
            )
            docs = loader.load()
            logger.info("Successfully Loaded the pdf file in MARKDOWN format...")
            return docs
        except FileNotFoundError:
            logger.error(f"Could not locate the file path: {file_path}. Please ensure that the file exists.")
            return []
        except Exception as e:
            logger.error(f"Some Error Occured: {e}. Please Try again. If the error persists put the issue in feedback.")
            return []
        
class DocumentPipeline:
    def __init__(self, ingestor: BasicDocumentIngestor):
        self.ingestor = ingestor 

    def process_batch(self, file_paths:List[Any]) -> List[Any]:
        all_documents =[]
        for path in file_paths:
            docs = self.ingestor.load(path)
            if docs:
                all_documents.extend(docs)
            logger.info(f"Batch Processing is completed. Total Documents Ingested {len(all_documents)}")
        return all_documents
           