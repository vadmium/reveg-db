#! /usr/bin/env python3
# coding=UTF-8

from OleFileIO_PL import OleFileIO
from struct import Struct
from io import SEEK_SET, SEEK_CUR, SEEK_END
from io import BufferedIOBase, UnsupportedOperation
from shorthand import bitmask
from io import TextIOWrapper, BytesIO
from shutil import copyfileobj

class Subfile(BufferedIOBase):
    def readable(self):
        return True
    
    def __init__(self, parent, size):
        self._parent = parent
        self._size = size
    
    def read(self, size=-1):
        if size < 0 or size is None or size > self._size:
            size = self._size
        self._size -= size
        result = self._parent.read(size)
        if len(result) < size:
            raise EOFError("Truncated read")
        return result
    read1 = read
    
    def seek(self, offset, base=SEEK_SET):
        if base == SEEK_END:
            raise UnsupportedOperation("SEEK_END")
        if base == SEEK_SET:
            offset -= self.tell()
        if offset > self._size:
            raise EOFError("Seek past end")
        self._size -= offset
        return self._parent.seek(offset, SEEK_CUR)
    
    def tell(self):
        return self._parent.tell()

unsigned2 = Struct("<H")
signed2 = Struct("<h")
unsigned4 = Struct("<L")
FibBase = Struct("<"
    "H"  # wIdent
    "H"  # nFib
    "2x"
    "H"  # lid
    "H"  # pnNext
    "BB"  # Bitfields
    "H"  # nFibBack
    "L"  # lKey
    "B"  # envr
    "B"  # Bitfields
    "2x 2x 4x 4x"
)
WORD_BINARY_FILE = 0xA5EC
WHICH_TBL_STM_BIT = 1
FibRgFcLcb97 = Struct("<"
    "104x"
    "LL"  # fcPlcfBtePapx, lcbPlcfBtePapx
    "152x"
    "LL"  # fcClx, lcbClx
)
Pcd = Struct("<"  # Piece descriptor
    "H"  # Bitfields
    "L"  # fc
    "H"  # prm
)
FC_MASK = bitmask(30)
COMPRESSED_BIT = 30
PN_MASK = bitmask(22)
SGC_BIT = 10
SGC_MASK = bitmask(3)
PARAGRAPH = 1
TABLE = 5
SPRA_BIT = 13
SPRA_MASK = bitmask(3)
PROP_MASK = bitmask(9 + 1 + 3)
sprmPChgTabs = 0x0615
sprmPFInTable = 0x0416
sprmPFTtp = 0x0417
sprmPHugePapx = 0x0646
sprmTDefTable = 0x1608
SPRA_SIZES = {0: 1, 1: 1, 2: 2, 3: 4, 4: 2, 5: 2, 7: 3}

def iter_pieces(doc, table, fcClx, lcbClx):
    table.seek(fcClx)
    subfile = Subfile(table, lcbClx)
    while True:
        clxt = subfile.read(1)
        if clxt != b"\x01":
            break
        [cbGrpprl] = signed2.unpack(subfile.read(2))
        assert cbGrpprl >= 0
        subfile.seek(cbGrpprl, SEEK_CUR)
    assert clxt == b"\x02"
    [lcb] = unsigned4.unpack(subfile.read(4))
    assert lcb >= 4
    [n, remainder] = divmod(lcb - 4, 4 + Pcd.size)
    assert not remainder
    [cp] = unsigned4.unpack(subfile.read(4))
    aCP1 = subfile.tell()
    aPcd = aCP1 + n * 4
    for i in range(n):
        subfile.seek(aPcd + i * Pcd.size)
        [_, fc, prm] = Pcd.unpack(subfile.read(Pcd.size))
        assert prm == 0x0000
        subfile.seek(aCP1 + i * 4)
        [next_cp] = unsigned4.unpack(subfile.read(4))
        assert next_cp > cp
        size = next_cp - cp
        fCompressed = fc >> COMPRESSED_BIT & 1
        fc &= FC_MASK
        yield Piece(doc, size, fCompressed, fc)
        cp = next_cp

