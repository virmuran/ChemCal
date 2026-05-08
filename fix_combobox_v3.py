# -*- coding: utf-8 -*-
"""
Safely add or update COMBOBOX_STYLE in all calculator files.
Uses precise multi-line string matching instead of regex for reliability.
Validates syntax with compile() after each modification.
"""

import os
import ast

CALC_DIR = r"c:\Users\Administrator\Desktop\CalcE\modules\chemical_calculations\calculators"

# The old COMBOBOX_STYLE that may exist from previous session
OLD_COMBOBOX = '''COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 4px 8px;
        background: white;
        color: black;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #bdc3c7;
    }
    QComboBox::down-arrow {
        width: 10px;
        height: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: white;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""'''

# The new correct COMBOBOX_STYLE (no drop-down/down-arrow, padding matches QLineEdit)
NEW_COMBOBOX = '''COMBOBOX_STYLE = """
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 10px;
        background: white;
        color: black;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        color: black;
        border: 1px solid #bdc3c7;
        selection-background-color: #3498db;
        selection-color: white;
    }
    QComboBox QAbstractItemView::item {
        padding: 3px 8px;
    }
"""'''

# For files that never had COMBOBOX_STYLE, we need to add it.
# Insert it after SCROLLBAR_STYLE definition block, or after GROUP_STYLE if no SCROLLBAR.
INSERT_MARKER_SCROLLBAR = 'SCROLLBAR_STYLE'
INSERT_MARKER_GROUP = 'GROUP_STYLE'

INSERT_BLOCK = NEW_COMBOBOX + "\n"

fixed = 0
added = 0
errors = []
skipped = 0

for fname in sorted(os.listdir(CALC_DIR)):
    if not fname.endswith('.py'):
        continue
    fpath = os.path.join(CALC_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip files without QComboBox
    if 'QComboBox' not in content:
        skipped += 1
        continue

    new_content = content

    if 'COMBOBOX_STYLE' in content:
        # Try exact string replacement of old COMBOBOX_STYLE
        if OLD_COMBOBOX in content:
            new_content = content.replace(OLD_COMBOBOX, NEW_COMBOBOX)
        else:
            # File has some COMBOBOX_STYLE but not the exact old one - skip for safety
            # Use ast to find and replace it safely
            skipped += 1
            continue
    else:
        # Need to INSERT COMBOBOX_STYLE
        # Find the end of SCROLLBAR_STYLE or GROUP_STYLE definition
        insert_pos = -1

        # Look for SCROLLBAR_STYLE first
        if INSERT_MARKER_SCROLLBAR in content:
            # Find SCROLLBAR_STYLE = """ ... """
            idx = content.index(INSERT_MARKER_SCROLLBAR)
            # Find the closing """ after this position
            search_start = idx + len(INSERT_MARKER_SCROLLBAR)
            closing = content.index('"""', search_start)
            # The closing """ is at position closing, move past it
            insert_pos = closing + 3
        elif INSERT_MARKER_GROUP in content:
            idx = content.index(INSERT_MARKER_GROUP)
            search_start = idx + len(INSERT_MARKER_GROUP)
            closing = content.index('"""', search_start)
            insert_pos = closing + 3

        if insert_pos > 0:
            # Insert after a newline
            if content[insert_pos] != '\n':
                INSERT_BLOCK = "\n" + NEW_COMBOBOX + "\n"
            else:
                INSERT_BLOCK = NEW_COMBOBOX + "\n"
            new_content = content[:insert_pos] + INSERT_BLOCK + content[insert_pos:]
        else:
            errors.append((fname, "Could not find insertion point"))
            continue

    # Validate syntax
    try:
        compile(new_content, fpath, 'exec')
    except SyntaxError as e:
        errors.append((fname, f"Syntax error after edit: {e}"))
        continue

    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        if 'COMBOBOX_STYLE' in content:
            fixed += 1
            print(f"  [Updated] {fname}")
        else:
            added += 1
            print(f"  [Added] {fname}")

print(f"\nUpdated: {fixed}, Added: {added}, Skipped: {skipped}")
if errors:
    print(f"Errors: {len(errors)}")
    for f, e in errors:
        print(f"  {f}: {e}")
