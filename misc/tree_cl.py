#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
from pathlib import Path
from typing import Iterable, List, Tuple, Optional
import fnmatch

TREE_BRANCH = "├── "
TREE_LAST = "└── "
TREE_PIPE = "│   "
TREE_SPACE = "    "

DEFAULT_EXCLUDES = [
    ".git", ".hg", ".svn", ".DS_Store", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".venv", "venv", "env", ".idea", ".vscode",
    "node_modules", "dist", "build", ".coverage", ".ruff_cache",
]

def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024.0

def should_exclude(path: Path, exclude_globs: List[str]) -> bool:
    name = path.name
    for pattern in exclude_globs:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
            return True
    return False

def list_dir_sorted(path: Path) -> Tuple[List[Path], List[Path]]:
    try:
        entries = list(path.iterdir())
    except PermissionError:
        return [], []
    dirs = sorted([e for e in entries if e.is_dir()], key=lambda p: p.name.lower())
    files = sorted([e for e in entries if e.is_file()], key=lambda p: p.name.lower())
    return dirs, files

def safe_count_lines(file_path: Path) -> Optional[int]:
    """Conta linhas com tolerância a encoding. Retorna None em erro."""
    try:
        # Tenta utf-8 primeiro
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return None

def build_tree(
    root: Path,
    prefix: str,
    show_hidden: bool,
    exclude_globs: List[str],
    max_depth: Optional[int],
    current_depth: int,
    show_sizes: bool,
    count_ext: Optional[str],
    totals: dict,
) -> Iterable[str]:
    if max_depth is not None and current_depth >= max_depth:
        return

    dirs, files = list_dir_sorted(root)

    def visible(p: Path) -> bool:
        hidden = p.name.startswith(".")
        if hidden and not show_hidden:
            return False
        if should_exclude(p, exclude_globs):
            return False
        return True

    dirs = [d for d in dirs if visible(d)]
    files = [f for f in files if visible(f)]

    entries = [(d, True) for d in dirs] + [(f, False) for f in files]

    for idx, (entry, is_dir) in enumerate(entries):
        connector = TREE_LAST if idx == len(entries) - 1 else TREE_BRANCH
        line = prefix + connector + entry.name

        line_suffix_parts = []

        # Tamanho de arquivo (se aplicável)
        if not is_dir and show_sizes:
            try:
                size = human_size(entry.stat().st_size)
                line_suffix_parts.append(f"{size}")
            except OSError:
                pass

        # Contagem de linhas (se extensão casar)
        if not is_dir and count_ext:
            if entry.suffix.lower() == count_ext:
                n_lines = safe_count_lines(entry)
                if n_lines is not None:
                    line_suffix_parts.append(f"{n_lines} linhas")
                    totals["total_lines"] += n_lines
                    totals["files_counted"] += 1
                else:
                    line_suffix_parts.append("erro ao ler")

        if line_suffix_parts:
            line += "  (" + ", ".join(line_suffix_parts) + ")"

        yield line

        if is_dir:
            extension = TREE_SPACE if idx == len(entries) - 1 else TREE_PIPE
            new_prefix = prefix + extension
            yield from build_tree(
                entry,
                new_prefix,
                show_hidden,
                exclude_globs,
                max_depth,
                current_depth + 1,
                show_sizes,
                count_ext,
                totals,
            )

def print_tree(
    path: Path,
    show_hidden: bool = False,
    exclude: List[str] = None,
    include_defaults: bool = True,
    max_depth: Optional[int] = None,
    show_sizes: bool = False,
    header: bool = True,
    count_lines_ext: Optional[str] = None,
):
    path = path.resolve()
    if not path.exists():
        print(f"Erro: caminho não encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    exclude_globs = []
    if include_defaults:
        exclude_globs.extend(DEFAULT_EXCLUDES)
    if exclude:
        exclude_globs.extend(exclude)

    # Normaliza extensão para formato ".ext"
    count_ext = None
    if count_lines_ext:
        count_ext = count_lines_ext if count_lines_ext.startswith(".") else f".{count_lines_ext}"
        count_ext = count_ext.lower()

    if header:
        print(path.name)
        print(TREE_BRANCH[:-1])  # "├──" -> "├─"

    totals = {"total_lines": 0, "files_counted": 0}

    for line in build_tree(
        path,
        prefix="",
        show_hidden=show_hidden,
        exclude_globs=exclude_globs,
        max_depth=max_depth,
        current_depth=0,
        show_sizes=show_sizes,
        count_ext=count_ext,
        totals=totals,
    ):
        print(line)

    if count_ext:
        print()
        print(f"Total de linhas em arquivos '*{count_ext}': {totals['total_lines']} (arquivos contados: {totals['files_counted']})")

def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Imprime a estrutura de diretórios/arquivos em formato de árvore, com opções de exclusão, profundidade e contagem de linhas por extensão."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Caminho da pasta alvo (padrão: .)",
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Mostrar arquivos ocultos (que começam com ponto).",
    )
    parser.add_argument(
        "-x", "--exclude",
        action="append",
        default=[],
        help="Padrões/globs para excluir (pode repetir). Ex: -x '*.log' -x 'dist'",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Não aplicar exclusões padrão (como .git, node_modules, etc).",
    )
    parser.add_argument(
        "-d", "--max-depth",
        type=int,
        default=None,
        help="Profundidade máxima de navegação (ex.: 2).",
    )
    parser.add_argument(
        "-s", "--sizes",
        action="store_true",
        help="Mostrar tamanhos de arquivos.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Não imprimir o cabeçalho com o nome da pasta raiz.",
    )
    parser.add_argument(
        "-cl", "--count-lines",
        dest="count_lines_ext",
        type=str,
        default=None,
        metavar="EXT",
        help="Conta linhas de arquivos com a extensão informada (ex.: py, js, .ts). Mostra por arquivo e total ao final.",
    )

    parser.add_argument(
        "--up",
        type=int,
        default=None,
        help="Sobe N níveis a partir do diretório onde este script está localizado.",
    )
    
    return parser.parse_args(argv)

def main(argv: List[str] = None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.up is not None:
        if args.up < 0:
            print("Erro: --up deve ser um número inteiro maior ou igual a zero.", file=sys.stderr)
            sys.exit(1)

        script_dir = Path(__file__).resolve().parent
        target = script_dir

        for _ in range(args.up):
            target = target.parent
    else:
        target = Path(args.path)

    print_tree(
        target,
        show_hidden=args.all,
        exclude=args.exclude,
        include_defaults=not args.no_default_excludes,
        max_depth=args.max_depth,
        show_sizes=args.sizes,
        header=not args.no_header,
        count_lines_ext=args.count_lines_ext,
    )

if __name__ == "__main__":
    main()