with open('frontend/lib/live/commands.ts', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'item_responses: notice.items.map(item => ({ item_id: item.id, related_document_id: document?.id ?? item.documentId })),'
replacement = 'item_responses: notice.items.map(item => ({ item_id: item.id, related_document_id: document?.id ?? item.documentId, narrative: text(values.response) || "Compliance correction provided." })),'

if target in c:
    c = c.replace(target, replacement)
    with open('frontend/lib/live/commands.ts', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Updated commands.ts with narrative.")
else:
    print("Target not found")
