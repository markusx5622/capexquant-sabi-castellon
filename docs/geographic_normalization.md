# Auditable Geographic Normalization

## Objective

Geographic normalization reconciles source municipality labels without losing their original form or hiding review decisions inside program code.

## Core principles

1. Preserve the source label.
2. Create a conservative matching key.
3. Store canonical decisions in a separate reference table.
4. Require explicit review status and rule descriptions.
5. Validate the mapping schema and record preservation.
6. Avoid automatic equivalence assumptions based only on string similarity.

## Original label

`municipality_original` stores the normalized presentation of the raw `municipality` value. Basic text normalization may standardise whitespace and case, but the source category remains traceable.

The original input column is not overwritten.

## Matching key

`municipality_match_key` is used to identify candidate variants. The process:

1. preserves missing values;
2. trims leading and trailing whitespace;
3. collapses repeated whitespace;
4. converts text to uppercase;
5. removes accents for matching;
6. replaces punctuation with spaces;
7. collapses the resulting whitespace.

The match key is a comparison aid. Equal keys do not by themselves prove that two labels represent the same municipality.

## Municipality inventory

The local inventory aggregates raw categories for review and may include:

- company count;
- employee count;
- total revenue;
- total EBITDA;
- adverse-status count.

Because the inventory can contain aggregates derived from licensed data, it belongs under `data/processed/` and remains private.

## Public mapping table

The auditable reference file is:

```text
data/reference/municipality_mapping.csv
```

Required fields are:

| Field | Purpose |
|---|---|
| `municipality_original` | Traceable source label |
| `municipality_match_key` | Conservative comparison key |
| `municipality_canonical` | Reviewed canonical label |
| `review_status` | Review state |
| `normalization_rule` | Reason or transformation rule |
| `notes` | Optional contextual explanation |

The mapping contains labels and rules, not company-level licensed financial data.

## Review status

Supported states include:

- `pending`
- `reviewed`
- `not_applicable`

A generated template begins with identity mappings and `pending` review. A mapping should not be treated as final merely because a canonical column exists.

## Canonical label

`municipality_canonical` is the reviewed label used for consistent aggregation. It should be populated through documented decisions rather than a hidden `.replace()` dictionary.

## Validation controls

The geographic workflow validates:

- required company and municipality fields;
- non-empty input for inventory creation;
- mapping schema completeness;
- uniqueness where required by the applied join contract;
- valid review statuses;
- preservation of company row count;
- preservation of original municipality labels;
- absence of uncontrolled many-to-many joins;
- coverage of the categories intended for canonical analysis.

## Bilingual and compound categories

Labels may contain:

- Spanish and Valencian variants;
- official bilingual forms;
- apostrophes, accents or hyphens;
- compound labels separated by `/`;
- legacy or non-standard place names.

A compound or bilingual source label must not be split or merged automatically without a documented rule. The canonical choice should follow an explicit project convention and retain the original label for auditability.

## Limitations

- String normalization cannot establish legal geographic equivalence.
- Municipality naming can change over time.
- Source categories may be broader or less precise than current official boundaries.
- Manual review can contain judgement and must therefore remain versioned.
- Public synthetic categories demonstrate functionality but do not reproduce the private geographic distribution.
