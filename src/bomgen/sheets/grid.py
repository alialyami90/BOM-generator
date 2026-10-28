"""A small mutable builder for one sheet, and A1-style references across sheets."""

from bomgen.models.sheet import (
    Borders,
    BorderStyle,
    Cell,
    CellStyle,
    CellValue,
    ColumnFormat,
    HeaderFooter,
    Merge,
    PrintSetup,
    RowFormat,
    SheetModel,
    cell_name,
)


def quote_sheet(name: str) -> str:
    """The sheet name as a formula prefix, always quoted (``'1'``, ``'O''Brien'``)."""
    return "'" + name.replace("'", "''") + "'"


def ref(sheet: str, row: int, col: int) -> str:
    """A reference to one cell on another sheet, e.g. ``'1'!C8``."""
    return f"{quote_sheet(sheet)}!{cell_name(row, col)}"


class SheetBuilder:
    """Collects cells, merges and dimensions, then freezes them into a ``SheetModel``."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._cells: dict[tuple[int, int], Cell] = {}
        self._merges: list[Merge] = []
        self._rows: dict[int, RowFormat] = {}
        self._columns: dict[int, ColumnFormat] = {}

    def set(
        self, row: int, col: int, value: CellValue = None, style: CellStyle | None = None
    ) -> None:
        self._cells[(row, col)] = Cell(value=value, style=style)

    def merge(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        value: CellValue = None,
        style: CellStyle | None = None,
    ) -> None:
        """Merge a range; ``value`` and ``style`` go on its top-left cell."""
        self.set(first_row, first_col, value, style)
        self.span(first_row, first_col, last_row, last_col)

    def span(self, first_row: int, first_col: int, last_row: int, last_col: int) -> None:
        """Merge a range, keeping the top-left cell as it was written."""
        self._merges.append(
            Merge(first_row=first_row, first_col=first_col, last_row=last_row, last_col=last_col)
        )

    def height(self, row: int, height: float) -> None:
        self._rows[row] = RowFormat(height=height)

    def width(self, col: int, width: float | None = None, *, hidden: bool = False) -> None:
        self._columns[col] = ColumnFormat(width=width, hidden=hidden)

    def box(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        *,
        outer: BorderStyle,
        inner: BorderStyle = BorderStyle.NONE,
    ) -> None:
        """Re-border every cell of the range: ``outer`` on its edges, ``inner`` between cells.

        A merge inside the range counts as one cell; empty cells get a plain style.
        """
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                span = self._span_of(row, col)
                if span is None:
                    continue  # covered by a merge; its anchor carries the borders
                top, left, bottom, right = span

                def side(on_edge: bool) -> BorderStyle:
                    return outer if on_edge else inner

                borders = Borders(
                    top=side(top == first_row),
                    left=side(left == first_col),
                    bottom=side(bottom == last_row),
                    right=side(right == last_col),
                )
                cell = self._cells.get((row, col), Cell())
                style = (cell.style or CellStyle()).model_copy(update={"borders": borders})
                self._cells[(row, col)] = cell.model_copy(update={"style": style})

    def _span_of(self, row: int, col: int) -> tuple[int, int, int, int] | None:
        """The (top, left, bottom, right) of the cell or merge anchored here; None if covered."""
        for merge in self._merges:
            if merge.contains(row, col):
                if (row, col) != (merge.first_row, merge.first_col):
                    return None
                return merge.first_row, merge.first_col, merge.last_row, merge.last_col
        return row, col, row, col

    @property
    def last_row(self) -> int:
        rows = [row for row, _col in self._cells] + [m.last_row for m in self._merges]
        return max(rows, default=0)

    def build(
        self, print_setup: PrintSetup, header_footer: HeaderFooter | None = None
    ) -> SheetModel:
        covered = {
            (row, col)
            for merge in self._merges
            for row in range(merge.first_row, merge.last_row + 1)
            for col in range(merge.first_col, merge.last_col + 1)
            if (row, col) != (merge.first_row, merge.first_col)
        }
        return SheetModel(
            name=self.name,
            cells={key: cell for key, cell in self._cells.items() if key not in covered},
            merges=tuple(self._merges),
            columns=dict(self._columns),
            rows=dict(self._rows),
            print_setup=print_setup,
            header_footer=header_footer,
        )
