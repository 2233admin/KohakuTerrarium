---
name: tree
description: List directory structure as a tree
category: builtin
tags: [file, directory, navigation]
---

# tree

Display directory structure as a visual tree.

## WHEN TO USE

- Exploring project structure
- Understanding folder organization
- Finding files before reading them
- Getting overview of a directory

## WHEN NOT TO USE

- Searching file contents (use grep)
- Finding files by pattern (use glob)
- Reading file contents (use read)

## HOW TO USE

```xml
<tree>path/to/directory</tree>
```

## Arguments

| Arg | Type | Description |
|-----|------|-------------|
| path | body | Directory path to list (required) |
| max_depth | attribute | Maximum depth to traverse (optional) |

## Examples

```xml
<!-- List current directory -->
<tree>.</tree>

<!-- List specific folder -->
<tree>src/kohakuterrarium</tree>

<!-- List with depth limit -->
<tree max_depth="2">.</tree>

<!-- List memory folder -->
<tree>./memory</tree>
```

## Output Format

```
./memory
├── character.md
├── context.md
├── facts.md
├── preferences.md
└── rules.md
```

## LIMITATIONS

- Large directories may be truncated
- Hidden files may be included/excluded based on config
- Symbolic links handled per platform

## TIPS

- Use before `read` to discover file paths
- Combine with `glob` for pattern matching
- Use `max_depth` for large directories
