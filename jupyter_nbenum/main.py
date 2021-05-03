import nbformat
import nbformat.v4 as nbf
import re
import sys
from typing import List, Callable
import argparse
import uuid


class Indexer:
    def __init__(self, in_roman: bool = False, no_verify: bool = False) -> None:
        self.index: List[int] = [0]
        self.formater: Callable[[int], str] = int_to_roman if in_roman else str
        self.no_verify = no_verify

    def get_index(self, level: int) -> str:
        if level >= len(self.index):
            self.index.extend([0] * (level + 1 - len(self.index)))

        self._update_index(level)
        return self._index2string(level)

    def _index2string(self, level: int) -> str:
        if (not self.no_verify) and (0 in self.index[: level + 1]):
            raise ValueError(f"Heading order at {self.index} is not valid.")
        return ".".join(map(self.formater, self.index[: level + 1])) + "."

    def _update_index(self, level: int) -> None:
        self.index[level] += 1
        self.index[level + 1 :] = [0 for _ in range(level + 1, len(self.index))]


def int_to_roman(n: int) -> str:
    # https://stackoverflow.com/questions/394574/code-golf-new-year-edition-integer-to-roman-numeral
    letters = "M,CM,D,CD,C,XC,L,XL,X,IX,V,IV,I".split(",")
    letter_vals = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    result = ""

    for l, v in zip(letters, letter_vals):
        c = n // v
        result += l * c
        n -= v * c
    return result or "0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index the headers in a jupyter notebook. If you dont want a cell to be indexed, tag it with `NOINDEX`"
    )
    parser.add_argument("--title_level", type=int, help="level of top level title", default=1)
    parser.add_argument("--stdout", help="print to stdout", action="store_true")
    parser.add_argument(
        "--no_verify", help="don't verify if heading order is valid.", action="store_true"
    )
    parser.add_argument("--roman", help="use roman numerals", action="store_true")
    parser.add_argument("--add_toc", help="add table of content", action="store_true")
    parser.add_argument("file", type=str, help="path to jupyter notebook")
    return parser.parse_args()


def main() -> None:
    TOC_CONTENT = []

    args = parse_args()

    title_level: int = args.title_level
    indexer = Indexer(args.roman, args.no_verify)

    with open(args.file, "r+") as f:
        notebook = nbformat.read(f, as_version=4)

    for cell in notebook["cells"]:
        if "NOINDEX" in cell["metadata"].get("tags", []):
            continue

        if cell["cell_type"] == "markdown":
            lines = cell["source"].split("\n")
            for i, line in enumerate(lines):
                is_header = re.search(r"^#+ ", line)
                if is_header:
                    m = re.search(
                        r"^(#+)\s+((\d\.)*\d\.?\s+)?(([0IXVMC]+\.)*[0IXVMC]+\.?\s+)?([^<]*)(<a[^>]*><\/a>)?$",
                        line,
                    )

                    if m is None:
                        continue

                    level = len(m.group(1))

                    _line = ""
                    _line += "#" * (level)
                    if level > title_level:
                        _idx = indexer.get_index(level - 1 - title_level)
                        _line += " " + _idx
                    _line += " " * 2 + m.group(6)

                    if args.add_toc and level > title_level:
                        _id = uuid.uuid1()
                        _line += f'<a class="anchor" id="{_id}"></a>'
                        TOC_CONTENT += [
                            "\t" * (level - 1 - title_level) + f"* [{_idx} {m.group(6)}](#{_id})"
                        ]

                    lines[0] = _line

            cell["source"] = "\n".join(lines)

    if args.add_toc:
        _toc_cells = [c for c in notebook["cells"] if "TOC" in c["metadata"].get("tags", [])]
        if _toc_cells:
            _toc_cell, *_ = _toc_cells
        else:
            _toc_cell = nbf.new_markdown_cell()
            notebook["cells"].insert(0, _toc_cell)

        _toc_cell["metadata"] = {"tags": ["TOC", "NOINDEX"]}
        _toc_cell["source"] = (
            "#" * (1 + args.title_level) + " Table of Content\n" + "\n".join(TOC_CONTENT)
        )

    with (sys.stdout if args.stdout else open(args.file, "w+")) as f:
        nbformat.write(notebook, f, version=4)


if __name__ == "__main__":
    main()
