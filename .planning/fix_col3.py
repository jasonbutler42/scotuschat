"""Replace Column 3 action buttons with HIT/MISS-aware button logic in +page.svelte."""

import sys

FILE = 'C:/workspace/scotuschat/project/app/src/routes/admin/pipeline/[job_id]/+page.svelte'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

T = '\t'

# The old Column 3 block — from the disposition check through the closing {/if}
old_parts = [
    T*11 + '{#if s?.disposition !== null && s?.disposition !== undefined}\n',
    T*12 + '<!-- Row is dispositioned — show Override button to reopen correction flow -->\n',
    T*12 + '<button\n',
    T*13 + 'type="button"\n',
    T*13 + 'onclick={() => {\n',
    T*14 + 'const st = rowStates[rowKey];\n',
    T*14 + 'if (!st) return;\n',
    T*14 + 'st.disposition = null;\n',
    T*14 + 'st.person_id = null;\n',
    T*14 + 'st.correcting = false;\n',
    T*14 + 'st.addingPerson = false;\n',
    T*13 + '}}\n',
    T*13 + 'style="\n',
    T*14 + 'font-size: 14px;\n',
    T*14 + 'font-weight: 400;\n',
    T*14 + 'color: #94a3b8;\n',
    T*14 + 'background: transparent;\n',
    T*14 + 'border: 1px solid #334155;\n',
    T*14 + 'border-radius: 4px;\n',
    T*14 + 'padding: 6px 12px;\n',
    T*14 + 'cursor: pointer;\n',
    T*14 + 'min-height: 32px;\n',
    T*13 + '"\n',
    T*12 + '>\n',
    T*13 + 'Override\n',
    T*12 + '</button>\n',
    T*11 + '{:else}\n',
    T*12 + '<div style="display: flex; gap: 8px; flex-wrap: wrap;">\n',
    T*13 + '{#if row.auto_match_id}\n',
    T*14 + '<button\n',
    T*15 + 'type="button"\n',
    T*15 + 'onclick={() => handleConfirm(rowKey, row)}\n',
    T*15 + 'style="\n',
    T*16 + 'font-size: 14px;\n',
    T*16 + 'font-weight: 400;\n',
    T*16 + 'color: #e2e8f0;\n',
    T*16 + 'background: transparent;\n',
    T*16 + 'border: 1px solid #334155;\n',
    T*16 + 'border-radius: 4px;\n',
    T*16 + 'padding: 6px 12px;\n',
    T*16 + 'cursor: pointer;\n',
    T*16 + 'min-height: 32px;\n',
    T*15 + '"\n',
    T*14 + '>\n',
    T*15 + 'Confirm\n',
    T*14 + '</button>\n',
    T*13 + '{/if}\n',
    T*13 + '<button\n',
    T*14 + 'type="button"\n',
    T*14 + 'onclick={() => handleCorrect(rowKey)}\n',
    T*14 + 'style="\n',
    T*15 + 'font-size: 14px;\n',
    T*15 + 'font-weight: 400;\n',
    T*15 + 'color: #e2e8f0;\n',
    T*15 + 'background: transparent;\n',
    T*15 + 'border: 1px solid #334155;\n',
    T*15 + 'border-radius: 4px;\n',
    T*15 + 'padding: 6px 12px;\n',
    T*15 + 'cursor: pointer;\n',
    T*15 + 'min-height: 32px;\n',
    T*14 + '"\n',
    T*13 + '>\n',
    T*14 + 'Correct\n',
    T*13 + '</button>\n',
    T*12 + '</div>\n',
    T*11 + '{/if}\n',
]

old = ''.join(old_parts)

