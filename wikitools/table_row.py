import typing


class TableRow(typing.List[str]):
    header: typing.List[str]

    def __init__(self, row: typing.Optional[typing.List[str]] = None, header: typing.Optional[typing.List[str]] = None):
        if header:
            self.header = header
        if row:
            for cell in row:
                self.append(cell)

    def get(self, key: str):
        # TODO: may raise a ValueError
        return self[self.header.index(key)]