class Piece:
    def __init__(self, doc, size, fCompressed, fc):
        self._doc = doc
        self._decoder = Cp1252Decoder if fCompressed else Utf16Decoder
        self.code_size = self._decoder.code_size
        self.bytes_remaining = size * self.code_size
        [self.byte_offset, remainder] = divmod(fc, 2 // self.code_size)
        assert not remainder
    
    def get_reader(self, size=None):
        if size is None:
            size = self.bytes_remaining
        else:
            assert not size % self.code_size
        self.bytes_remaining -= size
        self._doc.seek(self.byte_offset)
        self.byte_offset += size
        reader = self._decoder.reader_cls(self._doc, size)
        return TextIOWrapper(reader, self._decoder.encoding, newline="\r")

class Cp1252Decoder:
    code_size = 1
    encoding = "cp1252"
    
    class reader_cls(Subfile):
        def read(self, *args):
            text = super().read(*args)
            assert {0x80, 0x8E, 0x9E}.isdisjoint(text)
            return text

class Utf16Decoder:
    code_size = 2
    encoding = "utf-16-le"
    reader_cls = Subfile

def parse_prop_list(prl, ole):
    in_table = False
    is_ttp = False
    while True:
        sprm = prl.read(2)
        if not sprm:
            break
        [sprm] = unsigned2.unpack(sprm)
        assert sprm >> SGC_BIT & SGC_MASK in {PARAGRAPH, TABLE}
        spra = sprm >> SPRA_BIT & SPRA_MASK
        sprm &= PROP_MASK
        if sprm == sprmPFInTable:
            assert spra == 1
            [in_table] = prl.read(1)
            assert in_table in {0, 1}
        elif sprm == sprmPFTtp:
            assert spra == 1
            [is_ttp] = prl.read(1)
            assert is_ttp in {0, 1}
        elif sprm == sprmPHugePapx:
            assert spra == 3
            assert ole
            [offset] = unsigned4.unpack(prl.read())
            data = ole.openstream("Data")
            data.seek(offset)
            [cbGrpprl] = unsigned2.unpack(data.read(2))
            prl = Subfile(data, cbGrpprl)
            data = None
            continue
        elif spra == 6:
            if sprm == sprmTDefTable:
                [cb] = unsigned2.unpack(prl.read(2))
                assert cb > 1
                prl.seek(cb - 1, SEEK_CUR)
            else:
                [cb] = prl.read(1)
                if sprm == sprmPChgTabs and cb == 255:
                    [cTabs] = prl.read(1)
                    prl.seek(4 * cTabs, SEEK_CUR)
                    [cTabs] = prl.read(1)
                    prl.seek(3 * cTabs, SEEK_CUR)
                else:
                    prl.seek(cb, SEEK_CUR)
        else:
            prl.seek(SPRA_SIZES[spra], SEEK_CUR)
    return (in_table, is_ttp)

def iter_para_buckets(table, fcPlcfBtePapx, lcbPlcfBtePapx):
    table.seek(fcPlcfBtePapx)
    assert lcbPlcfBtePapx > 4
    [n, remainder] = divmod(lcbPlcfBtePapx - 4, 4 + 4)
    assert not remainder
    [fc] = unsigned4.unpack(table.read(4))
    yield fc
    aFC1 = table.tell()
    aPnBtePapx = aFC1 + n * 4
    for i in range(n):
        table.seek(aPnBtePapx + i * 4)
        [pn] = unsigned4.unpack(table.read(4))
        table.seek(aFC1 + i * 4)
        [next_fc] = unsigned4.unpack(table.read(4))
        assert next_fc >= fc
        yield (fc, next_fc, pn & PN_MASK)
        fc = next_fc
    return None

def iter_paras_from_pn(doc, ole, fc, next_fc, pn, target, buckets):
    while True:  # For each bucket
        doc.seek(pn * 512)
        page = doc.read(512)
        cpara = page[-1]
        page = page[:-1]
        [rgfc] = unsigned4.unpack_from(page)
        assert rgfc == fc
        rgbx = (1 + cpara) * 4
        for i in range(cpara):
            [next_rgfc] = unsigned4.unpack_from(page, (1 + i) * 4)
            assert next_rgfc >= fc
            if next_rgfc > target:
                bOffset = page[rgbx + i * (1 + 12)]
                if bOffset:
                    bOffset *= 2
                    cb = page[bOffset]
                    bOffset += 1
                    if cb:
                        cb = cb * 2 - 1
                    else:
                        cb = page[bOffset] * 2
                        bOffset += 1
                    grpprlInPapx = BytesIO(page[bOffset : bOffset + cb])
                    [istd] = unsigned2.unpack(grpprlInPapx.read(2))
                    [in_table, is_ttp] = parse_prop_list(grpprlInPapx, ole)
                else:
                    in_table = False
                    is_ttp = False
                yield (next_rgfc, in_table, is_ttp)
            fc = next_rgfc
        assert fc == next_fc
        try:
            [fc, next_fc, pn] = next(buckets)
        except StopIteration:
            break

def iter_paras_from(doc, ole, table, fcPlcfBtePapx, lcbPlcfBtePapx, target):
    buckets = iter_para_buckets(table, fcPlcfBtePapx, lcbPlcfBtePapx)
    fc = next(buckets)
    if target < fc:
        return None
    for [fc, next_fc, pn] in buckets:
        if next_fc > target:
            return iter_paras_from_pn(doc, ole, fc, next_fc, pn,
                target, buckets)
    return None

def main(file):
    with open(file, "rb") as file:
        ole = OleFileIO(file)
        doc = ole.openstream("WordDocument")
        base = FibBase.unpack(doc.read(FibBase.size))
        [wIdent, _, _, _, _, bits_fm, _, _, _, _] = base
        assert wIdent == WORD_BINARY_FILE
        fWhichTblStm = bits_fm >> WHICH_TBL_STM_BIT & 1
        [csw] = unsigned2.unpack(doc.read(2))
        doc.seek(csw * 2, SEEK_CUR)
        [cslw] = unsigned2.unpack(doc.read(2))
        doc.seek(cslw * 4, SEEK_CUR)
        [cbRgFcLcb] = unsigned2.unpack(doc.read(2))
        cbRgFcLcb *= 8
        assert cbRgFcLcb >= FibRgFcLcb97.size
        fibRgFcLcb97 = FibRgFcLcb97.unpack(doc.read(FibRgFcLcb97.size))
        [fcPlcfBtePapx, lcbPlcfBtePapx, fcClx, lcbClx] = fibRgFcLcb97
        table = ole.openstream("{}Table".format(fWhichTblStm))
        
        from sys import stdout
        pieces = iter_pieces(doc, table, fcClx, lcbClx)
        prev_in_table = False
        for piece in pieces:  # For each piece starting a paragraph
            paras = iter_paras_from(doc, ole, table,
                fcPlcfBtePapx, lcbPlcfBtePapx, piece.byte_offset)
            while True:  # For each paragraph in the current piece
                para_size = 0
                while True:  # For each piece contributing to the paragraph
                    [end, in_table, is_ttp] = next(paras)
                    end -= piece.byte_offset
                    if end <= piece.bytes_remaining:
                        break
                    while True:  # For each piece without paragraph info
                        para_size += piece.bytes_remaining // piece.code_size
                        copyfileobj(piece.get_reader(), stdout)
                        piece = next(piece)
                        paras = iter_paras_from(doc, table,
                            fcPlcfBtePapx, lcbPlcfBtePapx, piece.byte_offset)
                        if paras is not None:
                            break
                if is_ttp:
                    para_size += end // piece.code_size
                    assert para_size == 1
                    assert piece.get_reader(end).read() == "\x07"
                    mark = "╜"
                else:
                    assert end
                    copyfileobj(piece.get_reader(end - piece.code_size), stdout)
                    mark = piece.get_reader(piece.code_size).read()
                    mark = {"\r": "¶", "\x07": "¤", "\f": "§"}[mark]
                if not prev_in_table and in_table:
                    print(end="╤")
                elif prev_in_table and not in_table:
                    print(end="╚")
                print(mark)
                prev_in_table = in_table
                if not piece.bytes_remaining:
                    break
        assert not prev_in_table
        
        for [exctype, msg] in ole.parsing_issues:
            print("{}: {}".format(exctype.__name__, msg))

if __name__ == "__main__":
    from clifunc import run
    run(main)