# New Column 3 block:
# - HIT rows (auto_resolved === true) with disposition != null: show single "Change" button
# - HIT rows with disposition === null: cannot happen (inited as confirmed), but handle gracefully
# - MISS rows with disposition != null: show Override button
# - MISS rows with disposition === null: show Correct button (Confirm only if auto_match_id)
new_parts = [
    T*11 + '{#if row.auto_resolved === true}\n',
    T*12 + '<!-- HIT row: single Change button — operator clicks to re-pick from full roster ([07-07] Gap 1a) -->\n',
    T*12 + '<button\n',
    T*13 + 'type="button"\n',
    T*13 + 'onclick={() => handleCorrect(rowKey)}\n',
    T*13 + 'style="\n',
    T*14 + 'font-size: 14px;\n',
    T*14 + 'font-weight: 400;\n',
    T*14 + 'color: #e2e8f0;\n',
    T*14 + 'background: transparent;\n',
    T*14 + 'border: 1px solid #334155;\n',
    T*14 + 'border-radius: 4px;\n',
    T*14 + 'padding: 6px 12px;\n',
    T*14 + 'cursor: pointer;\n',
    T*14 + 'min-height: 32px;\n',
    T*13 + '"\n',
    T*12 + '>\n',
    T*13 + 'Change\n',
    T*12 + '</button>\n',
    T*11 + '{:else if s?.disposition !== null && s?.disposition !== undefined}\n',
    T*12 + '<!-- MISS row is dispositioned — Override reopens correction flow -->\n',
    T*12 + '<button\n',
    T*13 + 'type="button"\n',
    T*13 + 'onclick={() => {\n',
    T*14 + 'const st = rowStates[rowKey];\n',
    T*14 + 'if (!st) return;\n',
    T*14 + 'st.disposition = null;\n',
    T*14 + 'st.person_id = null;\n',
    T*14 + 'st.correcting = false;\n',
    T*14 + 'st.addingPerson = false;\n',
    T*13 + '}}\n',
    T*13 + 'style="\n',
    T*14 + 'font-size: 14px;\n',
    T*14 + 'font-weight: 400;\n',
    T*14 + 'color: #94a3b8;\n',
    T*14 + 'background: transparent;\n',
    T*14 + 'border: 1px solid #334155;\n',
    T*14 + 'border-radius: 4px;\n',
    T*14 + 'padding: 6px 12px;\n',
    T*14 + 'cursor: pointer;\n',
    T*14 + 'min-height: 32px;\n',
    T*13 + '"\n',
    T*12 + '>\n',
    T*13 + 'Override\n',
    T*12 + '</button>\n',
    T*11 + '{:else}\n',
    T*12 + '<!-- MISS row not yet dispositioned — Confirm (if auto_match_id) + Correct -->\n',
    T*12 + '<div style="display: flex; gap: 8px; flex-wrap: wrap;">\n',
    T*13 + '{#if row.auto_match_id}\n',
    T*14 + '<button\n',
    T*15 + 'type="button"\n',
    T*15 + 'onclick={() => handleConfirm(rowKey, row)}\n',
    T*15 + 'style="\n',
    T*16 + 'font-size: 14px;\n',
    T*16 + 'font-weight: 400;\n',
    T*16 + 'color: #e2e8f0;\n',
    T*16 + 'background: transparent;\n',
    T*16 + 'border: 1px solid #334155;\n',
    T*16 + 'border-radius: 4px;\n',
    T*16 + 'padding: 6px 12px;\n',
    T*16 + 'cursor: pointer;\n',
    T*16 + 'min-height: 32px;\n',
    T*15 + '"\n',
    T*14 + '>\n',
    T*15 + 'Confirm\n',
    T*14 + '</button>\n',
    T*13 + '{/if}\n',
    T*13 + '<button\n',
    T*14 + 'type="button"\n',
    T*14 + 'onclick={() => handleCorrect(rowKey)}\n',
    T*14 + 'style="\n',
    T*15 + 'font-size: 14px;\n',
    T*15 + 'font-weight: 400;\n',
    T*15 + 'color: #e2e8f0;\n',
    T*15 + 'background: transparent;\n',
    T*15 + 'border: 1px solid #334155;\n',
    T*15 + 'border-radius: 4px;\n',
    T*15 + 'padding: 6px 12px;\n',
    T*15 + 'cursor: pointer;\n',
    T*15 + 'min-height: 32px;\n',
    T*14 + '"\n',
    T*13 + '>\n',
    T*14 + 'Correct\n',
    T*13 + '</button>\n',
    T*12 + '</div>\n',
    T*11 + '{/if}\n',
]

new = ''.join(new_parts)

if old not in content:
    print("ERROR: old string not found in file")
    # Find first mismatch
    for i in range(1, len(old)+1):
        if content.find(old[:i]) == -1:
            print(f"Mismatch at character {i-1}: {repr(old[max(0,i-30):i+10])}")
            break
    sys.exit(1)

new_content = content.replace(old, new, 1)
assert new_content != content

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("SUCCESS: Column 3 replaced with HIT/MISS-aware button logic")
