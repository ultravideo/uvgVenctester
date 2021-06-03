import subprocess
from enum import Enum
from collections import defaultdict
from typing import List, Dict
from math import isnan

import tester.core.metrics as met
from tester.core.log import console_log
from tester.core.test import Test
from tester.core.video import RawVideoSequence
import tester.core.cfg as cfg


def table_validate_config():
    for field in cfg.Cfg().table_enabled_columns:
        if field not in cfg.Cfg().table_column_headers or field not in cfg.Cfg().table_column_formats:
            console_log.error(f"Table: Field {field} is enabled but missing for table columns of formats")

    try:
        subprocess.check_call([str(cfg.Cfg().wkhtmltopdf), "--version"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        console_log.warning(f"wkhtmltopdf command not reachable")


class TableFormats(Enum):
    HTML = 1
    PDF = 2


class TableColumns(Enum):
    VIDEO = 1
    PSNR_BDBR = 2
    SSIM_BDBR = 3
    VMAF_BDBR = 4
    SPEEDUP = 5


def tablefy(context, header_page=None):
    # The CSS is statically in the HTML because it is much easier than having
    # it in a file and since the pdf generation is very peculiar about the
    # height of the elements
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
          height: 100%;
          top: 40%;
          position: relative;
          font: 18px times;
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
          margin-right: 40px;
        }
        </style>
        '''
        '<meta charset="utf-8">',
        '   </head>',
        '<body>'
    ]
    pixels = 4
    pages = []
    page_count = 0
    for test in context.get_tests():
        for anchor in [context.get_test(name) for name in test.anchor_names]:
            if anchor == test:
                continue
            html, pixels = tablefy_one(context, test, anchor)
            pages.extend(html)
            page_count += 1

    if header_page:
        a.append(f'<div">{header_page}</div>')
    a.extend(pages)

    a.append('</body>')
    a.append('</html>')
    # For some reason the pdf generation requires some extra padding...
    pixels += 5 if pixels % 2 else 4
    return "\n".join(a), pixels, page_count


def tablefy_one(context, test: Test, anchor: Test):
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
    # calculate the height of the table based on the number of elements
    pixels = 23 * len(class_averages) + 21 * sum(len(x) for x in all_data.values()) + 72

    for cls in sorted(class_averages.keys(), key=lambda x: x.lower()):
        html.append(
            row_from_data(class_averages[cls], "hevc")
        )
        for seq, data in sorted(all_data[cls].items(), key=lambda x: x[0].lower()):
            html.append(
                row_from_data(data)
            )

    html.append(
        row_from_data(total_averages, "total")
    )

    test_params = "\n".join(
        [f'<li>{x if y is None else x + " " + y} </li>'
         for x, y
         in test.subtests[0].param_set._to_args_dict(False).items()]
    )

    anchor_params = "\n".join(
        [f'<li>{x if y is None else x + " " + y} </li>'
         for x, y
         in anchor.subtests[0].param_set._to_args_dict(False).items()]
    )

    html.extend([
        '       </table>',
        '   </div>',
        '<div class="info">',
        f'<p style="margin-bottom: 5px">Anchor: Test name: {anchor.name} encoder: {anchor.encoder.get_name()}'
        f' version: {anchor.encoder_revision}</br>Using {anchor.quality_param_type.name}:'
        f' [{", ".join(str(x) for x in test.quality_param_list)}]</p>',
        '<ul style="margin-top: 5px">',
        anchor_params,
        '</ul>',
        f'<p style="margin-bottom: 5px">Test name: {test.name} encoder: {test.encoder.get_name()}'
        f' version: {test.encoder_revision}</br>Using {test.quality_param_type.name}:'
        f' [{", ".join(str(x) for x in test.quality_param_list)}]</p>',
        '<ul style="margin-top: 5px">',
        test_params,
        '</ul>',
        '</div>',
    ])

    html += [
        '</div>'
    ]

    return html, pixels


def collect_data(all_data, test, anchor, class_averages, context, total_averages):
    sequences: List[RawVideoSequence] = context.get_input_sequences()
    metrics: Dict[str, met.TestMetrics] = context.get_metrics()
    for sequence in sequences:
        c = sequence.get_sequence_class()
        actions = {
            TableColumns.PSNR_BDBR: lambda: metrics[test.name][sequence].compare_to_anchor(
                metrics[anchor.name][sequence], "psnr"),
            TableColumns.SSIM_BDBR: lambda: metrics[test.name][sequence].compare_to_anchor(
                metrics[anchor.name][sequence], "ssim"),
            TableColumns.VMAF_BDBR: lambda: metrics[test.name][sequence].compare_to_anchor(
                metrics[anchor.name][sequence], "vmaf"),
            TableColumns.SPEEDUP: lambda: metrics[test.name][sequence].compare_to_anchor(
                metrics[anchor.name][sequence], "encoding_time"),
            TableColumns.VIDEO: lambda: sequence.get_suffixless_name()
        }
        for m in cfg.Cfg().table_enabled_columns:
            temp = actions[m]()
            all_data[c][sequence.get_suffixless_name()][m] = temp
            if m == TableColumns.VIDEO:
                continue
            class_averages[c][m].append(temp)
            total_averages[m].append(temp)

    for cls in class_averages:
        for m in cfg.Cfg().table_enabled_columns:
            if m == TableColumns.VIDEO:
                continue
            non_nan_values = [x for x in class_averages[cls][m] if not isnan(x)]
            class_averages[cls][m] = sum(non_nan_values) / len(non_nan_values)
        class_averages[cls][TableColumns.VIDEO] = cls

    for m in cfg.Cfg().table_enabled_columns:
        if m == TableColumns.VIDEO:
            continue
        non_nan_values = [x for x in total_averages[m] if not isnan(x)]
        total_averages[m] = sum(non_nan_values) / len(non_nan_values)
    total_averages[TableColumns.VIDEO] = "Averages"


def table_header():
    a = [
            "<tr>"
        ] + [
            f"  <th>{cfg.Cfg().table_column_headers[x]}</th>"
            for x
            in cfg.Cfg().table_enabled_columns
        ] + [
            "</tr>"
        ]
    return "\n".join(a)


def row_from_data(row_data, row_class: [str, None] = None):
    out = [
              f'''<tr{"" if not row_class else f' class="{row_class}"'}>''',
          ] + [
              f'      <td> <div{""" style:"color: red";""" if type(row_data[x]) == float and isnan(row_data[x]) else ""}> ' +
              f'{cfg.Cfg().table_column_formats[x](row_data[x])} </div> </td>'
              for x
              in cfg.Cfg().table_enabled_columns
          ] + [
              '</tr>'
          ]
    return "\n".join(out)
