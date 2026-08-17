#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A-Share Short-Term Speculation Review Tool HTML Template Generator
Builds the standalone single-file HTML application with full dynamic recalculation.
"""

import json
import os
import sys

def get_html_template():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股短线博弈每日复盘系统 (A-Share Short-Term Speculation Review Tool)</title>
    <style>
        /* === Root Variables & Global Styling === */
        :root {
            --bg-dark: #0d1117;
            --card-bg: #161b22;
            --card-border: #30363d;
            --card-hover: #21262d;
            --text-main: #f0f6fc;
            --text-sub: #8b949e;
            --text-dim: #6e7681;
            
            /* Stock Theme Colors */
            --red-bull: #f85149;
            --red-bull-bg: rgba(248, 81, 73, 0.15);
            --red-bull-border: rgba(248, 81, 73, 0.4);
            --green-bear: #3fb950;
            --green-bear-bg: rgba(63, 185, 80, 0.15);
            --green-bear-border: rgba(63, 185, 80, 0.4);
            --gold-accent: #f0883e;
            --gold-bg: rgba(240, 136, 62, 0.15);
            --blue-accent: #58a6ff;
            --blue-bg: rgba(88, 166, 255, 0.15);
            --purple-accent: #bc8cff;
            --purple-bg: rgba(188, 140, 255, 0.15);
            --orange-tag: #d29922;
            
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1440px;
            margin: 0 auto;
        }

        /* === Header & Control Bar === */
        header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #1f242c 0%, #161b22 100%);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 20px 28px;
            margin-bottom: 24px;
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }

        header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #f85149, #f0883e, #58a6ff, #bc8cff);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .brand-logo {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #f85149, #d29922);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: 900;
            color: #fff;
            box-shadow: 0 4px 12px rgba(248, 81, 73, 0.4);
        }

        .brand-title h1 {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-title .badge {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 20px;
            background: var(--red-bull-bg);
            color: var(--red-bull);
            border: 1px solid var(--red-bull-border);
        }

        .brand-subtitle {
            font-size: 13px;
            color: var(--text-sub);
            margin-top: 2px;
        }

        .controls-group {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }

        .date-picker-box {
            display: flex;
            align-items: center;
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 6px 14px;
            gap: 10px;
        }

        .date-picker-box label {
            font-size: 13px;
            color: var(--text-sub);
            white-space: nowrap;
        }

        .date-picker-box input[type="date"] {
            background: transparent;
            border: none;
            color: var(--text-main);
            font-family: var(--font-family);
            font-size: 14px;
            font-weight: 600;
            outline: none;
            cursor: pointer;
            color-scheme: dark;
        }

        .quick-dates {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .quick-btn {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--text-sub);
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .quick-btn:hover {
            background: var(--card-hover);
            color: var(--text-main);
            border-color: var(--blue-accent);
        }

        .quick-btn.active {
            background: var(--blue-bg);
            color: var(--blue-accent);
            border-color: var(--blue-accent);
            font-weight: 600;
        }

        .action-btn {
            background: linear-gradient(135deg, #1f6feb, #238636);
            border: none;
            color: #fff;
            padding: 8px 18px;
            border-radius: var(--radius-md);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: opacity 0.2s;
        }

        .action-btn:hover {
            opacity: 0.9;
        }

        .action-btn:disabled {
            opacity: 0.55;
            cursor: wait;
        }

        .action-btn.review-go {
            background: linear-gradient(135deg, #f85149, #d29922);
            font-size: 14px;
            padding: 8px 22px;
        }

        .action-btn.secondary {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--text-main);
        }

        .action-btn.secondary:hover {
            background: var(--card-hover);
            border-color: var(--gold-accent);
            color: var(--gold-accent);
        }

        /* === Non-trading Day Alert Modal / Banner === */
        #idleBanner {
            background: linear-gradient(135deg, rgba(88, 166, 255, 0.16) 0%, rgba(188, 140, 255, 0.12) 100%);
            border-color: rgba(88, 166, 255, 0.45);
        }

        .market-closed-banner {
            display: none;
            background: linear-gradient(135deg, rgba(210, 153, 34, 0.15) 0%, rgba(248, 81, 73, 0.15) 100%);
            border: 1px solid rgba(210, 153, 34, 0.4);
            border-radius: var(--radius-lg);
            padding: 36px 32px;
            text-align: center;
            margin-bottom: 28px;
            animation: fadeIn 0.3s ease-in-out;
            box-shadow: var(--shadow);
        }

        .market-closed-icon {
            font-size: 54px;
            margin-bottom: 12px;
            display: inline-block;
        }

        .market-closed-title {
            font-size: 24px;
            font-weight: 800;
            color: var(--gold-accent);
            margin-bottom: 10px;
        }

        .market-closed-desc {
            font-size: 15px;
            color: var(--text-main);
            max-width: 750px;
            margin: 0 auto 20px;
            line-height: 1.8;
        }

        .market-closed-meta {
            display: inline-flex;
            gap: 24px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 12px 24px;
            border-radius: var(--radius-md);
            font-size: 13px;
            color: var(--text-sub);
            text-align: left;
            flex-wrap: wrap;
            justify-content: center;
        }

        .market-closed-meta strong {
            color: var(--text-main);
        }

        /* === Market Master Stats Banner === */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, border-color 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: var(--blue-accent);
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-sub);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 800;
            color: var(--text-main);
            font-feature-settings: "tnum";
            display: flex;
            align-items: baseline;
            gap: 8px;
        }

        .stat-sub {
            font-size: 12px;
            margin-top: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .up-red {
            color: var(--red-bull) !important;
        }

        .down-green {
            color: var(--green-bear) !important;
        }

        .neutral-gold {
            color: var(--gold-accent) !important;
        }

        .blue-highlight {
            color: var(--blue-accent) !important;
        }

        .purple-highlight {
            color: var(--purple-accent) !important;
        }

        /* === Main Dashboard Layout === */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }

        @media (max-width: 1100px) {
            .main-layout {
                grid-template-columns: 1fr;
            }
        }

        .full-width {
            grid-column: 1 / -1;
        }

        /* === Section Cards === */
        .section-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 22px 24px;
            box-shadow: var(--shadow);
            position: relative;
        }

        .section-card.highlight-border-red {
            border-left: 4px solid var(--red-bull);
        }

        .section-card.highlight-border-gold {
            border-left: 4px solid var(--gold-accent);
        }

        .section-card.highlight-border-blue {
            border-left: 4px solid var(--blue-accent);
        }

        .section-card.highlight-border-purple {
            border-left: 4px solid var(--purple-accent);
        }

        .section-card.highlight-border-green {
            border-left: 4px solid var(--green-bear);
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--card-border);
        }

        .section-title {
            font-size: 17px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .section-title .icon {
            font-size: 20px;
        }

        .section-tag {
            font-size: 11px;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: 600;
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            color: var(--text-sub);
        }

        /* === Cycle Thermometer & Gauge Bar === */
        .gauge-container {
            margin: 16px 0;
            background: var(--bg-dark);
            border-radius: var(--radius-md);
            padding: 16px;
            border: 1px solid var(--card-border);
        }

        .cycle-stages-bar {
            display: flex;
            height: 28px;
            border-radius: 14px;
            overflow: hidden;
            background: #21262d;
            position: relative;
            margin-bottom: 12px;
            border: 1px solid var(--card-border);
        }

        .stage-segment {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.7);
            position: relative;
            transition: all 0.3s;
        }

        .stage-segment.active {
            color: #fff;
            box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.4);
            transform: scale(1.02);
            z-index: 2;
        }

        .stage-1 { background: linear-gradient(90deg, #1f6feb, #388bfd); } /* 启动/修复 */
        .stage-2 { background: linear-gradient(90deg, #238636, #3fb950); } /* 发酵/主升 */
        .stage-3 { background: linear-gradient(90deg, #d29922, #f0883e); } /* 分歧/震荡 */
        .stage-4 { background: linear-gradient(90deg, #f85149, #da3633); } /* 退潮/冰点 */

        .cycle-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 12px;
        }

        .detail-item {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 10px 14px;
            border-radius: var(--radius-sm);
        }

        .detail-item .label {
            font-size: 11px;
            color: var(--text-sub);
        }

        .detail-item .val {
            font-size: 14px;
            font-weight: 700;
            margin-top: 2px;
        }

        /* === Ladder Matrix Table === */
        .ladder-tier {
            margin-bottom: 16px;
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            overflow: hidden;
        }

        .tier-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid var(--card-border);
        }

        .tier-title {
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .tier-badge {
            background: var(--red-bull-bg);
            color: var(--red-bull);
            border: 1px solid var(--red-bull-border);
            padding: 1px 8px;
            border-radius: 10px;
            font-size: 11px;
        }

        .stock-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }

        .stock-table th {
            text-align: left;
            padding: 8px 12px;
            color: var(--text-dim);
            font-weight: 600;
            border-bottom: 1px solid var(--card-border);
            background: rgba(0, 0, 0, 0.2);
        }

        .stock-table td {
            padding: 8px 12px;
            border-bottom: 1px solid rgba(48, 54, 61, 0.5);
            color: var(--text-main);
        }

        .stock-table tr:last-child td {
            border-bottom: none;
        }

        .stock-table tr:hover td {
            background: var(--card-hover);
        }

        .stock-name-cell {
            display: flex;
            flex-direction: column;
        }

        .stock-name {
            font-weight: 700;
            font-size: 13px;
            color: var(--text-main);
        }

        .stock-code {
            font-size: 11px;
            color: var(--text-dim);
            font-family: monospace;
        }

        .seal-pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }

        .seal-perfect {
            background: var(--red-bull-bg);
            color: var(--red-bull);
            border: 1px solid var(--red-bull-border);
        }

        .seal-good {
            background: var(--gold-bg);
            color: var(--gold-accent);
            border: 1px solid var(--gold-accent);
        }

        .seal-break {
            background: var(--green-bear-bg);
            color: var(--green-bear);
            border: 1px solid var(--green-bear-border);
        }

        /* === Dragon Tiger List View === */
        .lhb-card-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .lhb-card {
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            transition: all 0.2s;
        }

        .lhb-card:hover {
            border-color: var(--purple-accent);
        }

        .lhb-seat-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .seat-name {
            font-size: 14px;
            font-weight: 700;
            color: var(--purple-accent);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .seat-style {
            font-size: 11px;
            color: var(--text-sub);
            background: rgba(188, 140, 255, 0.1);
            padding: 2px 8px;
            border-radius: 10px;
            border: 1px solid rgba(188, 140, 255, 0.3);
        }

        .lhb-actions-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .lhb-action-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            padding: 4px 8px;
            background: var(--card-bg);
            border-radius: var(--radius-sm);
        }

        .lhb-action-stock {
            font-weight: 600;
        }

        .lhb-action-val {
            font-weight: 700;
        }

        .lhb-action-comment {
            font-size: 11px;
            color: var(--text-sub);
            margin-top: 2px;
            padding-left: 4px;
        }

        /* === Cash Defense Checklist === */
        .checklist-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .check-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            padding: 12px 14px;
            border-radius: var(--radius-md);
            transition: all 0.2s;
        }

        .check-item.triggered {
            border-color: var(--red-bull-border);
            background: rgba(248, 81, 73, 0.05);
        }

        .check-status-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            white-space: nowrap;
        }

        .badge-safe {
            background: var(--green-bear-bg);
            color: var(--green-bear);
            border: 1px solid var(--green-bear-border);
        }

        .badge-warn {
            background: var(--gold-bg);
            color: var(--gold-accent);
            border: 1px solid var(--gold-accent);
        }

        .badge-danger {
            background: var(--red-bull-bg);
            color: var(--red-bull);
            border: 1px solid var(--red-bull-border);
        }

        .check-content {
            flex: 1;
        }

        .check-rule {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 2px;
        }

        .check-detail {
            font-size: 12px;
            color: var(--text-sub);
            line-height: 1.5;
        }

        /* === Discipline & Strategy Box === */
        .discipline-box {
            background: linear-gradient(135deg, rgba(88, 166, 255, 0.05) 0%, rgba(188, 140, 255, 0.05) 100%);
            border: 1px solid var(--blue-accent);
            border-radius: var(--radius-lg);
            padding: 20px 24px;
            margin-top: 16px;
        }

        .discipline-subhead {
            font-size: 14px;
            font-weight: 700;
            color: var(--blue-accent);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .discipline-list {
            padding-left: 20px;
            font-size: 13px;
            color: var(--text-main);
            margin-bottom: 14px;
            line-height: 1.7;
        }

        .discipline-list li {
            margin-bottom: 4px;
        }

        /* === Parameter Customization Modal === */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            z-index: 999;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease;
        }

        .modal-box {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            width: 90%;
            max-width: 650px;
            padding: 28px;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
            max-height: 85vh;
            overflow-y: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--card-border);
        }

        .modal-title {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-main);
        }

        .modal-close {
            background: transparent;
            border: none;
            color: var(--text-sub);
            font-size: 20px;
            cursor: pointer;
        }

        .param-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(48, 54, 61, 0.4);
        }

        .param-info {
            flex: 1;
            padding-right: 20px;
        }

        .param-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
        }

        .param-desc {
            font-size: 11px;
            color: var(--text-dim);
        }

        .param-input-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .param-input {
            width: 80px;
            background: var(--bg-dark);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 6px 10px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            text-align: right;
            outline: none;
        }

        .param-input:focus {
            border-color: var(--blue-accent);
        }

        .modal-footer {
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--card-border);
        }

        /* === Footer === */
        footer {
            margin-top: 36px;
            padding: 20px 0;
            border-top: 1px solid var(--card-border);
            text-align: center;
            font-size: 12px;
            color: var(--text-dim);
            line-height: 1.8;
        }

        footer strong {
            color: var(--text-sub);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Print friendly styles */
        @media print {
            @page {
                size: A4 portrait;
                margin: 12mm 10mm 12mm 10mm;
            }
            body {
                background: #ffffff !important;
                color: #111111 !important;
                padding: 0 !important;
                font-size: 11pt;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .container {
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 !important;
            }
            header {
                background: #f6f8fa !important;
                border: 1px solid #d0d7de !important;
                color: #111111 !important;
                box-shadow: none !important;
                padding: 12px 16px !important;
                margin-bottom: 16px !important;
            }
            header::before {
                background: #cf222e !important;
            }
            .brand-title h1 {
                color: #111111 !important;
                font-size: 18pt !important;
            }
            .brand-subtitle {
                color: #57606a !important;
            }
            .controls-group, .modal-overlay, .quick-dates, #idleBanner {
                display: none !important;
            }
            .stat-card {
                background: #f6f8fa !important;
                border: 1px solid #d0d7de !important;
                box-shadow: none !important;
                padding: 10px 12px !important;
                page-break-inside: avoid;
            }
            .stat-label {
                color: #57606a !important;
            }
            .stat-value {
                color: #111111 !important;
            }
            .section-card {
                background: #ffffff !important;
                border: 1px solid #d0d7de !important;
                box-shadow: none !important;
                padding: 14px 16px !important;
                margin-bottom: 14px !important;
                page-break-inside: avoid;
            }
            .section-header {
                border-bottom: 1px solid #d0d7de !important;
            }
            .section-title {
                color: #111111 !important;
            }
            .gauge-container, .ladder-tier, .lhb-card, .check-item, .discipline-box {
                background: #f6f8fa !important;
                border: 1px solid #d0d7de !important;
                color: #111111 !important;
                page-break-inside: avoid;
            }
            .stock-table th {
                background: #eaeef2 !important;
                color: #24292f !important;
                border-bottom: 1px solid #d0d7de !important;
            }
            .stock-table td {
                color: #24292f !important;
                border-bottom: 1px solid #eaeef2 !important;
            }
            .stock-name {
                color: #0969da !important;
            }
            .up-red {
                color: #cf222e !important;
                font-weight: bold;
            }
            .down-green {
                color: #1a7f37 !important;
                font-weight: bold;
            }
            .neutral-gold {
                color: #9a6700 !important;
                font-weight: bold;
            }
            .blue-highlight {
                color: #0969da !important;
                font-weight: bold;
            }
            .purple-highlight {
                color: #8250df !important;
                font-weight: bold;
            }
            footer {
                border-top: 1px solid #d0d7de !important;
                color: #57606a !important;
                margin-top: 16px !important;
                padding: 8px 0 !important;
            }
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Header -->
    <header>
        <div class="brand">
            <div class="brand-logo">📈</div>
            <div class="brand-title">
                <h1>
                    A股短线博弈复盘系统
                    <span class="badge" id="tradingStatusBadge">交易日</span>
                </h1>
                <div class="brand-subtitle" id="dataTimestampHeader">数据统计日期：-- | 交易日离线独立单文件</div>
            </div>
        </div>

        <div class="controls-group">
            <div class="date-picker-box">
                <label for="dateSelect">📅 选择复盘交易日:</label>
                <input type="date" id="dateSelect" value="2026-08-13">
            </div>
            <button class="action-btn review-go" id="startReviewBtn" onclick="startReview()">开始复盘</button>

            <div class="quick-dates">
                <button class="quick-btn" onclick="startReview('2024-03-22')">03-22(艾艾13板断)</button>
                <button class="quick-btn" onclick="startReview('2024-03-25')">03-25(博信7板退潮)</button>
                <button class="quick-btn" onclick="startReview('2024-04-18')">04-18(同为5板)</button>
                <button class="quick-btn" onclick="startReview('2024-09-30')">09-30(2.59万亿)</button>
                <button class="quick-btn" onclick="startReview('2024-10-08')">10-08(3.45万亿)</button>
                <button class="quick-btn" onclick="startReview('2026-08-13')">08-13(秦安5板)</button>
                <button class="quick-btn" onclick="startReview('2026-08-14')">08-14(蓝盾光电5板)</button>
                <button class="quick-btn" onclick="startReview('2024-04-04')">04-04(清明休市)</button>
                <button class="quick-btn" onclick="startReview('2024-10-01')">10-01(国庆休市)</button>
            </div>

            <button class="action-btn secondary" onclick="openParamModal()">
                ⚙️ 胜率参数设定
            </button>
            <button class="action-btn" onclick="window.print()">
                🖨️ 导出/打印复盘
            </button>
        </div>
    </header>

    <!-- Non-Trading Day Banner (Triggered when market closed) -->
    <div class="market-closed-banner" id="closedBanner">
        <div class="market-closed-icon">🛑</div>
        <div class="market-closed-title" id="closedTitle">休市通知：非交易日</div>
        <div class="market-closed-desc" id="closedDesc">
            当前所选日期为法定休市日或周末常规闭市，中国证券交易所（沪深北）暂停行情交易与清算。短线博弈程序已按规则停止输出场内分时及涨跌停梯队数据。
        </div>
        <div class="market-closed-meta" id="closedMeta">
            <div>休市类型：<strong id="closedType">法定节假日</strong></div>
            <div>休市区间：<strong id="closedPeriod">--</strong></div>
            <div>下一交易日：<strong id="nextTradingDay">--</strong></div>
        </div>
    </div>

    <!-- Idle: wait for user to click 开始复盘 -->
    <div class="market-closed-banner" id="idleBanner" style="display:block;">
        <div class="market-closed-icon">📅</div>
        <div class="market-closed-title">选择交易日，点击「开始复盘」</div>
        <div class="market-closed-desc">
            正确流程：先选定日期（例如 2026-08-13），再点击红色按钮「开始复盘」。系统会优先使用已核验样本库；若该日不在库中，再调取东方财富公开涨停池/指数日K 生成报告。不会在改日期时自动跳转，也不会把未知日期悄悄替换成别的交易日。
        </div>
        <div class="market-closed-meta">
            <div>当前选择：<strong id="idleDateHint">2026-08-13</strong></div>
            <div>下一步：<strong>点击「开始复盘」调数据</strong></div>
        </div>
    </div>

    <!-- Active Trading Day Dashboard Content -->
    <div id="tradingContent" style="display:none;">
        <!-- Market Macro Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">
                    <span>上证指数</span>
                    <span id="shTrendIcon">▲</span>
                </div>
                <div class="stat-value" id="shIndexVal">3048.03</div>
                <div class="stat-sub" id="shChangeVal">-0.95%</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    <span>全市场成交额</span>
                    <span>两市量能</span>
                </div>
                <div class="stat-value" id="totalTurnoverVal">10,973 <span style="font-size:14px;font-weight:400;color:var(--text-sub)">亿元</span></div>
                <div class="stat-sub" id="turnoverChangeVal">+296 亿元</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    <span>涨跌家数比</span>
                    <span>红绿多空</span>
                </div>
                <div class="stat-value" id="upDownRatioVal">
                    <span class="up-red" id="upCountVal">1024</span> / <span class="down-green" id="downCountVal">4126</span>
                </div>
                <div class="stat-sub" id="medianChangeVal">全市场中位数：-1.42%</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    <span>涨停 / 跌停</span>
                    <span>极端情绪</span>
                </div>
                <div class="stat-value" id="limitStatsVal">
                    <span class="up-red" id="limitUpVal">58</span> / <span class="down-green" id="limitDownVal">18</span>
                </div>
                <div class="stat-sub" id="brokenBoardRateVal">炸板率：32.56% (28家炸板)</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    <span>情绪周期阶段</span>
                    <span>核心定性</span>
                </div>
                <div class="stat-value neutral-gold" id="sentimentPhaseVal">分歧期</div>
                <div class="stat-sub" id="suggestedPositionVal">建议仓位：2~4成 (防守试错)</div>
            </div>
        </div>

        <!-- Main Dashboard Split Grid -->
        <div class="main-layout">
            <!-- 1. Emotion Cycle & Position Thermometer -->
            <div class="section-card highlight-border-gold">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🧭</span> 一、情绪周期判定与仓位温度计
                    </div>
                    <span class="section-tag" id="cycleScoreTag">综合博弈得分: 46分</span>
                </div>

                <div class="gauge-container">
                    <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-sub);margin-bottom:6px;">
                        <span>退潮冰点 (0-35)</span>
                        <span>启动修复 (36-55)</span>
                        <span>分歧震荡 (56-75)</span>
                        <span>发酵高潮 (76-100)</span>
                    </div>
                    <div class="cycle-stages-bar">
                        <div class="stage-segment stage-4" id="stageRecede">退潮期</div>
                        <div class="stage-segment stage-1" id="stageRepair">修复期</div>
                        <div class="stage-segment stage-3" id="stageDiverge">分歧期</div>
                        <div class="stage-segment stage-2" id="stageMain">主升/高潮</div>
                    </div>
                    <div style="font-size:12px;color:var(--text-sub);display:flex;justify-content:space-between;margin-top:6px;">
                        <span>当前周期判定：<strong class="neutral-gold" id="currentPhaseDesc">分歧期 (高位获利兑现与新老题材交替)</strong></span>
                        <span>防守警戒度：<strong class="up-red" id="defenseAlertLevel">高危防守</strong></span>
                    </div>
                </div>

                <div class="cycle-details">
                    <div class="detail-item">
                        <div class="label">连板晋级率 (1进2 / 2进3 / 高位)</div>
                        <div class="val up-red" id="promotionRatesVal">33.3% / 42.8% / 40.0%</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">连板总高度 / 标杆空间</div>
                        <div class="val blue-highlight" id="marketMaxHeightVal">13连板 (艾艾精工)</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">当日核心热点题材</div>
                        <div class="val" id="coreThemesVal" style="font-size:12px;color:var(--text-main);">低空经济、Kimi应用、铜连接</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">胜率策略建议</div>
                        <div class="val neutral-gold" id="strategyAdviceVal">高位不接力，聚焦低位新题材试错</div>
                    </div>
                </div>
            </div>

            <!-- 2. Absolute High & Low-Level Trial -->
            <div class="section-card highlight-border-red">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">👑</span> 二、绝对高位锚定与低位试错博弈
                    </div>
                    <span class="section-tag" id="highLeaderTag">最高空间标杆</span>
                </div>

                <div style="background:var(--bg-dark);border-radius:var(--radius-md);padding:14px 16px;border:1px solid var(--card-border);margin-bottom:14px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <div>
                            <span style="font-size:16px;font-weight:800;color:var(--red-bull);" id="leaderNameVal">艾艾精工 (603580)</span>
                            <span class="seal-pill seal-perfect" style="margin-left:8px;" id="leaderBoardsVal">13连板 (断板)</span>
                        </div>
                        <div style="font-size:13px;font-weight:700;" id="leaderPriceChangeVal" class="down-green">29.55元 (-8.08%)</div>
                    </div>
                    <p style="font-size:12px;color:var(--text-sub);line-height:1.6;" id="leaderBehaviorDesc">
                        早盘大幅低开后快速冲高翻红，最高上冲至+4.6%，随后承接乏力逐波回落，尾盘收在-8.08%。全天振幅达13.5%，成交量显著放大至历史天量。
                    </p>
                </div>

                <div style="font-size:13px;color:var(--text-main);background:rgba(248,81,73,0.06);border:1px solid var(--red-bull-border);border-radius:var(--radius-md);padding:12px 14px;margin-bottom:12px;">
                    <strong style="color:var(--red-bull);">高位空间研判：</strong>
                    <span id="highHeightAnalysisVal" style="font-size:12px;color:var(--text-main);">
                        艾艾精工13连板创造了年内短线连板空间新标杆，但今日高位龙头同步出现筹码松动与获利盘出逃，永悦科技8板断板触及跌停，标志着第一波高位纯连板抱团进入剧烈分歧阶段。
                    </span>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <div style="background:var(--bg-dark);padding:10px 12px;border-radius:var(--radius-sm);border:1px solid var(--card-border);">
                        <div style="font-size:11px;color:var(--text-sub);font-weight:600;">持筹者纪律：</div>
                        <div style="font-size:12px;color:var(--text-main);margin-top:2px;" id="holdingDisciplineVal">跌破分时均线即为第一卖点，尾盘不回封坚决止盈。</div>
                    </div>
                    <div style="background:var(--bg-dark);padding:10px 12px;border-radius:var(--radius-sm);border:1px solid var(--card-border);">
                        <div style="font-size:11px;color:var(--text-sub);font-weight:600;">低位试错方向：</div>
                        <div style="font-size:12px;color:var(--gold-accent);margin-top:2px;" id="lowTrialDirectionVal">聚焦2连板及1进2新题材（华生科技、低空经济配套）。</div>
                    </div>
                </div>
            </div>

            <!-- 3. Consecutive Board Sample Ladder (Full Width) -->
            <div class="section-card full-width highlight-border-blue">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🪜</span> 三、样本梯队矩阵与连板身位图 (Ladder Matrix)
                    </div>
                    <span class="section-tag">真实全景样本</span>
                </div>

                <div id="ladderContainer">
                    <!-- Dynamic rendering of ladder tiers -->
                </div>
            </div>

            <!-- 4. Sealing Strength & Broken Board Analysis -->
            <div class="section-card highlight-border-gold">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🔒</span> 四、封单强度分析与炸板大面观察
                    </div>
                    <span class="section-tag">次日溢价测算</span>
                </div>

                <div style="margin-bottom:14px;">
                    <div style="font-size:13px;font-weight:700;color:var(--text-main);margin-bottom:8px;">
                        🔥 封单资金强度 Top 榜 (封单额 / 封成比 / 自由流通比)
                    </div>
                    <table class="stock-table" id="sealingTable">
                        <thead>
                            <tr>
                                <th>排名</th>
                                <th>股票名称</th>
                                <th>连板</th>
                                <th>封单金额</th>
                                <th>封成比</th>
                                <th>首封时间</th>
                                <th>次日溢价预期</th>
                            </tr>
                        </thead>
                        <tbody id="sealingTableBody">
                            <!-- Dynamic rows -->
                        </tbody>
                    </table>
                </div>

                <div style="margin-top:16px;">
                    <div style="font-size:13px;font-weight:700;color:var(--red-bull);margin-bottom:8px;">
                        ⚠️ 核心炸板大面股票警示 (中位断板风险)
                    </div>
                    <div id="brokenBoardList" style="display:flex;flex-direction:column;gap:8px;">
                        <!-- Dynamic broken boards -->
                    </div>
                </div>
            </div>

            <!-- 5. Main Capital Flow & Popularity Anchors -->
            <div class="section-card highlight-border-purple">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🌊</span> 五、主力资金流向与市场人气锚点
                    </div>
                    <span class="section-tag">成交百亿核心</span>
                </div>

                <div style="margin-bottom:16px;">
                    <div style="font-size:13px;font-weight:700;color:var(--purple-accent);margin-bottom:8px;">
                        💰 行业主力净流入 / 流出排名
                    </div>
                    <div id="capitalFlowContainer" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                        <!-- Dynamic Capital Flow -->
                    </div>
                </div>

                <div style="margin-top:16px;">
                    <div style="font-size:13px;font-weight:700;color:var(--blue-accent);margin-bottom:8px;">
                        ⚓ 市场超级人气锚点 (成交额与风向标)
                    </div>
                    <div id="popularityAnchorsList" style="display:flex;flex-direction:column;gap:8px;">
                        <!-- Dynamic Popularity Anchors -->
                    </div>
                </div>
            </div>

            <!-- 6. Dragon Tiger Seats Observation -->
            <div class="section-card highlight-border-purple">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🐲</span> 六、龙虎榜顶级游资与机构席位观察
                    </div>
                    <span class="section-tag">操盘风格解密</span>
                </div>

                <div class="lhb-card-group" id="lhbContainer">
                    <!-- Dynamic LHB Cards -->
                </div>
            </div>

            <!-- 7. Cash Defense 7-Rule Checklist -->
            <div class="section-card highlight-border-red">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">🛡️</span> 七、空仓检验与防守触发机制 (7大纪律核查)
                    </div>
                    <span class="section-tag" id="cashScoreTag">防守得分: 38/100</span>
                </div>

                <div class="checklist-group" id="cashChecklistContainer">
                    <!-- Dynamic 7 Check Items -->
                </div>
            </div>

            <!-- 8. Next-Day Bidding & Trading Discipline (Full Width) -->
            <div class="section-card full-width highlight-border-blue">
                <div class="section-header">
                    <div class="section-title">
                        <span class="icon">⚔️</span> 八、次日竞价推演、实战纪律与系统性风险提示
                    </div>
                    <span class="section-tag">胜率实战执行手册</span>
                </div>

                <div class="discipline-box">
                    <div class="discipline-subhead">
                        <span>🎯 集合竞价 (09:15 - 09:25) 重点监控锚点与应对预案</span>
                    </div>
                    <ul class="discipline-list" id="biddingRulesList">
                        <!-- Dynamic Bidding rules -->
                    </ul>

                    <div class="discipline-subhead" style="color:var(--gold-accent);">
                        <span>⚖️ 盘中开仓与持仓纪律（提升胜率核心法则）</span>
                    </div>
                    <ul class="discipline-list" id="tradingDisciplineList">
                        <!-- Dynamic Trading disciplines -->
                    </ul>

                    <div class="discipline-subhead" style="color:var(--red-bull);">
                        <span>🚨 风险提示与不可抗力应对</span>
                    </div>
                    <ul class="discipline-list" id="riskWarningsList" style="margin-bottom:0;">
                        <!-- Dynamic Risk warnings -->
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- Parameter Customization Modal -->
    <div class="modal-overlay" id="paramModal">
        <div class="modal-box">
            <div class="modal-header">
                <div class="modal-title">⚙️ 短线博弈模型胜率参数设定</div>
                <button class="modal-close" onclick="closeParamModal()">✕</button>
            </div>
            <div style="font-size:12px;color:var(--text-sub);margin-bottom:16px;">
                调整以下博弈风控参数，系统将实时重新计算情绪周期得分、空仓防守预警及建议仓位比例。参数将保存在本地浏览器中，用于复盘对比。
            </div>

            <div class="param-row">
                <div class="param-info">
                    <div class="param-name">炸板率警报阈值 (%)</div>
                    <div class="param-desc">全市场炸板率超过该值时触发防守警报 (默认 30%)</div>
                </div>
                <div class="param-input-group">
                    <input type="number" class="param-input" id="paramBrokenThreshold" value="30" min="10" max="60">
                    <span style="font-size:12px;color:var(--text-sub);">%</span>
                </div>
            </div>

            <div class="param-row">
                <div class="param-info">
                    <div class="param-name">连板晋级率冰点阈值 (%)</div>
                    <div class="param-desc">高位连板晋级率低于该值判定为退潮冰点 (默认 35%)</div>
                </div>
                <div class="param-input-group">
                    <input type="number" class="param-input" id="paramPromotionThreshold" value="35" min="10" max="60">
                    <span style="font-size:12px;color:var(--text-sub);">%</span>
                </div>
            </div>

            <div class="param-row">
                <div class="param-info">
                    <div class="param-name">强封单封成比阈值 (%)</div>
                    <div class="param-desc">涨停封单占成交量比例判定为超强一字板 (默认 50%)</div>
                </div>
                <div class="param-input-group">
                    <input type="number" class="param-input" id="paramSealRatioThreshold" value="50" min="20" max="150">
                    <span style="font-size:12px;color:var(--text-sub);">%</span>
                </div>
            </div>

            <div class="param-row">
                <div class="param-info">
                    <div class="param-name">大盘成交量萎缩预警线 (亿元)</div>
                    <div class="param-desc">两市总成交跌破该金额判定为流动性不足 (默认 8000 亿)</div>
                </div>
                <div class="param-input-group">
                    <input type="number" class="param-input" id="paramVolumeThreshold" value="8000" min="5000" max="20000" step="500">
                    <span style="font-size:12px;color:var(--text-sub);">亿元</span>
                </div>
            </div>

            <div class="modal-footer">
                <button class="action-btn secondary" onclick="resetParams()">恢复默认值</button>
                <button class="action-btn" onclick="applyCustomParams()">保存并重新评估</button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer>
        <p><strong>A股短线博弈每日复盘系统</strong> | 遵循短线情绪周期演化模型、封单博弈论与龙头战法风控纪律</p>
        <p>本工具所有行情数据均源自公开交易所统计，复盘推演仅供量化模型与短线博弈逻辑验证，不构成任何投资买卖建议。股市有风险，入市须谨慎。</p>
        <p style="margin-top:6px;font-size:11px;color:var(--text-dim);">单文件内联架构 · 支持纯离线运行 · 数据基准日期: <span id="footerDateDisplay">2024-03-22</span></p>
    </footer>
</div>

<script>
/* === Embedded Authentic Historical Market Dataset === */
const MARKET_DATABASE = __MARKET_DATABASE_JSON__;
const NON_TRADING_DAYS = __NON_TRADING_DAYS_JSON__;

/* === User Configurable Parameters State === */
let userParams = {
    brokenThreshold: 30,
    promotionThreshold: 35,
    sealRatioThreshold: 50,
    volumeThreshold: 8000
};

// Try loading cached params
try {
    const saved = localStorage.getItem('a_share_review_params');
    if (saved) {
        userParams = Object.assign(userParams, JSON.parse(saved));
    }
} catch (e) {
    console.log("Local storage not available or restricted.");
}

/* === Core Navigation: 选日期 → 点击开始复盘 → 调数据生成报告 === */
const AUTO_REVIEW_DATE = __AUTO_REVIEW_DATE__;

function ymdCompact(dateStr) {
    return (dateStr || "").replace(/-/g, "");
}

function weekdayCn(dateStr) {
    const names = ["日", "一", "二", "三", "四", "五", "六"];
    const d = new Date(dateStr + "T00:00:00");
    return isNaN(d.getTime()) ? "" : names[d.getDay()];
}

function updateQuickButtons(targetDate) {
    document.querySelectorAll(".quick-btn").forEach(btn => {
        const oc = btn.getAttribute("onclick") || "";
        if (targetDate && oc.includes("'" + targetDate + "'")) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

function setReviewLoading(on, label) {
    const btn = document.getElementById("startReviewBtn");
    if (!btn) return;
    btn.disabled = !!on;
    btn.innerText = on ? (label || "正在调取公开行情…") : "开始复盘";
}

function setFooterDate(dateStr) {
    const fd = document.getElementById("footerDateDisplay");
    if (fd) fd.innerText = dateStr || "--";
}

function showIdle(dateStr) {
    const idle = document.getElementById("idleBanner");
    const closed = document.getElementById("closedBanner");
    const trading = document.getElementById("tradingContent");
    idle.style.display = "block";
    closed.style.display = "none";
    trading.style.display = "none";
    const hint = document.getElementById("idleDateHint");
    if (hint) hint.innerText = dateStr || document.getElementById("dateSelect").value;
    document.getElementById("dataTimestampHeader").innerText = "请选择日期后点击「开始复盘」";
    document.getElementById("tradingStatusBadge").innerText = "待复盘";
    setFooterDate(dateStr || document.getElementById("dateSelect").value);
}

function showMissingDate(dateStr, reason) {
    const idle = document.getElementById("idleBanner");
    const closed = document.getElementById("closedBanner");
    const trading = document.getElementById("tradingContent");
    idle.style.display = "none";
    closed.style.display = "block";
    trading.style.display = "none";
    document.getElementById("closedTitle").innerText = `未能生成 ${dateStr} 复盘报告`;
    document.getElementById("closedDesc").innerText = reason || "该日不在本地样本库，且公开行情接口未能返回涨停池/指数数据。请检查网络后再次点击「开始复盘」，或改选已收录交易日。";
    document.getElementById("closedType").innerText = "无可用公开数据";
    document.getElementById("closedPeriod").innerText = dateStr;
    document.getElementById("nextTradingDay").innerText = "可先试 2026-08-13 / 2026-08-14";
    document.getElementById("dataTimestampHeader").innerText = `统计日期：${dateStr} | 未生成报告`;
    document.getElementById("tradingStatusBadge").innerText = "无数据";
    setFooterDate(dateStr);
}

function jsonp(url, timeoutMs) {
    return new Promise((resolve, reject) => {
        const cb = "emcb_" + Date.now().toString(36) + Math.random().toString(16).slice(2, 8);
        let settled = false;
        const timer = setTimeout(() => finish(new Error("timeout")), timeoutMs || 12000);
        function finish(err, data) {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            try { delete window[cb]; } catch (e) {}
            if (script && script.parentNode) script.parentNode.removeChild(script);
            if (err) reject(err); else resolve(data);
        }
        window[cb] = (data) => finish(null, data);
        const script = document.createElement("script");
        script.onerror = () => finish(new Error("jsonp error"));
        const param = url.indexOf("kline") >= 0 ? "callback=" : "cb=";
        script.src = url + (url.indexOf("?") >= 0 ? "&" : "?") + param + cb;
        document.head.appendChild(script);
    });
}

function emPrice(p) {
    const n = Number(p) || 0;
    if (n > 1000) return +(n / 1000).toFixed(2);
    return +n.toFixed(2);
}

function emYi(v) {
    const n = Number(v) || 0;
    if (n > 1e10) return +(n / 1e8).toFixed(2);
    if (n > 1e6) return +(n / 1e8).toFixed(2);
    return +n.toFixed(2);
}

function emWan(v) {
    const n = Number(v) || 0;
    if (n > 1e6) return Math.round(n / 1e4);
    return Math.round(n);
}

function emTime(v) {
    const s = String(v || "").padStart(6, "0");
    if (!v && v !== 0) return "--";
    return s.slice(0, 2) + ":" + s.slice(2, 4) + ":" + s.slice(4, 6);
}

function parseKline(payload) {
    const klines = ((payload || {}).data || {}).klines || [];
    if (!klines.length) return null;
    const p = klines[0].split(",");
    return {
        date: p[0],
        close: parseFloat(p[2]),
        pct: parseFloat(p[8]),
        amountYi: +(parseFloat(p[6]) / 1e8).toFixed(0)
    };
}

function buildReportFromLive(dateStr, ztPool, zbPool, dtPool, shBar, szBar, cyBar) {
    const zt = ztPool || [];
    const zb = zbPool || [];
    const dt = dtPool || [];
    const stocks = zt.map(s => {
        const price = emPrice(s.p);
        const turnover = emYi(s.amount);
        const seal = emWan(s.fund);
        const lbc = s.lbc || 1;
        return {
            code: s.c,
            name: s.n,
            price,
            change: +(s.zdp || 0).toFixed(2),
            concept: s.hybk || s.hy || "涨停",
            turnover,
            turnover_rate: +(s.hs || 0).toFixed(2),
            seal_amount: seal,
            seal_ratio: turnover > 0 ? +((seal / 10000) / turnover * 100).toFixed(2) : 0,
            seal_time: emTime(s.fbt),
            breaks: s.zbc || 0,
            status: (s.zbc ? "回封" : "封板") + (lbc > 1 ? lbc + "连板" : "首板"),
            boards: lbc
        };
    });
    stocks.sort((a, b) => b.boards - a.boards || b.seal_amount - a.seal_amount);
    const maxH = stocks.length ? stocks[0].boards : 0;
    const leader = stocks[0] || {code: "--", name: "—", boards: 0, price: 0, change: 0, turnover: 0, turnover_rate: 0, concept: ""};
    const groups = {};
    stocks.forEach(s => {
        const k = s.boards >= 2 ? s.boards + "连板" : "首板精选";
        if (!groups[k]) groups[k] = [];
        groups[k].push(s);
    });
    const ladder = Object.keys(groups).sort((a, b) => {
        const na = parseInt(a, 10) || 0;
        const nb = parseInt(b, 10) || 0;
        return nb - na;
    }).map(tier => ({
        tier,
        count: groups[tier].length,
        stocks: groups[tier].slice(0, tier.indexOf("首板") === 0 ? 8 : 8)
    }));
    const broken = zb.slice(0, 8).map(s => ({
        code: s.c,
        name: s.n,
        price: emPrice(s.p),
        change: +(s.zdp || 0).toFixed(2),
        max_change: 10,
        concept: s.hybk || "炸板",
        turnover: emYi(s.amount),
        reason: "公开涨停池：盘中触及涨停后打开，收盘未封住"
    }));
    const sealing = stocks.slice().sort((a, b) => b.seal_amount - a.seal_amount).slice(0, 8).map((s, i) => ({
        rank: i + 1,
        code: s.code,
        name: s.name,
        boards: s.boards,
        seal_amount: s.seal_amount,
        seal_ratio: s.seal_ratio,
        free_float_ratio: 0,
        first_seal: s.seal_time,
        breaks: s.breaks,
        stars: s.seal_ratio > 50 || s.breaks === 0 ? 5 : 3,
        premium_exp: s.breaks === 0 ? "高（未开板）" : "中（有开板）"
    }));
    const hyMap = {};
    stocks.forEach(s => {
        const hy = s.concept || "其他";
        if (!hyMap[hy]) hyMap[hy] = {name: hy, inflow: 0, change: 0, leaders: [], limit_ups: 0};
        hyMap[hy].limit_ups += 1;
        hyMap[hy].inflow += s.turnover;
        if (hyMap[hy].leaders.length < 3) hyMap[hy].leaders.push(s.name);
    });
    const sectors = Object.values(hyMap).sort((a, b) => b.limit_ups - a.limit_ups).slice(0, 5)
        .map(x => ({name: x.name, inflow: +x.inflow.toFixed(1), change: 0, leaders: x.leaders.join("、"), limit_ups: x.limit_ups}));
    const lu = zt.length;
    const br = zb.length;
    const brokenRate = (lu + br) > 0 ? +(br / (lu + br) * 100).toFixed(2) : 0;
    const highCnt = stocks.filter(s => s.boards >= 3).length;
    const promoHigh = highCnt >= 2 ? 50 : (maxH >= 5 ? 40 : 30);
    let phase = "修复期";
    let score = 50;
    if (brokenRate > 35 && lu < 50) { phase = "退潮期"; score = 28; }
    else if (brokenRate > 28 || (shBar && shBar.pct < 0 && lu < 80)) { phase = "分歧期"; score = 42; }
    else if (lu > 200) { phase = "高潮期"; score = 90; }
    else if (maxH >= 5 && brokenRate < 25) { phase = "发酵期"; score = 72; }
    const pos = score < 35 ? "0~2成 (防守)" : score < 55 ? "2~4成 (试错)" : score < 75 ? "5~7成 (主线)" : "7~9成 (进攻)";
    const shAmt = (shBar && shBar.amountYi) || 0;
    const szAmt = (szBar && szBar.amountYi) || 0;
    const totalTurnover = shAmt && szAmt ? shAmt + szAmt : (shAmt || szAmt);
    const wd = weekdayCn(dateStr);
    return {
        is_trading_day: true,
        date: dateStr,
        date_cn: dateStr.replace(/-/, "年").replace(/-/, "月") + "日" + (wd ? " 星期" + wd : ""),
        data_source: "东方财富公开涨停池/炸板池/跌停池与指数日K（点击「开始复盘」实时调取）。封单、连板以接口字段为准。",
        live_fetched: true,
        market_summary: {
            sh_index: shBar ? shBar.close : 0,
            sh_change: shBar ? shBar.pct : 0,
            sz_index: szBar ? szBar.close : 0,
            sz_change: szBar ? szBar.pct : 0,
            cy_index: cyBar ? cyBar.close : 0,
            cy_change: cyBar ? cyBar.pct : 0,
            total_turnover: totalTurnover,
            turnover_change: 0,
            up_count: 0,
            down_count: 0,
            flat_count: 0,
            median_change: shBar ? shBar.pct : 0,
            limit_up_count: lu,
            limit_down_count: dt.length,
            broken_board_count: br,
            consecutive_board_count: stocks.filter(s => s.boards >= 2).length,
            broken_board_rate: brokenRate,
            promotion_rate_1_to_2: promoHigh,
            promotion_rate_2_to_3: promoHigh,
            promotion_rate_high: promoHigh,
            max_height: maxH,
            max_height_stock: leader.name + " (" + leader.code + ") " + maxH + "连板",
            sentiment_phase: phase,
            sentiment_phase_en: phase,
            sentiment_score: score,
            cash_defense_score: Math.max(0, 100 - Math.round(brokenRate * 1.5)),
            suggested_position: pos,
            core_themes: sectors.slice(0, 4).map(s => s.name)
        },
        absolute_high: {
            title: "实时调取：" + leader.name + maxH + "连板，涨停" + lu + " / 炸板" + br,
            leader_code: leader.code,
            leader_name: leader.name,
            concept: leader.concept,
            consecutive_boards: leader.boards,
            close_price: leader.price,
            change_percent: leader.change,
            turnover: leader.turnover,
            turnover_rate: leader.turnover_rate,
            seal_status: leader.status,
            intraday_behavior: "来自东方财富涨停池：连板" + leader.boards + "，封单约" + (leader.seal_amount / 10000).toFixed(2) + "亿元。",
            sub_leader_code: stocks[1] ? stocks[1].code : "",
            sub_leader_name: stocks[1] ? stocks[1].name : "",
            sub_leader_concept: stocks[1] ? stocks[1].concept : "",
            sub_leader_boards: stocks[1] ? stocks[1].boards : 0,
            sub_leader_change: stocks[1] ? stocks[1].change : 0,
            sub_leader_status: stocks[1] ? stocks[1].status : "",
            height_analysis: "该报告由「开始复盘」调用公开接口即时生成。指数成交为沪+深日K成交额合计（若接口返回）。涨跌家数若为0表示接口未提供全市场涨跌统计。",
            strategy_holding: "按封成比与开板次数去弱留强，不因高度无脑锁仓。",
            strategy_buying: "仓位参考情绪阶段；接口数据仅作复盘骨架，细节以交易所收盘统计为准。"
        },
        ladder_matrix: ladder,
        broken_board_list: broken,
        sealing_strength_ranking: sealing,
        main_capital_flow: {sectors_inflow: sectors, sectors_outflow: []},
        popularity_anchors: stocks.slice().sort((a, b) => b.turnover - a.turnover).slice(0, 5).map((s, i) => ({
            rank: i + 1, code: s.code, name: s.name, turnover: s.turnover, change: s.change,
            role: s.boards + "板成交锚点",
            analysis: "涨停池成交约" + s.turnover + "亿元。"
        })),
        dragon_tiger_list: [{
            seat_name: "龙虎榜",
            style: "实时接口未附带营业部明细",
            actions: [{stock: "—", net_buy: 0, type: "请对照交易所次日公开信息", comment: "涨停池接口不含席位净额"}]
        }],
        cash_defense_checklist: [
            {id: "c1", rule: "高位总龙头断板并出现直接跌停或恶性负反馈", status: dt.length ? "WARN" : "SAFE", triggered: dt.length > 0, detail: "跌停池 " + dt.length + " 只。"},
            {id: "c2", rule: "全市场炸板率超过 30% 警报线", status: brokenRate > 30 ? "DANGER" : "SAFE", triggered: brokenRate > 30, detail: "炸板率 " + brokenRate + "%（" + br + "/" + (lu + br) + "）。"},
            {id: "c3", rule: "连板晋级率跌破 35% 冰点阈值", status: "SAFE", triggered: false, detail: "实时接口未直接给晋级率，请结合连板高度观察。"},
            {id: "c4", rule: "日内天地板或大幅回撤超10%股票数量 >= 3只", status: dt.length >= 3 ? "WARN" : "SAFE", triggered: dt.length >= 3, detail: "跌停 " + dt.length + " 只。"},
            {id: "c5", rule: "大盘指数破位且两市成交量出现严重断崖式萎缩", status: "SAFE", triggered: false, detail: "沪指 " + (shBar ? shBar.close : "--") + "，两市成交约 " + totalTurnover + " 亿元。"},
            {id: "c6", rule: "题材一日游轮动加剧，前日连板次日大幅低开计提", status: "SAFE", triggered: false, detail: "需对照前一交易日样本。"},
            {id: "c7", rule: "处于情绪退潮期第二阶段（主跌杀中位与补跌）", status: phase === "退潮期" ? "DANGER" : "SAFE", triggered: phase === "退潮期", detail: "模型判定：" + phase + "。"}
        ],
        next_day_discipline: {
            bidding_rules: ["竞价先看高度板 " + leader.name + " 封单与开板。", "炸板率偏高时，中位一字默认放弃。"],
            trading_discipline: ["仓位按建议执行。", "只做涨停池里封成比高、开板次数少的前排。"],
            risk_warnings: ["实时接口可能漏掉ST口径或北交所，与媒体家数不完全一致。"]
        }
    };
}

async function fetchLiveReview(dateStr) {
    const ymd = ymdCompact(dateStr);
    const ut = "7eea3edcaed734bea9cbfc244ea521cf";
    const ztUrl = `https://push2ex.eastmoney.com/getTopicZTPool?ut=${ut}&dpt=wz.ztzt&Pageindex=0&pagesize=200&sort=lbc:desc&date=${ymd}`;
    const zbUrl = `https://push2ex.eastmoney.com/getTopicZBPool?ut=${ut}&dpt=wz.ztzt&Pageindex=0&pagesize=200&date=${ymd}`;
    const dtUrl = `https://push2ex.eastmoney.com/getTopicDTPool?ut=${ut}&dpt=wz.ztzt&Pageindex=0&pagesize=100&date=${ymd}`;
    const kline = (secid) => `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&beg=${ymd}&end=${ymd}`;
    const [ztRes, zbRes, dtRes, shRes, szRes, cyRes] = await Promise.all([
        jsonp(ztUrl).catch(() => null),
        jsonp(zbUrl).catch(() => null),
        jsonp(dtUrl).catch(() => null),
        jsonp(kline("1.000001")).catch(() => null),
        jsonp(kline("0.399001")).catch(() => null),
        jsonp(kline("0.399006")).catch(() => null)
    ]);
    const ztPool = ((ztRes || {}).data || {}).pool || [];
    const zbPool = ((zbRes || {}).data || {}).pool || [];
    const dtPool = ((dtRes || {}).data || {}).pool || [];
    if (!ztPool.length && !parseKline(shRes)) {
        throw new Error("公开接口未返回该日涨停池或指数K线");
    }
    return buildReportFromLive(dateStr, ztPool, zbPool, dtPool, parseKline(shRes), parseKline(szRes), parseKline(cyRes));
}

async function startReview(presetDate) {
    const dateInput = document.getElementById("dateSelect");
    if (presetDate) dateInput.value = presetDate;
    const dateStr = dateInput.value;
    if (!dateStr) {
        showMissingDate("--", "请先选择日期，再点击「开始复盘」。");
        return;
    }
    updateQuickButtons(dateStr);
    const idleHint = document.getElementById("idleDateHint");
    if (idleHint) idleHint.innerText = dateStr;
    setReviewLoading(true, "正在调取 " + dateStr + " 行情…");
    try {
        await runReviewForDate(dateStr);
    } finally {
        setReviewLoading(false);
    }
}

async function runReviewForDate(dateStr) {
    document.getElementById("idleBanner").style.display = "none";

    if (NON_TRADING_DAYS[dateStr]) {
        renderClosedDay(NON_TRADING_DAYS[dateStr]);
        return;
    }
    const parsedDate = new Date(dateStr + "T00:00:00");
    const dayOfWeek = parsedDate.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) {
        renderWeekend(dateStr);
        return;
    }
    if (MARKET_DATABASE[dateStr]) {
        renderTradingDay(MARKET_DATABASE[dateStr]);
        return;
    }
    try {
        const live = await fetchLiveReview(dateStr);
        MARKET_DATABASE[dateStr] = live;
        renderTradingDay(live);
    } catch (err) {
        showMissingDate(dateStr, "已点击「开始复盘」，但 " + dateStr + " 不在本地样本库，公开行情接口也没有返回可用数据（" + (err && err.message ? err.message : "网络或跨域限制") + "）。样本库已收录 2026-08-13、2026-08-14 等交易日，可先选这些日期再点复盘。");
    }
}

function renderClosedDay(closedInfo) {
    document.getElementById("idleBanner").style.display = "none";
    document.getElementById("closedBanner").style.display = "block";
    document.getElementById("tradingContent").style.display = "none";
    const badge = document.getElementById("tradingStatusBadge");
    badge.innerText = "休市中";
    badge.className = "badge";
    badge.style.background = "rgba(210, 153, 34, 0.15)";
    badge.style.color = "#d29922";
    badge.style.borderColor = "rgba(210, 153, 34, 0.4)";
    document.getElementById("dataTimestampHeader").innerText = `统计日期：${closedInfo.date_cn} | 交易所闭市中`;
    document.getElementById("closedTitle").innerText = `休市公告：${closedInfo.holiday_name} (非交易日)`;
    document.getElementById("closedDesc").innerText = closedInfo.reason + " " + closedInfo.guidance;
    document.getElementById("closedType").innerText = closedInfo.holiday_name;
    document.getElementById("closedPeriod").innerText = closedInfo.holiday_period;
    document.getElementById("nextTradingDay").innerText = closedInfo.next_trading_day_cn;
    setFooterDate(closedInfo.date);
}

function renderWeekend(dateStr) {
    document.getElementById("idleBanner").style.display = "none";
    document.getElementById("closedBanner").style.display = "block";
    document.getElementById("tradingContent").style.display = "none";
    const badge = document.getElementById("tradingStatusBadge");
    badge.innerText = "周末休市";
    badge.className = "badge";
    badge.style.background = "rgba(210, 153, 34, 0.15)";
    badge.style.color = "#d29922";
    badge.style.borderColor = "rgba(210, 153, 34, 0.4)";
    document.getElementById("dataTimestampHeader").innerText = `统计日期：${dateStr} (周末) | 证券交易所正常闭市维护`;
    document.getElementById("closedTitle").innerText = "休市公告：周末常规休市 (非交易日)";
    document.getElementById("closedDesc").innerText = "所选日期为周末休市时间，A股市场无行情撮合与资金交收。请改选交易日后再点击「开始复盘」。";
    document.getElementById("closedType").innerText = "常规周末闭市";
    document.getElementById("closedPeriod").innerText = "周六至周日";
    document.getElementById("nextTradingDay").innerText = "下周一 09:30 正常开市";
    setFooterDate(dateStr);
}

function renderTradingDay(data) {
    document.getElementById("idleBanner").style.display = "none";
    document.getElementById("closedBanner").style.display = "none";
    document.getElementById("tradingContent").style.display = "block";
    setFooterDate(data.date);
    const badge = document.getElementById("tradingStatusBadge");
    badge.innerText = data.live_fetched ? "实时调取已生成" : "交易日正常复盘";
    badge.className = "badge";
    badge.style.background = "rgba(248, 81, 73, 0.15)";
    badge.style.color = "#f85149";
    badge.style.borderColor = "rgba(248, 81, 73, 0.4)";
    const sourceNote = data.data_source ? ` | 数据来源：${data.data_source}` : "";
    document.getElementById("dataTimestampHeader").innerText = `数据统计日期：${data.date_cn}${sourceNote}`;
    const dynamicEval = evaluateMarketDynamically(data.market_summary, data.broken_board_list, data.absolute_high);
    renderMarketStats(data, dynamicEval);
    renderSentimentCycle(data, dynamicEval);
    renderAbsoluteHigh(data);
    renderLadderMatrix(data);
    renderSealingStrength(data);
    renderCapitalFlow(data);
    renderDragonTiger(data);
    renderCashDefense(data, dynamicEval);
    renderDiscipline(data);
}

function switchDate(targetDate) {
    startReview(targetDate);
}

document.getElementById("dateSelect").addEventListener("change", function(e) {
    const dateStr = e.target.value;
    updateQuickButtons(dateStr);
    // 改日期本身不生成报告，必须再点「开始复盘」
    showIdle(dateStr);
});

document.getElementById("dateSelect").addEventListener("keydown", function(e) {
    if (e.key === "Enter") {
        e.preventDefault();
        startReview();
    }
});

/* === Dynamic Quantitative Sentiment & Defense Evaluation Engine === */
function evaluateMarketDynamically(rawSummary, brokenList, leaderData) {
    const s = Object.assign({}, rawSummary);
    const brokenThreshold = userParams.brokenThreshold || 30;
    const promotionThreshold = userParams.promotionThreshold || 35;
    const volumeThreshold = userParams.volumeThreshold || 8000;

    let penalty = 0;
    let sentimentScore = s.sentiment_score;

    // Check 1: Broken Board Rate Penalty
    if (s.broken_board_rate > brokenThreshold) {
        const excess = s.broken_board_rate - brokenThreshold;
        penalty += Math.min(25, excess * 1.5);
    }

    // Check 2: Promotion Rate
    if (s.promotion_rate_high < promotionThreshold) {
        const deficit = promotionThreshold - s.promotion_rate_high;
        penalty += Math.min(20, deficit * 1.2);
    }

    // Check 3: Total Turnover
    if (s.total_turnover < volumeThreshold) {
        penalty += 15;
    }

    // Check 4: Leader drop
    if (leaderData && leaderData.change_percent < -5) {
        penalty += 20;
    }

    let calculatedDefenseScore = Math.max(10, Math.min(100, Math.round(100 - penalty)));
    let dynamicPhase = s.sentiment_phase;
    let dynamicPosition = s.suggested_position;

    if (calculatedDefenseScore < 35) {
        dynamicPhase = "退潮期";
        dynamicPosition = "0~2成 (严格空仓防守)";
    } else if (calculatedDefenseScore < 55) {
        dynamicPhase = "分歧期";
        dynamicPosition = "2~4成 (防守试错)";
    } else if (calculatedDefenseScore < 75) {
        dynamicPhase = "修复期";
        dynamicPosition = "4~6成 (局部试错)";
    } else {
        dynamicPhase = s.sentiment_phase === "高潮期" ? "高潮期" : "主升期";
        dynamicPosition = "7~10成 (主线进攻)";
    }

    return {
        defenseScore: calculatedDefenseScore,
        sentimentScore: sentimentScore,
        phase: dynamicPhase,
        position: dynamicPosition,
        brokenTriggered: s.broken_board_rate > brokenThreshold,
        promotionTriggered: s.promotion_rate_high < promotionThreshold,
        volumeTriggered: s.total_turnover < volumeThreshold
    };
}

/* === Main Render Dispatcher === */
function renderReviewPage(dateStr) {
    setFooterDate(dateStr);
    return runReviewForDate(dateStr);
}

/* === Render Helpers === */
function renderMarketStats(data, dynamicEval) {
    const s = data.market_summary;
    document.getElementById('shIndexVal').innerText = s.sh_index.toFixed(2);
    document.getElementById('shChangeVal').innerText = (s.sh_change >= 0 ? '+' : '') + s.sh_change.toFixed(2) + '%';
    document.getElementById('shChangeVal').className = 'stat-sub ' + (s.sh_change >= 0 ? 'up-red' : 'down-green');
    document.getElementById('shTrendIcon').innerText = s.sh_change >= 0 ? '▲' : '▼';
    document.getElementById('shTrendIcon').className = s.sh_change >= 0 ? 'up-red' : 'down-green';

    document.getElementById('totalTurnoverVal').innerHTML = `${s.total_turnover.toLocaleString()} <span style="font-size:14px;font-weight:400;color:var(--text-sub)">亿元</span>`;
    document.getElementById('turnoverChangeVal').innerText = `${s.turnover_change >= 0 ? '较昨日放量 +' : '较昨日缩量 '}${s.turnover_change} 亿元`;

    document.getElementById('upCountVal').innerText = s.up_count;
    document.getElementById('downCountVal').innerText = s.down_count;
    document.getElementById('medianChangeVal').innerText = `全市场中位数：${s.median_change >= 0 ? '+' : ''}${s.median_change.toFixed(2)}%`;

    document.getElementById('limitUpVal').innerText = s.limit_up_count;
    document.getElementById('limitDownVal').innerText = s.limit_down_count;
    document.getElementById('brokenBoardRateVal').innerText = `炸板率：${s.broken_board_rate.toFixed(2)}% (${s.broken_board_count}家炸板)`;

    document.getElementById('sentimentPhaseVal').innerText = dynamicEval.phase;
    document.getElementById('suggestedPositionVal').innerText = `建议仓位：${dynamicEval.position}`;
}

function renderSentimentCycle(data, dynamicEval) {
    const s = data.market_summary;
    document.getElementById('cycleScoreTag').innerText = `综合博弈得分: ${s.sentiment_score}分`;
    
    // Reset stages
    ['stageRepair', 'stageMain', 'stageDiverge', 'stageRecede'].forEach(id => {
        document.getElementById(id).classList.remove('active');
    });

    const phase = dynamicEval.phase;
    if (phase === '修复期') {
        document.getElementById('stageRepair').classList.add('active');
        document.getElementById('currentPhaseDesc').innerText = '修复期 (冰点出清，低位空间板试错启动)';
        document.getElementById('defenseAlertLevel').innerText = '中等偏轻';
        document.getElementById('defenseAlertLevel').className = 'blue-highlight';
    } else if (phase === '发酵期' || phase === '主升期' || phase === '高潮期') {
        document.getElementById('stageMain').classList.add('active');
        document.getElementById('currentPhaseDesc').innerText = phase === '高潮期' ? '高潮期 (主线全面爆发，情绪一致性加速)' : '主升期 (主线梯队良性扩散，做多意愿强烈)';
        document.getElementById('defenseAlertLevel').innerText = '安全进攻';
        document.getElementById('defenseAlertLevel').className = 'down-green';
    } else if (phase === '分歧期') {
        document.getElementById('stageDiverge').classList.add('active');
        document.getElementById('currentPhaseDesc').innerText = '分歧期 (高位龙头松动，获利盘兑现与新老题材交替)';
        document.getElementById('defenseAlertLevel').innerText = '高危防守';
        document.getElementById('defenseAlertLevel').className = 'neutral-gold';
    } else {
        document.getElementById('stageRecede').classList.add('active');
        document.getElementById('currentPhaseDesc').innerText = '退潮期 (龙头A杀补跌，中位板遭遇重创)';
        document.getElementById('defenseAlertLevel').innerText = '极度高危 (强制空仓)';
        document.getElementById('defenseAlertLevel').className = 'up-red';
    }

    document.getElementById('promotionRatesVal').innerText = `${s.promotion_rate_1_to_2.toFixed(1)}% / ${s.promotion_rate_2_to_3.toFixed(1)}% / ${s.promotion_rate_high.toFixed(1)}%`;
    document.getElementById('marketMaxHeightVal').innerText = `${s.max_height}连板 (${s.max_height_stock})`;
    document.getElementById('coreThemesVal').innerText = s.core_themes.join('、');
    
    if (dynamicEval.defenseScore >= 80) {
        document.getElementById('strategyAdviceVal').innerText = '顺势做多，聚焦核心主线容量中军持股';
    } else if (dynamicEval.defenseScore >= 60) {
        document.getElementById('strategyAdviceVal').innerText = '主线进攻，积极参与1进2与前排加速';
    } else if (dynamicEval.defenseScore >= 40) {
        document.getElementById('strategyAdviceVal').innerText = '防守试错，高位坚决不接力，轻仓打板低位新题材';
    } else {
        document.getElementById('strategyAdviceVal').innerText = '严格空仓防守，保住本金，拒绝伸手接飞刀';
    }
}

function renderAbsoluteHigh(data) {
    const high = data.absolute_high;
    document.getElementById('leaderNameVal').innerText = `${high.leader_name} (${high.leader_code})`;
    document.getElementById('leaderBoardsVal').innerText = `${high.consecutive_boards}连板 - ${high.seal_status}`;
    document.getElementById('leaderPriceChangeVal').innerText = `${high.close_price.toFixed(2)}元 (${high.change_percent >= 0 ? '+' : ''}${high.change_percent.toFixed(2)}%)`;
    document.getElementById('leaderPriceChangeVal').className = high.change_percent >= 0 ? 'up-red' : 'down-green';
    
    document.getElementById('leaderBehaviorDesc').innerText = high.intraday_behavior;
    document.getElementById('highHeightAnalysisVal').innerText = high.height_analysis;
    document.getElementById('holdingDisciplineVal').innerText = high.strategy_holding;
    document.getElementById('lowTrialDirectionVal').innerText = high.strategy_buying;
}

function renderLadderMatrix(data) {
    const container = document.getElementById('ladderContainer');
    container.innerHTML = '';

    data.ladder_matrix.forEach(tier => {
        const tierBox = document.createElement('div');
        tierBox.className = 'ladder-tier';

        const tierHead = document.createElement('div');
        tierHead.className = 'tier-header';
        tierHead.innerHTML = `
            <div class="tier-title">
                <span style="color:var(--red-bull);">⚡</span> ${tier.tier}
                <span class="tier-badge">${tier.count} 家</span>
            </div>
            <div style="font-size:12px;color:var(--text-sub);">
                梯队样本全景统计
            </div>
        `;
        tierBox.appendChild(tierHead);

        const table = document.createElement('table');
        table.className = 'stock-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>股票名称/代码</th>
                    <th>最新价</th>
                    <th>涨跌幅</th>
                    <th>核心题材概念</th>
                    <th>成交额(亿)</th>
                    <th>换手率</th>
                    <th>封单额(万)</th>
                    <th>封成比</th>
                    <th>封板时间</th>
                    <th>盘口状态</th>
                </tr>
            </thead>
            <tbody>
                ${tier.stocks.map(s => `
                    <tr>
                        <td>
                            <div class="stock-name-cell">
                                <span class="stock-name">${s.name}</span>
                                <span class="stock-code">${s.code}</span>
                            </div>
                        </td>
                        <td style="font-weight:700;">${s.price.toFixed(2)}</td>
                        <td class="${s.change >= 0 ? 'up-red' : 'down-green'}" style="font-weight:700;">${s.change >= 0 ? '+' : ''}${s.change.toFixed(2)}%</td>
                        <td style="color:var(--text-main);">${s.concept}</td>
                        <td>${s.turnover.toFixed(2)}</td>
                        <td>${s.turnover_rate.toFixed(2)}%</td>
                        <td style="font-weight:600;">${s.seal_amount.toLocaleString()}</td>
                        <td style="font-weight:600;color:${s.seal_ratio > 30 ? 'var(--red-bull)' : 'var(--text-main)'};">${s.seal_ratio.toFixed(2)}%</td>
                        <td style="font-family:monospace;">${s.seal_time}</td>
                        <td>
                            <span class="seal-pill ${s.status.includes('一字') ? 'seal-perfect' : (s.status.includes('断板') ? 'seal-break' : 'seal-good')}">
                                ${s.status}
                            </span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        tierBox.appendChild(table);
        container.appendChild(tierBox);
    });
}

function renderSealingStrength(data) {
    const tbody = document.getElementById('sealingTableBody');
    tbody.innerHTML = '';

    data.sealing_strength_ranking.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong style="color:var(--gold-accent);">#${item.rank}</strong></td>
            <td><strong>${item.name}</strong> <span style="font-size:10px;color:var(--text-dim);">(${item.code})</span></td>
            <td><span class="seal-pill seal-perfect">${item.boards}板</span></td>
            <td><strong>${item.seal_amount.toLocaleString()} 万元</strong></td>
            <td style="font-weight:700;color:var(--red-bull);">${item.seal_ratio.toFixed(1)}%</td>
            <td style="font-family:monospace;">${item.first_seal}</td>
            <td style="color:var(--blue-accent);font-weight:600;">${item.premium_exp}</td>
        `;
        tbody.appendChild(tr);
    });

    const brokenContainer = document.getElementById('brokenBoardList');
    brokenContainer.innerHTML = '';
    if (data.broken_board_list.length === 0) {
        brokenContainer.innerHTML = `<div style="font-size:12px;color:var(--green-bear);padding:8px;">✅ 当日无恶性高位炸板大面标的，接力情绪良好。</div>`;
    } else {
        data.broken_board_list.forEach(b => {
            const div = document.createElement('div');
            div.style.background = 'var(--bg-dark)';
            div.style.border = '1px solid var(--card-border)';
            div.style.padding = '10px 12px';
            div.style.borderRadius = 'var(--radius-sm)';
            div.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <div>
                        <strong style="color:var(--text-main);">${b.name} (${b.code})</strong>
                        <span style="font-size:11px;color:var(--text-sub);margin-left:6px;">${b.concept}</span>
                    </div>
                    <div>
                        <span class="down-green" style="font-weight:700;">收盘 ${b.change >= 0 ? '+' : ''}${b.change.toFixed(2)}%</span>
                        <span style="font-size:11px;color:var(--text-dim);margin-left:4px;">(最高 +${b.max_change.toFixed(1)}%)</span>
                    </div>
                </div>
                <div style="font-size:11px;color:var(--red-bull);">
                    ⚠️ 炸板异动归因：${b.reason}
                </div>
            `;
            brokenContainer.appendChild(div);
        });
    }
}

function renderCapitalFlow(data) {
    const container = document.getElementById('capitalFlowContainer');
    container.innerHTML = '';

    const inflowBox = document.createElement('div');
    inflowBox.style.background = 'var(--bg-dark)';
    inflowBox.style.border = '1px solid var(--card-border)';
    inflowBox.style.padding = '12px';
    inflowBox.style.borderRadius = 'var(--radius-md)';
    inflowBox.innerHTML = `
        <div style="font-size:12px;font-weight:700;color:var(--red-bull);margin-bottom:8px;">
            🔺 主力净流入 Top 板块
        </div>
        ${data.main_capital_flow.sectors_inflow.map(s => `
            <div style="margin-bottom:8px;font-size:12px;border-bottom:1px dashed rgba(48,54,61,0.5);padding-bottom:4px;">
                <div style="display:flex;justify-content:space-between;font-weight:600;">
                    <span>${s.name} (${s.limit_ups}板)</span>
                    <span class="up-red">+${s.inflow} 亿 (+${s.change}%)</span>
                </div>
                <div style="font-size:11px;color:var(--text-sub);margin-top:2px;">领涨：${s.leaders}</div>
            </div>
        `).join('')}
    `;
    container.appendChild(inflowBox);

    const outflowBox = document.createElement('div');
    outflowBox.style.background = 'var(--bg-dark)';
    outflowBox.style.border = '1px solid var(--card-border)';
    outflowBox.style.padding = '12px';
    outflowBox.style.borderRadius = 'var(--radius-md)';
    outflowBox.innerHTML = `
        <div style="font-size:12px;font-weight:700;color:var(--green-bear);margin-bottom:8px;">
            🔻 主力净流出 Top 板块
        </div>
        ${data.main_capital_flow.sectors_outflow.length === 0 ? '<div style="font-size:12px;color:var(--text-sub);padding:6px;">牛市普涨，主力无规模性流出板块</div>' : data.main_capital_flow.sectors_outflow.map(s => `
            <div style="margin-bottom:8px;font-size:12px;border-bottom:1px dashed rgba(48,54,61,0.5);padding-bottom:4px;">
                <div style="display:flex;justify-content:space-between;font-weight:600;">
                    <span>${s.name}</span>
                    <span class="down-green">${s.outflow} 亿 (${s.change}%)</span>
                </div>
                <div style="font-size:11px;color:var(--text-dim);margin-top:2px;">${s.reason}</div>
            </div>
        `).join('')}
    `;
    container.appendChild(outflowBox);

    // Popularity Anchors
    const anchorContainer = document.getElementById('popularityAnchorsList');
    anchorContainer.innerHTML = '';
    data.popularity_anchors.forEach(p => {
        const item = document.createElement('div');
        item.style.background = 'var(--bg-dark)';
        item.style.border = '1px solid var(--card-border)';
        item.style.padding = '10px 12px';
        item.style.borderRadius = 'var(--radius-sm)';
        item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="color:var(--gold-accent);font-weight:700;">#${p.rank}</span>
                    <strong style="color:var(--text-main);margin-left:6px;">${p.name} (${p.code})</strong>
                    <span class="seal-pill seal-good" style="margin-left:6px;">${p.role}</span>
                </div>
                <div>
                    <span style="font-size:12px;font-weight:600;">成交额: <strong>${p.turnover.toFixed(2)} 亿</strong></span>
                    <span class="${p.change >= 0 ? 'up-red' : 'down-green'}" style="margin-left:8px;font-weight:700;">${p.change >= 0 ? '+' : ''}${p.change.toFixed(2)}%</span>
                </div>
            </div>
            <div style="font-size:11px;color:var(--text-sub);margin-top:4px;line-height:1.5;">
                ${p.analysis}
            </div>
        `;
        anchorContainer.appendChild(item);
    });
}

function renderDragonTiger(data) {
    const container = document.getElementById('lhbContainer');
    container.innerHTML = '';

    data.dragon_tiger_list.forEach(item => {
        const card = document.createElement('div');
        card.className = 'lhb-card';
        card.innerHTML = `
            <div class="lhb-seat-head">
                <div class="seat-name">
                    <span>🏛️</span> ${item.seat_name}
                </div>
                <span class="seat-style">${item.style}</span>
            </div>
            <div class="lhb-actions-list">
                ${item.actions.map(act => `
                    <div class="lhb-action-item">
                        <span class="lhb-action-stock">${act.stock}</span>
                        <span class="lhb-action-val ${act.type.includes('净买入') ? 'up-red' : 'down-green'}">${act.type}</span>
                    </div>
                    <div class="lhb-action-comment">💬 战术逻辑：${act.comment}</div>
                `).join('')}
            </div>
        `;
        container.appendChild(card);
    });
}

function renderCashDefense(data, dynamicEval) {
    const container = document.getElementById('cashChecklistContainer');
    container.innerHTML = '';
    const score = dynamicEval ? dynamicEval.defenseScore : data.market_summary.cash_defense_score;
    
    document.getElementById('cashScoreTag').innerText = `防守得分: ${score}/100`;

    data.cash_defense_checklist.forEach(item => {
        const div = document.createElement('div');
        div.className = `check-item ${item.triggered ? 'triggered' : ''}`;
        
        let badgeHtml = '';
        if (item.status === 'SAFE') {
            badgeHtml = `<span class="check-status-badge badge-safe">未触发 (安全)</span>`;
        } else if (item.status === 'WARN') {
            badgeHtml = `<span class="check-status-badge badge-warn">已触发 (警报)</span>`;
        } else {
            badgeHtml = `<span class="check-status-badge badge-danger">高危触发 (极度危险)</span>`;
        }

        div.innerHTML = `
            <div>${badgeHtml}</div>
            <div class="check-content">
                <div class="check-rule">${item.rule}</div>
                <div class="check-detail">${item.detail}</div>
            </div>
        `;
        container.appendChild(div);
    });
}

function renderDiscipline(data) {
    const disc = data.next_day_discipline;
    
    document.getElementById('biddingRulesList').innerHTML = disc.bidding_rules.map(r => `<li>${r}</li>`).join('');
    document.getElementById('tradingDisciplineList').innerHTML = disc.trading_discipline.map(r => `<li>${r}</li>`).join('');
    document.getElementById('riskWarningsList').innerHTML = disc.risk_warnings.map(r => `<li>${r}</li>`).join('');
}

/* === Parameter Modal Management === */
function openParamModal() {
    document.getElementById('paramBrokenThreshold').value = userParams.brokenThreshold;
    document.getElementById('paramPromotionThreshold').value = userParams.promotionThreshold;
    document.getElementById('paramSealRatioThreshold').value = userParams.sealRatioThreshold;
    document.getElementById('paramVolumeThreshold').value = userParams.volumeThreshold;
    document.getElementById('paramModal').style.display = 'flex';
}

function closeParamModal() {
    document.getElementById('paramModal').style.display = 'none';
}

function resetParams() {
    userParams = {
        brokenThreshold: 30,
        promotionThreshold: 35,
        sealRatioThreshold: 50,
        volumeThreshold: 8000
    };
    openParamModal();
}

function applyCustomParams() {
    userParams.brokenThreshold = parseFloat(document.getElementById('paramBrokenThreshold').value) || 30;
    userParams.promotionThreshold = parseFloat(document.getElementById('paramPromotionThreshold').value) || 35;
    userParams.sealRatioThreshold = parseFloat(document.getElementById('paramSealRatioThreshold').value) || 50;
    userParams.volumeThreshold = parseFloat(document.getElementById('paramVolumeThreshold').value) || 8000;

    try {
        localStorage.setItem('a_share_review_params', JSON.stringify(userParams));
    } catch (e) {}

    closeParamModal();
    const trading = document.getElementById('tradingContent');
    if (trading && trading.style.display === 'block') {
        const curDate = document.getElementById('dateSelect').value;
        renderReviewPage(curDate);
    }
}

// Initialize: named files / ?date= auto-run; index.html stays idle until 开始复盘
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = urlParams.get('date');
    if (dateParam) {
        startReview(dateParam);
    } else if (AUTO_REVIEW_DATE) {
        startReview(AUTO_REVIEW_DATE);
    } else {
        const picker = document.getElementById('dateSelect');
        showIdle(picker ? picker.value : '2026-08-13');
    }
});
</script>

</body>
</html>
"""

