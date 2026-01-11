---
name: memory_read
description: Retrieve information from memory system
category: subagent
tags: [memory, retrieval, context]
---

# memory_read

Sub-agent for searching and retrieving information from the memory folder.

## WHEN TO USE

- Need to recall stored information (facts, preferences, context)
- Looking up character/agent definition
- Retrieving past conversation context
- Finding specific stored data

## WHEN NOT TO USE

- Reading arbitrary files outside memory
- Storing new information (use memory_write)
- Simple file read when you know exact path

## HOW TO USE

```xml
<agent type="memory_read">what to find</agent>
```

## Arguments

| Arg | Type | Description |
|-----|------|-------------|
| type | attribute | Must be "memory_read" |
| body | content | What information to retrieve |

## Examples

```xml
<!-- Find character definition -->
<agent type="memory_read">Get my character definition</agent>

<!-- Recall user preferences -->
<agent type="memory_read">What are the user's preferences?</agent>

<!-- Find specific fact -->
<agent type="memory_read">What do I know about the project structure?</agent>

<!-- Get conversation context -->
<agent type="memory_read">Recent conversation topics</agent>
```

## CAPABILITIES

The memory_read sub-agent has access to:
- `tree` - List files in memory folder
- `read` - Read file contents
- `grep` - Search within files

It will:
1. List available memory files
2. Search for relevant content
3. Return found information

## OUTPUT

Returns the relevant information found in memory, formatted for use.

## LIMITATIONS

- Read-only (cannot modify memory)
- Only searches configured memory path
- May not find information if not stored
