from enum import Enum
from collections import defaultdict
from typing import List, Dict

import tester.core.metrics as met
from tester.core.video import RawVideoSequence
import tester.core.cfg as cfg


class TableColumns(Enum):
    VIDEO = 1
    PSNR_BDBR = 2
    SSIM_BDBR = 3
    VMAF_BDBR = 4
    SPEEDUP = 5


def tablefy(context):
    a = [
        '',
        '<!DOCTYPE html>',
        '<html>',
        '   <head>',
        '''
        <style>
        .data_table {
          float: left;
        }
        
        html, body {
          width: 99%;
          height: 100%;
          font: 13px times;
        }
        
        .info {
          float: left
          font: 20px times;
          height: 100%;
          top: 40%;
          position: relative;
          font: 20px times;
        }
                
        .complete {
          clear: left;
          position: relative;
        }
        
        table {
          border-spacing: 0px 3px;
        }
        
        th{
          font: bold 24px times;
          padding: 3px 15px;
          border-bottom: 3px solid black;
        }
        
        tbody td { 
          text-align: right;
          padding: 1px 3px;
        }
        
        tbody td:first-child { 
          text-align: left;
        }
        
        .hevc td{
          font: bold 15px Times;
          border-bottom: 1px solid black;
          border-collapse: collapse;
        }
        
        .total td{
          font: bold 18px Times;
          border-bottom: 1px solid black;
          border-top: 2px solid black;
          border-collapse: collapse;
        }
        
        div {
          margin-right: 20px;
        }
        </style>
        '''
        '<meta charset="utf-8">',
        '   </head>',
        '<body>'
    ]
    for test in context.get_tests():
        for anchor in [context.get_test(name) for name in test.anchor_names]:
            a.append(tablefy_one(context, test, anchor))

    a.append('</body>')
    a.append('</html>')
    return "\n".join(a)


def tablefy_one(context, test, anchor):
    html = [
        '<div class="complete">',
        '   <div class="data_table">',
        '       <table>',
        table_header(),
    ]
    class_averages = defaultdict(lambda: defaultdict(list))
    total_averages = defaultdict(list)
    all_data = defaultdict(lambda: defaultdict(dict))
    collect_data(all_data, test, anchor, class_averages, context, total_averages)

    for cls in sorted(class_averages.keys()):
        html.append(
            row_from_data(class_averages[cls], "hevc")
        )
        for seq, data in all_data[cls].items():
            html.append(
                row_from_data(data)
            )

    html.append(
        row_from_data(total_averages, "total")
    )

    html.extend([
        '       </table>',
        '   </div>',
        '<div class="info">',
        'This should be explaining anchor and tested',
        '</div>',
    ])

    html += [
        '</div>'
    ]
    return "\n".join(html)


def collect_data(all_data, test, anchor, class_averages, context, total_averages):
    sequences: List[RawVideoSequence] = context.get_input_sequences()
    metrics: Dict[str, met.TestMetrics] = context.get_metrics()
    for sequence in sequences:
        c = sequence.get_sequence_class()
        actions = {
            TableColumns.PSNR_BDBR: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                metrics[anchor.name][sequence], "psnr"),
            TableColumns.SSIM_BDBR: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                metrics[anchor.name][sequence], "ssim"),
            TableColumns.VMAF_BDBR: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                metrics[anchor.name][sequence], "vmaf"),
            TableColumns.SPEEDUP: lambda: metrics[test.name][sequence].average_speedup(
                metrics[anchor.name][sequence]),
            TableColumns.VIDEO: lambda: sequence.get_suffixless_name()
        }
        for m in cfg.Cfg().table_enabled_fields:
            temp = actions[m]()
            all_data[c][sequence.get_suffixless_name()][m] = temp
            if m == TableColumns.VIDEO:
                continue
            class_averages[c][m].append(temp)
            total_averages[m].append(temp)

    for cls in class_averages:
        for m in cfg.Cfg().table_enabled_fields:
            if m == TableColumns.VIDEO:
                continue
            class_averages[cls][m] = sum(class_averages[cls][m]) / len(class_averages[cls][m])
        class_averages[cls][TableColumns.VIDEO] = cls

    for m in cfg.Cfg().table_enabled_fields:
        if m == TableColumns.VIDEO:
            continue
        total_averages[m] = sum(total_averages[m]) / len(total_averages[m])
    total_averages[TableColumns.VIDEO] = "Averages"


def table_header():
    a = [
            "<tr>"
        ] + [
            f"  <th>{cfg.Cfg().table_column_headers[x]}</th>"
            for x
            in cfg.Cfg().table_enabled_fields
        ] + [
            "</tr>"
        ]
    return "\n".join(a)


def row_from_data(row_data, row_class: [str, None] = None):
    out = [
              f'''<tr{"" if not row_class else f' class="{row_class}"'}>''',
          ] + [
              f'      <td> <div> {cfg.Cfg().table_column_formats[x](row_data[x])} <div> </td>'
              for x
              in cfg.Cfg().table_enabled_fields
          ] + [
              '</tr>'
          ]
    return "\n".join(out)
