# Bases Functions Reference

## Global Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `date()` | `date(string): date` | Parse string to date (`YYYY-MM-DD HH:mm:ss`) |
| `duration()` | `duration(string): duration` | Parse duration string |
| `now()` | `now(): date` | Current date and time |
| `today()` | `today(): date` | Current date (time = 00:00:00) |
| `if()` | `if(condition, trueResult, falseResult?)` | Conditional |
| `min()` | `min(n1, n2, ...): number` | Smallest number |
| `max()` | `max(n1, n2, ...): number` | Largest number |
| `number()` | `number(any): number` | Convert to number |
| `link()` | `link(path, display?): Link` | Create a link |
| `list()` | `list(element): List` | Wrap in list if not already |
| `file()` | `file(path): file` | Get file object |
| `image()` | `image(path): image` | Create image for rendering |
| `icon()` | `icon(name): icon` | Lucide icon by name |
| `html()` | `html(string): html` | Render as HTML |

## Date Functions & Fields

**Fields:** `date.year`, `date.month`, `date.day`, `date.hour`, `date.minute`, `date.second`

| Function | Description |
|----------|-------------|
| `date.format(string)` | Format with Moment.js pattern |
| `date.time()` | Get time as string |
| `date.relative()` | Human-readable relative time |

## Duration Type

Subtracting two dates returns a **Duration** — not a number. Access a field first.

**Fields:** `duration.days`, `duration.hours`, `duration.minutes`, `duration.seconds`, `duration.milliseconds`

```yaml
# CORRECT
"(date(due_date) - today()).days"
"(now() - file.ctime).days.round(0)"

# WRONG — Duration doesn't support .round() directly
"(now() - file.ctime).round(0)"
```

## Date Arithmetic

```yaml
# Duration units: y/year, M/month, d/day, w/week, h/hour, m/minute, s/second
"now() + \"1 day\""
"today() + \"7d\""
"(now() - file.ctime).days"
```

## String Functions

**Field:** `string.length`

| Function | Description |
|----------|-------------|
| `contains(value)` | Check substring |
| `startsWith(query)` | Starts with |
| `endsWith(query)` | Ends with |
| `isEmpty()` | Empty or not present |
| `lower()` | Lowercase |
| `title()` | Title Case |
| `trim()` | Remove whitespace |
| `replace(pattern, replacement)` | Replace |
| `slice(start, end?)` | Substring |
| `split(separator, n?)` | Split to list |

## Number Functions

| Function | Description |
|----------|-------------|
| `abs()` | Absolute value |
| `ceil()` | Round up |
| `floor()` | Round down |
| `round(digits?)` | Round |
| `toFixed(precision)` | Fixed-point string |

## List Functions

**Field:** `list.length`

| Function | Description |
|----------|-------------|
| `contains(value)` | Element exists |
| `filter(expression)` | Filter (uses `value`, `index`) |
| `map(expression)` | Transform (uses `value`, `index`) |
| `join(separator)` | Join to string |
| `sort()` | Sort ascending |
| `unique()` | Remove duplicates |
| `flat()` | Flatten nested |
| `slice(start, end?)` | Sublist |

## File Functions

| Function | Description |
|----------|-------------|
| `asLink(display?)` | Convert to link |
| `hasLink(otherFile)` | Has link to file |
| `hasTag(...tags)` | Has any of the tags |
| `hasProperty(name)` | Has property |
| `inFolder(folder)` | In folder or subfolder |

## Link Functions

| Function | Description |
|----------|-------------|
| `asFile()` | Get file object |
| `linksTo(file)` | Links to file |

## Object Functions

| Function | Description |
|----------|-------------|
| `keys()` | List of keys |
| `values()` | List of values |
| `isEmpty()` | No properties |

## RegExp Functions

| Function | Description |
|----------|-------------|
| `matches(string)` | Test if matches |
