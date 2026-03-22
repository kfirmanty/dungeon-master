"""
CLI entry point — the user-facing interface to BookWorm.

Commands:
    bookworm ingest --title "Title" /path/to/book.txt
    bookworm ask "What happens in chapter 3?"
    bookworm ask --book "Title" "What happens?"
    bookworm list
    bookworm remove --title "Title"
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bookworm.config import get_settings
from bookworm.db.connection import get_connection, register_vector_type
from bookworm.db.migrations import run_migrations
from bookworm.db import repository
from bookworm.embeddings.local import TransformerEmbeddingProvider
from bookworm.llm.ollama import OllamaProvider
from bookworm.ingestion.pipeline import ingest_book
from bookworm.retrieval.pipeline import query

app = typer.Typer(help="BookWorm — Ask questions about your books using RAG")
console = Console()


def _setup():
    """Initialize database connection, run migrations, and create providers.

    This is called by every command. In a larger app you'd use dependency
    injection, but for a CLI this direct approach is clearer.
    """
    settings = get_settings()

    try:
        conn = get_connection(settings.database_url)
    except ConnectionError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    run_migrations(conn)
    register_vector_type(conn)  # must come AFTER migrations create the vector extension

    embedding_provider = TransformerEmbeddingProvider(model_name=settings.embedding_model)
    llm_provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )

    return settings, conn, embedding_provider, llm_provider


@app.command()
def ingest(
    file_path: Path = typer.Argument(..., help="Path to the .txt or .md book file"),
    title: str = typer.Option(..., "--title", "-t", help="Book title"),
):
    """Ingest a book: read, chunk, embed, and store in the database."""
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(code=1)

    if file_path.suffix.lower() not in (".txt", ".md", ".markdown"):
        console.print("[yellow]Warning: BookWorm supports .txt and .md files. Other formats may not work correctly.[/yellow]")

    settings, conn, embedding_provider, _ = _setup()

    try:
        ingest_book(file_path, title, settings, conn, embedding_provider)
    except Exception as e:
        console.print(f"[red]Ingestion failed: {e}[/red]")
        raise typer.Exit(code=1)
    finally:
        conn.close()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your question about the book"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Book title to search (default: most recent)"),
):
    """Ask a question about an ingested book."""
    settings, conn, embedding_provider, llm_provider = _setup()

    try:
        # Resolve the target book
        if book:
            book_meta = repository.get_book_by_title(conn, book)
            if not book_meta:
                console.print(f"[red]Book not found: '{book}'[/red]")
                console.print("Use [bold]bookworm list[/bold] to see ingested books.")
                raise typer.Exit(code=1)
        else:
            book_meta = repository.get_latest_book(conn)
            if not book_meta:
                console.print("[red]No books ingested yet.[/red]")
                console.print("Use [bold]bookworm ingest[/bold] to add a book first.")
                raise typer.Exit(code=1)

        console.print(f"Searching '{book_meta.title}'...\n")

        result = query(
            question=question,
            settings=settings,
            conn=conn,
            embedding_provider=embedding_provider,
            llm_provider=llm_provider,
            book_id=book_meta.id,
            book_title=book_meta.title,
        )

        # Print the answer
        console.print("[bold]Answer:[/bold]")
        console.print(result.answer)

        # Print sources for transparency — a key RAG feature
        if result.sources:
            console.print("\n[dim]Sources:[/dim]")
            for src in result.sources:
                chapter = f"Ch.{src.chapter_number}" if src.chapter_number else "?"
                title_str = f" ({src.chapter_title})" if src.chapter_title else ""
                sim = f"{src.similarity_score:.2f}"
                # Show a preview of the chunk (first 80 chars)
                preview = src.content[:80].replace("\n", " ") + "..."
                console.print(f"  [dim]{chapter}{title_str} [sim={sim}]: {preview}[/dim]")

    except ConnectionError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    finally:
        conn.close()


@app.command(name="list")
def list_books():
    """List all ingested books."""
    settings, conn, _, _ = _setup()

    try:
        books = repository.list_books(conn)

        if not books:
            console.print("No books ingested yet. Use [bold]bookworm ingest[/bold] to add one.")
            return

        table = Table(title="Ingested Books")
        table.add_column("Title", style="bold")
        table.add_column("File")
        table.add_column("Ingested At")
        table.add_column("ID", style="dim")

        for book in books:
            table.add_row(
                book.title,
                book.file_path,
                book.ingested_at.strftime("%Y-%m-%d %H:%M") if book.ingested_at else "?",
                str(book.id)[:8] + "...",
            )

        console.print(table)
    finally:
        conn.close()


@app.command()
def remove(
    title: str = typer.Option(..., "--title", "-t", help="Title of the book to remove"),
):
    """Remove a book and all its chunks from the database."""
    settings, conn, _, _ = _setup()

    try:
        book = repository.get_book_by_title(conn, title)
        if not book:
            console.print(f"[red]Book not found: '{title}'[/red]")
            raise typer.Exit(code=1)

        repository.delete_book(conn, book.id)
        console.print(f"Removed '{book.title}' and all its chunks.")
    finally:
        conn.close()
