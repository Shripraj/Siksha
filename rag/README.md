# RAG pipeline scaffold

Production pipeline:
1. Parse PDF/DOCX/TXT/CSV/XLSX syllabus material.
2. Normalize and chunk text.
3. Attach school_id, class_id, subject_id, chapter_id and topic_id metadata.
4. Embed chunks with a local/hosted embedding model.
5. Store vectors in FAISS or another vector database.
6. Retrieve only within the student's school/subject/topic scope.
7. Send retrieved context to Groq for lesson explanations and assessment generation.
8. Log source chunk IDs for traceability.

This demo includes the assessment and upload interfaces but intentionally keeps the heavy ingestion worker as a separate production concern.
