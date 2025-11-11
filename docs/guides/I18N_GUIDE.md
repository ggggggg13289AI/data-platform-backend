# Internationalization (I18n) Guide

**Medical Imaging Data Platform**
**Version**: 1.0
**Last Updated**: 2025-11-10
**Target Audience**: Documentation maintainers, translators, developers

---

## 📚 Table of Contents

1. [Overview](#overview)
2. [Documentation Structure](#documentation-structure)
3. [Current Language Support](#current-language-support)
4. [Adding a New Language](#adding-a-new-language)
5. [Translation Guidelines](#translation-guidelines)
6. [Maintenance Best Practices](#maintenance-best-practices)
7. [File Naming Conventions](#file-naming-conventions)
8. [Quality Assurance](#quality-assurance)
9. [Tools and Resources](#tools-and-resources)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose
This guide explains how to add, maintain, and manage multilingual documentation for the Medical Imaging Data Platform. Our i18n strategy ensures that documentation is accessible to users in their native language while maintaining consistency and technical accuracy.

### Design Philosophy
- **User-Centric**: Default language matches primary user demographic (Traditional Chinese for Taiwan)
- **Scalable**: Easy to add new languages without restructuring
- **Maintainable**: Each language version independently editable
- **Standard**: Follows industry conventions (ISO locale codes, separate files)

### Current Implementation
```
image_data_platform/
├── README.md                     # Brief overview + language selector (Traditional Chinese)
└── docs/
    ├── README.zh-TW.md          # Complete Traditional Chinese documentation (default)
    ├── README.en.md             # Complete English documentation
    └── guides/
        └── I18N_GUIDE.md        # This guide
```

---

## Documentation Structure

### Main README (Root)
**File**: `README.md`
**Length**: ~100-150 lines
**Language**: Traditional Chinese (預設語言)
**Purpose**: Brief project overview with language selector

**Content Requirements**:
- Language selector at top (prominently displayed)
- Brief project description (2-3 paragraphs)
- Key features summary (bullet points)
- Quick start links
- Link to complete documentation in each language

**Example Structure**:
```markdown
# 專案名稱

## 📚 Language / 語言
[Language selector with flags/links]

## 簡介
[2-3 paragraphs overview]

## 主要功能
- Feature 1
- Feature 2
- Feature 3

## 快速開始
→ 完整文檔：[繁體中文](./docs/README.zh-TW.md) | [English](./docs/README.en.md)
```

### Language-Specific Documentation
**Location**: `docs/README.{locale}.md`
**Length**: Complete documentation (typically 400-600 lines)
**Purpose**: Full project documentation in specific language

**Content Requirements**:
- Complete project overview
- Architecture description
- Technology stack details
- Setup instructions
- API documentation
- Development guidelines
- Deployment information
- Troubleshooting guide
- Contributing guidelines

---

## Current Language Support

### Supported Languages

#### 1. Traditional Chinese (繁體中文)
- **Locale Code**: `zh-TW`
- **File**: `docs/README.zh-TW.md`
- **Status**: ✅ Complete (550 lines)
- **Default**: Yes
- **Target Audience**: Taiwan users, medical professionals in Taiwan
- **Characteristics**:
  - Uses Traditional Chinese characters (正體字)
  - Medical terminology follows Taiwan standards
  - Professional and formal tone
  - Technical terms in English where appropriate

#### 2. English
- **Locale Code**: `en`
- **File**: `docs/README.en.md`
- **Status**: ✅ Complete (550 lines)
- **Default**: No
- **Target Audience**: International developers, English-speaking medical professionals
- **Characteristics**:
  - Clear, technical writing style
  - American English spelling conventions
  - Technical documentation standards
  - Accessible to non-native speakers

#### 3. Simplified Chinese (简体中文) - Reference
- **Locale Code**: `zh-CN`
- **File**: `docs/README.md.bak` (archived original)
- **Status**: ⚠️ Archived (not actively maintained)
- **Purpose**: Reference for original content
- **Note**: Not linked in language selector

---

## Adding a New Language

### Step-by-Step Process

#### Step 1: Choose Locale Code
Use ISO 639-1 (language) + ISO 3166-1 (country) format:
- Japanese: `ja` or `ja-JP`
- Korean: `ko` or `ko-KR`
- German: `de` or `de-DE`
- French: `fr` or `fr-FR`
- Spanish: `es` or `es-ES`

**Recommended Format**: `{language}-{COUNTRY}` when region matters (e.g., `zh-TW` vs `zh-CN`)

#### Step 2: Create Documentation File
```bash
# Copy the English version as a template
cp docs/README.en.md docs/README.{locale}.md

# Example: Adding Japanese
cp docs/README.en.md docs/README.ja-JP.md
```

#### Step 3: Translate Content
Translate the entire document following [Translation Guidelines](#translation-guidelines) below.

**Translation Checklist**:
- [ ] Headers and section titles
- [ ] Body paragraphs and descriptions
- [ ] UI element descriptions
- [ ] Error messages and warnings
- [ ] Comments in code examples (if any)
- [ ] Alt text for images
- [ ] Links text (URLs stay the same)
- [ ] Table contents

**Preserve Unchanged**:
- [ ] Code snippets and syntax
- [ ] Command examples
- [ ] File paths
- [ ] URLs and links
- [ ] Technical terms (API, REST, JSON, etc.)
- [ ] Framework names (React, Django, FastAPI)
- [ ] Library names
- [ ] Function/variable names in code

#### Step 4: Update Language Selector
Edit the main `README.md` to add the new language option:

```markdown
## 📚 Language / 語言

- **[繁体中文 (Traditional Chinese)](./docs/README.zh-TW.md)** ← Default / 預設版本
- **[English](./docs/README.en.md)**
- **[日本語 (Japanese)](./docs/README.ja-JP.md)** ← NEW
```

**Language Selector Format**:
```markdown
- **[Native Name (English Name)](./docs/README.{locale}.md)**
```

Examples:
- `[繁体中文 (Traditional Chinese)](./docs/README.zh-TW.md)`
- `[English](./docs/README.en.md)`
- `[日本語 (Japanese)](./docs/README.ja-JP.md)`
- `[한국어 (Korean)](./docs/README.ko-KR.md)`
- `[Deutsch (German)](./docs/README.de-DE.md)`

#### Step 5: Quality Assurance
Run through the [Quality Assurance](#quality-assurance) checklist below.

#### Step 6: Git Commit
```bash
git add README.md docs/README.{locale}.md
git commit -m "docs: Add {language} translation

- Create docs/README.{locale}.md ({language} documentation)
- Update language selector in main README.md
- Ensure content parity with existing translations

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Translation Guidelines

### General Principles

#### 1. Content Parity
**Rule**: All language versions must contain identical technical information.

**What This Means**:
- Same features described
- Same setup steps included
- Same API endpoints documented
- Same architecture diagrams referenced
- Same examples provided

**Acceptable Differences**:
- Cultural context examples
- Region-specific installation notes
- Local terminology preferences

#### 2. Technical Accuracy
**Rule**: Technical terms must be consistent and correct.

**Medical Terminology**:
- Use established medical dictionaries for the target language
- For Taiwan (zh-TW): Follow Taiwan medical standards (醫療術語)
- For mainland China (zh-CN): Follow PRC medical standards
- When uncertain, provide both native term and English in parentheses

**IT Terminology**:
- Keep common technical terms in English: API, REST, JSON, HTTP, SQL
- Translate when natural translation exists: database → 資料庫/数据库
- Use target language conventions: "click" → "點擊" (zh-TW) / "点击" (zh-CN)

#### 3. Tone and Style
**Professional Tone**:
- Formal but accessible
- Clear and direct
- Technical but not overly complex
- Respectful of user's expertise

**Consistency**:
- Use same terminology throughout document
- Maintain parallel structure in lists
- Keep section organization identical across languages

#### 4. Code and Examples
**Always Preserve**:
- Code syntax (Python, JavaScript, SQL, etc.)
- Variable names (unless they're in natural language)
- Function names and API endpoints
- File paths and directory structure
- Command-line examples
- JSON/YAML structure

**Translate Only**:
- Comments in code (with cultural sensitivity)
- String literals that represent UI text
- Error messages that users will see
- Log messages visible to users

**Example**:
```python
# ENGLISH
# Fetch all medical studies from database
studies = db.query(Study).filter(Study.status == "active").all()

# TRADITIONAL CHINESE
# 從資料庫獲取所有醫療研究記錄
studies = db.query(Study).filter(Study.status == "active").all()

# Code stays identical, only comment translated
```

### Language-Specific Considerations

#### Traditional Chinese (zh-TW)
**Character Set**: Traditional Chinese characters (正體字)
**Terminology Source**: Taiwan medical and IT standards
**Key Terms**:
- 數據 (data) not 数据
- 資料庫 (database) not 数据库
- 檢索 (search/retrieve) not 检索
- 醫療 (medical) not 医疗

**Punctuation**:
- Use full-width punctuation: 「」『』（）
- Proper use of 、 (enumeration comma)
- 。 (full stop) at sentence end

**Style**:
- Formal written Chinese
- Appropriate use of 的/得/地
- Professional medical terminology

#### English
**Variant**: American English (for consistency)
**Spelling**: -ize not -ise, color not colour, center not centre
**Style**: Technical documentation standards (Microsoft/Google style)
**Tone**: Professional but approachable
**Sentence Structure**: Clear and concise, active voice preferred

**Common Patterns**:
- Use bullet points for lists
- Use numbered lists for sequential steps
- Short paragraphs (3-5 sentences)
- Subheadings for scanability

#### Japanese (ja-JP)
**Script**: Hiragana, Katakana, Kanji mix
**Loanwords**: Use katakana for English technical terms
**Politeness Level**: です・ます form (polite formal)
**Medical Terms**: Japanese medical kanji + romaji in parentheses if needed

#### Korean (ko-KR)
**Script**: Hangul (한글)
**Loanwords**: Use Hangul phonetic spelling for English terms
**Formality**: Formal polite form (합니다 style)
**Medical Terms**: Korean medical terminology with Hanja in parentheses if needed

---

## Maintenance Best Practices

### Version Synchronization

#### When to Update All Languages
1. **Architecture changes**: Framework switches, major refactoring
2. **New features**: Significant functionality additions
3. **API changes**: Endpoint modifications, parameter changes
4. **Setup changes**: Installation process updates
5. **Security updates**: Important security notices
6. **Deprecated features**: Feature removals or deprecations

#### How to Keep in Sync
1. **Edit all versions together** when making structural changes
2. **Use Git diffs** to identify what needs translation
3. **Track version numbers** in each file header
4. **Document changes** in commit messages

**Example Workflow**:
```bash
# 1. Make change to English version
vim docs/README.en.md

# 2. Identify changed lines
git diff docs/README.en.md

# 3. Apply equivalent changes to other languages
vim docs/README.zh-TW.md
vim docs/README.ja-JP.md

# 4. Commit all together
git add docs/README.*.md
git commit -m "docs: Update API endpoint documentation across all languages"
```

### Update Frequency

**Immediate Updates**:
- Breaking changes
- Security vulnerabilities
- Critical bug fixes
- Incorrect information

**Batched Updates** (weekly/monthly):
- Typo corrections
- Style improvements
- Minor clarifications
- Additional examples

### Translation Review Process

1. **Self-Review**: Translator reviews own work
2. **Technical Review**: Developer verifies technical accuracy
3. **Language Review**: Native speaker reviews language quality
4. **User Testing**: Sample users verify clarity

**Checklist**:
- [ ] Content parity with source language
- [ ] Technical terms accurate
- [ ] Grammar and spelling correct
- [ ] Formatting consistent
- [ ] Links working
- [ ] Code examples functional
- [ ] Cultural sensitivity appropriate

---

## File Naming Conventions

### README Files
**Pattern**: `README.{locale}.md`

**Examples**:
- `README.zh-TW.md` (Traditional Chinese, Taiwan)
- `README.en.md` or `README.en-US.md` (English, USA)
- `README.ja-JP.md` (Japanese, Japan)
- `README.ko-KR.md` (Korean, South Korea)
- `README.de-DE.md` (German, Germany)
- `README.fr-FR.md` (French, France)

### Other Documentation
For non-README documentation, use suffix pattern:

**Pattern**: `{document-name}.{locale}.md`

**Examples**:
- `API_GUIDE.zh-TW.md`
- `API_GUIDE.en.md`
- `SETUP_INSTRUCTIONS.ja-JP.md`

### Directory Structure
```
docs/
├── README.zh-TW.md           # Complete Traditional Chinese README
├── README.en.md              # Complete English README
├── README.ja-JP.md           # Complete Japanese README
├── guides/
│   ├── I18N_GUIDE.md         # This guide (English default)
│   ├── SETUP_GUIDE.zh-TW.md  # Setup guide in Traditional Chinese
│   └── SETUP_GUIDE.en.md     # Setup guide in English
└── api/
    ├── API_CONTRACT.md       # API documentation (English default)
    └── API_CONTRACT.zh-TW.md # API documentation in Traditional Chinese
```

---

## Quality Assurance

### Pre-Commit Checklist

#### Content Quality
- [ ] All sections translated (no placeholders like "TODO" or "TBD")
- [ ] Technical information identical to source
- [ ] Code examples work and are properly formatted
- [ ] Commands tested and functional
- [ ] Links resolve correctly (relative paths)

#### Language Quality
- [ ] Grammar correct for target language
- [ ] Spelling verified (use spellchecker)
- [ ] Terminology consistent throughout
- [ ] Tone appropriate (professional, formal)
- [ ] Cultural sensitivity maintained

#### Format Quality
- [ ] Markdown syntax correct (headers, lists, code blocks)
- [ ] Consistent use of formatting (bold, italic, code)
- [ ] Tables formatted properly
- [ ] Images display correctly
- [ ] Line breaks appropriate

#### Technical Quality
- [ ] File encoding UTF-8 (supports all characters)
- [ ] No broken internal links
- [ ] No broken external links
- [ ] Code syntax highlighting works
- [ ] Special characters render correctly

### Validation Tools

#### Markdown Linting
```bash
# Install markdownlint
npm install -g markdownlint-cli

# Check documentation
markdownlint docs/README.*.md
```

#### Link Checking
```bash
# Install markdown-link-check
npm install -g markdown-link-check

# Verify all links
markdown-link-check docs/README.en.md
markdown-link-check docs/README.zh-TW.md
```

#### Encoding Verification
```bash
# Check file encoding (should be UTF-8)
file -i docs/README.*.md
```

#### Diff Comparison
```bash
# Compare structure between versions
diff -y --suppress-common-lines \
  <(grep "^##" docs/README.en.md) \
  <(grep "^##" docs/README.zh-TW.md)

# Should show identical section structure
```

---

## Tools and Resources

### Translation Tools

#### Machine Translation (Starting Point Only)
- **Google Translate**: https://translate.google.com
- **DeepL**: https://www.deepl.com (good for European languages)
- **Microsoft Translator**: https://www.microsoft.com/translator

⚠️ **Warning**: Machine translation is only a starting point. Always review and edit by native speaker.

#### Professional Tools
- **SDL Trados**: Professional CAT tool
- **MemoQ**: Translation memory system
- **Lokalise**: Collaborative translation platform
- **Crowdin**: Continuous localization platform

### Terminology Resources

#### Medical Terminology
- **Taiwan**: 國家教育研究院雙語詞彙 (Taiwan Medical Terms Database)
- **Japan**: 日本医学会医学用語辞典 (Japanese Medical Dictionary)
- **International**: MeSH (Medical Subject Headings)

#### IT Terminology
- **Microsoft Terminology**: https://www.microsoft.com/language
- **Apple Style Guide**: https://help.apple.com/applestyleguide/
- **Google Developer Documentation Style Guide**

### Markdown Editors
- **VS Code** with Markdown extensions
- **Typora**: WYSIWYG Markdown editor
- **MarkText**: Open-source Markdown editor
- **Obsidian**: Note-taking with Markdown

### Collaboration Tools
- **Git**: Version control for documentation
- **GitHub**: Code review and collaboration
- **Pull Requests**: For translation review process

---

## Troubleshooting

### Common Issues

#### Issue 1: Encoding Problems
**Symptom**: Chinese characters display as `???` or weird symbols

**Solution**:
```bash
# Ensure file is UTF-8
iconv -f ISO-8859-1 -t UTF-8 docs/README.zh-TW.md > docs/README.zh-TW.md.utf8
mv docs/README.zh-TW.md.utf8 docs/README.zh-TW.md

# Verify encoding
file -i docs/README.zh-TW.md
# Should show: charset=utf-8
```

#### Issue 2: Broken Links
**Symptom**: Links don't work after moving files

**Solution**:
- Use relative paths: `./docs/README.en.md` not `/docs/README.en.md`
- Check capitalization (case-sensitive on Linux/macOS)
- Verify file actually exists
- Use `markdown-link-check` tool

#### Issue 3: Inconsistent Formatting
**Symptom**: Different formatting across language versions

**Solution**:
1. Establish style guide for each language
2. Use linting tools (markdownlint)
3. Create templates for common sections
4. Automate formatting with Prettier

#### Issue 4: Missing Translations
**Symptom**: Some sections still in original language

**Solution**:
```bash
# Find English text in Chinese file (basic detection)
grep -E '[A-Za-z]{10,}' docs/README.zh-TW.md | grep -v '```' | grep -v 'http'

# Review each match to determine if it should be translated
```

#### Issue 5: Outdated Translations
**Symptom**: English version updated but other languages haven't changed

**Solution**:
1. Use Git to track changes:
```bash
git log --oneline docs/README.en.md
# Check if zh-TW updated at same time
git log --oneline docs/README.zh-TW.md
```

2. Compare file modification dates:
```bash
ls -lt docs/README.*.md
```

3. Set up monitoring or CI checks for version sync

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-10 | Initial I18n guide creation |

---

## Related Documentation

- [Documentation Index](../DOCUMENTATION_INDEX.md) - Complete documentation inventory
- [Session Report](../../claudedocs/SESSION_MULTILINGUAL_README_REPORT.md) - Implementation details
- [Project Overview](../01_PROJECT_OVERVIEW.md) - Technical architecture

---

## Contributing

If you'd like to contribute translations or improve this guide:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-japanese-translation`
3. Follow this guide to add your translation
4. Submit a Pull Request with clear description
5. Participate in review process

**Quality Standards**: All contributions must meet the quality checklist above.

---

**Guide Created**: 2025-11-10
**Maintained By**: Documentation Team
**Contact**: See main README for project contacts
**License**: Same as project license
