#! /usr/bin/env python3

from excel import FreqExcelReader
from contextlib import ExitStack
from sys import stderr, stdout
from time import monotonic
import csv
from io import TextIOWrapper

def main(freqs, per_evc):
    per_evc = float(per_evc)
    deadline = monotonic() + 1
    midline = False
    
    with ExitStack() as cleanup:
        freqs = FreqExcelReader(freqs)
        cleanup.callback(freqs.close)
        
        out = TextIOWrapper(stdout.buffer, stdout.encoding, stdout.errors,
            newline="", line_buffering=stdout.line_buffering)
        cleanup.callback(out.detach)
        writer = csv.writer(out)
        writer.writerow(("NAME", "Frequency", "rel"))
        
        total = format(len(freqs))
        last_evc = None
        for [i, plant] in enumerate(freqs):
            if stderr:
                now = monotonic()
                if now >= deadline:
                    if midline:
                        stderr.write("\r")
                    msg = "Record {:{}}/{}".format(i + 1, len(total), total)
                    stderr.write(msg)
                    stderr.flush()
                    midline = True
                    deadline = now + 0.1
            
            freq = plant["Frequency"]
            if plant["EVC"] != last_evc:
                last_evc = plant["EVC"]
                last_desc = plant["EVC_DESC"]
                max_freq = freq
                evc_start = i
                writer.writerow(())
                writer.writerow((f'{last_evc} {last_desc}',))
            else:
                assert freq <= max_freq
                if plant["EVC_DESC"] != last_desc:
                    msg = "EVC {} EVC_DESC inconsistent between {!r} and " \
                        "{!r}".format(last_evc, last_desc, plant["EVC_DESC"])
                    print(msg, file=stderr)
                    last_desc = plant["EVC_DESC"]
                if i - evc_start >= per_evc:
                    continue
            rel = format(freq / max_freq, '#.2g')
            writer.writerow((plant["NAME"], freq, rel))
    
    if stderr and midline:
        stderr.write("\x1B[1K\r")
        stderr.flush()

if __name__ == "__main__":
    from clifunc import run
    run(main)
