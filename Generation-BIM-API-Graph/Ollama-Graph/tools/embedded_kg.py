from pathlib import Path
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from .graph import vs_graph
from .llm import embedding_provider, llm
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_community.graphs.graph_document import Node, Relationship

load_dotenv()

# Default path for documents
DOCS_PATH = os.getenv('DOCS_PATH')
default_file_path = Path(DOCS_PATH) / 'data/vs.txt'


def process_document(file_path=None):
    """
    Process the document, vectorize the data, and prepare graph data.

    Args:
        file_path (str or Path): Path to the input file. If not provided, uses the default file path.
    """
    if not file_path:
        file_path = default_file_path

    # ------ Gather the data ------
    loader = TextLoader(str(file_path))  # Convert input_path to a string to use with TextLoader
    docs = loader.load()

    # ------ Chunk the data ------
    text_splitter = CharacterTextSplitter(
        separator="\ndef ",
        chunk_size=450,
        chunk_overlap=0,
    )
    chunks = text_splitter.split_documents(docs)

    # ------ Vectorize the data and Prepare Graph Data ------
    doc_transformer = LLMGraphTransformer(llm=llm)
    chunks_data = []
    graph_docs_batch = []

    # Batch size for embeddings
    batch_size = 10

    # Split chunks into batches
    batched_chunks = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]

    # Process each batch
    for batch in batched_chunks:
        batch_texts = [chunk.page_content for chunk in batch if chunk.page_content]

        # Get embeddings for the entire batch
        batch_embeddings = [embedding_provider.embed_query(text) for text in batch_texts]

        for chunk, chunk_embedding in zip(batch, batch_embeddings):
            if not chunk.page_content:
                continue

            # Extract the filename and metadata
            filename = os.path.basename(chunk.metadata["source"])
            chunk_id = f"{filename}.{chunks.index(chunk)}"
            print("chunk_id", chunk_id)

            # Collect properties for batch insertion into the graph
            properties = {
                "filename": filename,
                "chunk_id": chunk_id,
                "text": chunk.page_content,
                "textEmbedding": chunk_embedding
            }
            chunks_data.append(properties)

            # Generate graph documents for relationships
            graph_docs = doc_transformer.convert_to_graph_documents([chunk])
            if graph_docs:
                chunk_node = Node(id=chunk_id, type="Chunk")
                for graph_doc in graph_docs:
                    for node in graph_doc.nodes:
                        graph_doc.relationships.append(
                            Relationship(
                                source=chunk_node,
                                target=node,
                                type="HAS_ENTITY"
                            )
                        )
                graph_docs_batch.extend(graph_docs)

    # ------ Batch Insert Chunks into the Graph ------
    print("Batch Insert Chunks into the Graph")
    vs_graph.query(
        """
        UNWIND $chunks_data AS chunk
        MERGE (d:Document {id: chunk.filename})
        MERGE (c:Chunk {id: chunk.chunk_id})
        SET c.text = chunk.text
        MERGE (d)<-[:PART_OF]-(c)
        WITH c, chunk
        CALL db.create.setNodeVectorProperty(c, 'textEmbedding', chunk.textEmbedding)
        """,
        {"chunks_data": chunks_data}
    )

    # ------ Add Graph Documents (Nodes and Relationships) to the Graph ------
    if graph_docs_batch:
        print("graph_docs_batch")
        vs_graph.add_graph_documents(graph_docs_batch)

    # ------ Create the Vector Index ------
    print("VectorIndex")
    vs_graph.query(
        """
        CREATE VECTOR INDEX `vector`
        FOR (c: Chunk) ON (c.textEmbedding)
        OPTIONS {indexConfig: {
        `vector.dimensions`: 1024,
        `vector.similarity_function`: 'cosine'
        }};
        """
    )


# Callable function for external use
def run_embedded(file_path=None):
    """
    Entry point to run the document processing workflow.

    Args:
        file_path (str or Path): Path to the input file. If not provided, uses the default file path.
    """
    process_document(file_path)


# Ensure the script runs only when executed directly
if __name__ == "__main__":
    run_embedded()