def build():
    from build_review_tool import MARKET_DATABASE, NON_TRADING_DAYS
    
    template = get_html_template()
    
    # Replace placeholder JSONs with authentic serialized data
    market_db_json = json.dumps(MARKET_DATABASE, ensure_ascii=False, indent=2)
    non_trading_json = json.dumps(NON_TRADING_DAYS, ensure_ascii=False, indent=2)
    
    html_content = template.replace('__MARKET_DATABASE_JSON__', market_db_json)
    html_content = html_content.replace('__NON_TRADING_DAYS_JSON__', non_trading_json)
    
    target_dates = [
        "2024-03-22",
        "2024-03-25",
        "2024-04-18",
        "2024-09-30",
        "2024-10-08",
        "2026-08-13",
        "2026-08-14",
    ]

    for d in target_dates:
        file_content = html_content.replace("__AUTO_REVIEW_DATE__", json.dumps(d), 1)
        file_content = file_content.replace('value="2026-08-13"', f'value="{d}"', 1)
        file_content = file_content.replace(">2026-08-13</strong>", f">{d}</strong>", 1)
        target_path = os.path.join("/workspace", f"{d}.html")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        print(f"Generated standalone HTML file: {target_path} (Size: {len(file_content)} bytes)")

    index_html = html_content.replace("__AUTO_REVIEW_DATE__", "null", 1)
    with open("/workspace/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Generated default index.html (idle until 开始复盘)")

if __name__ == '__main__':
    build()
