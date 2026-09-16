"""
Frontend Document Ingestion Component.

Provides secure document upload, client-side file-type whitelisting (.pdf, .txt, .md),
size bounds enforcement, and detailed ingestion telemetry from Qdrant vector database.
"""

import streamlit as st
from pathlib import Path
from frontend.services.api_client import EnterpriseAPIClient


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


def render_documents_view(client: EnterpriseAPIClient):
    """Renders the Knowledge Ingestion Portal."""
    st.markdown("### 📄 Enterprise Knowledge Ingestion")
    st.caption(
        "Upload corporate policies, handbooks, and standard operating procedures. "
        "Uploaded files are chunked semantically, embedded, and indexed into Qdrant vector store."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Upload Policy Document")
        uploaded_file = st.file_uploader(
            "Choose a file to ingest",
            type=["pdf", "txt", "md"],
            help="Strict portfolio security policy allows only .pdf, .txt, and .md files up to 10MB.",
        )

        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_size = uploaded_file.size
            suffix = Path(file_name).suffix.lower()

            st.info(f"📁 Selected: **`{file_name}`** ({file_size / 1024:.1f} KB)")

            # Validation check
            if suffix not in ALLOWED_EXTENSIONS:
                st.error(f"❌ Security violation: Unsupported file type '{suffix}'. Allowed: .pdf, .txt, .md")
            elif file_size > MAX_FILE_SIZE_BYTES:
                st.error(f"❌ File exceeds maximum allowed size of 10MB ({file_size / (1024*1024):.2f} MB).")
            else:
                if st.button("⚡ Start Ingestion Pipeline", use_container_width=True):
                    with st.spinner("Processing document: loading, chunking, embedding, and indexing into Qdrant..."):
                        file_bytes = uploaded_file.getvalue()
                        ingest_result = client.upload_and_ingest(file_name, file_bytes)

                    if ingest_result.success and ingest_result.data:
                        report = ingest_result.data
                        st.success("✅ Document successfully indexed into enterprise vector store!")

                        # Render metrics row
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Documents Loaded", report.get("documents_loaded", 1))
                        m2.metric("Chunks Created", report.get("chunks_created", 0))
                        m3.metric("Vectors Upserted", report.get("vectors_upserted", 0))
                        m4.metric("Total in Collection", report.get("total_vectors_in_collection", 0))

                        st.caption(f"Elapsed Pipeline Time: `{report.get('elapsed_seconds', 0.0):.2f}s`")

                        with st.expander("Detailed Pipeline Logs", expanded=False):
                            st.json(report.get("details", []))
                    else:
                        st.error(f"❌ Ingestion failed ({ingest_result.status_code}): {ingest_result.error}")

    with col2:
        st.markdown("#### Ingestion Guidelines")
        st.markdown(
            """
            - **Allowed Formats:** `.pdf`, `.txt`, `.md`
            - **Max File Size:** 10 MB per file
            - **Vector Index:** Qdrant HNSW Collection
            - **Embedding Model:** Google `text-embedding-004` (or fallback)
            - **Chunking Strategy:** Recursive semantic chunker (800-token window with 150-token overlap)
            """
        )

        st.markdown("---")
        st.markdown("#### Sample Corporate Policies")
        policies_dir = Path("data/documents")
        if policies_dir.exists():
            files = list(policies_dir.glob("*"))
            if files:
                st.write(f"Found {len(files)} files in `data/documents`:")
                for f in files[:5]:
                    st.code(f.name, language="text")
            else:
                st.caption("No files currently staged in `data/documents/`.")
