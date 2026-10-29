with open('frontend/lib/live/commands.ts', 'r', encoding='utf-8') as f:
    c = f.read()

target = """        const workflows = await client.get<Envelope>("/workflows");
        const workflow = workflows.data.find(w => String(w.id) === text(values.workflowId));
        if (!workflow) throw new Error("The selected live workflow is unavailable. Refresh before creating a draft.");"""

replacement = """        const workflows = await client.get<Envelope>("/workflows");
        const workflow = workflows.data.find(w => String(w.id) === text(values.workflowId)) ?? workflows.data[0];
        if (!workflow) throw new Error("The selected live workflow is unavailable. Refresh before creating a draft.");"""

target_crlf = target.replace('\n', '\r\n')
replacement_crlf = replacement.replace('\n', '\r\n')

if target in c:
    c = c.replace(target, replacement)
    with open('frontend/lib/live/commands.ts', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Updated commands.ts (LF)")
elif target_crlf in c:
    c = c.replace(target_crlf, replacement_crlf)
    with open('frontend/lib/live/commands.ts', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Updated commands.ts (CRLF)")
else:
    print("Target not found!")

