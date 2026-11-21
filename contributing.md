# Contribution Guidelines

Contributions are warmly welcome! If you know or maintain a genuinely helpful roadmap, feel free to open a pull request—even if minor formatting details need adjustment, maintainers are happy to help polish them.

## Entry Format

- **Edit `README.md`:** Add your entry to the most relevant category and submit a pull request.
- **Alphabetical order:** Sort entries case-insensitively by link title within each category.
- **Single canonical link:** Include one `https://` link per entry using the project or resource name as the link text, without tracking or referral query parameters (such as `utm_*` or `ref`).
- **Description style:** Separate the link and description with ` - ` (space-dash-space). Start the description with an uppercase letter, end it with a period (`.`), and keep it clear, factual, and non-promotional.
- **Consistent naming:** Use standard technology names (for example, `Node.js` instead of `NodeJS` or `node.js`).

## Badges

Badges are placed at the end of the line after the description period:

1. **Year badge (optional):** Include only when the upstream resource explicitly states a target or last-updated year:
   - `2026+`: `<img alt="Year 2026" src="https://img.shields.io/badge/Year-2026-brightgreen">`
   - `2024–2025`: `<img alt="Year 2025" src="https://img.shields.io/badge/Year-2025-green">`
   - `2021–2023`: `<img alt="Year 2023" src="https://img.shields.io/badge/Year-2023-yellowgreen">`
   - `≤ 2020`: `<img alt="Year 2020" src="https://img.shields.io/badge/Year-2020-yellow">`
2. **Type / status badges:** Indicate the resource format or repository status (`GitHub-Repo` precedes companion `Format-*` badges when both apply):
   - GitHub repository: `<img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-Repo-181717?logo=github">`
   - Website / interactive app: `<img alt="Interactive website" src="https://img.shields.io/badge/Format-Website-0A66C2">` (or `alt="Website"`)
   - Course: `<img alt="Course" src="https://img.shields.io/badge/Format-Course-0A66C2">`
   - Book: `<img alt="Book" src="https://img.shields.io/badge/Format-Book-6F42C1">`
   - PDF: `<img alt="PDF roadmap" src="https://img.shields.io/badge/Format-PDF-B30B00?logo=adobeacrobatreader&logoColor=white">`
   - Blog article: `<img alt="Blog article" src="https://img.shields.io/badge/Blog-Article-0A66C2">`
   - Medium article: `<img alt="Medium article" src="https://img.shields.io/badge/Medium-Article-000000?logo=medium">`
   - Tool: `<img alt="Search tool" src="https://img.shields.io/badge/Type-Tool-0A66C2">`
   - Archived repository: `<img alt="Archived repository" src="https://img.shields.io/badge/Status-Archived-6e7781">`

## Local Validation

You can run the repository check locally with Python 3:

```bash
python3 .github/scripts/validate_readme.py
```

Thanks everyone!
