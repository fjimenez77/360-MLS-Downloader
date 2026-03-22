# Contributing to 360 MLS Downloader

Thanks for your interest in contributing! Here's how to get started.

---

## How to Contribute

### 1. Fork the Repository

Click the **Fork** button at the top-right of the [repo page](https://github.com/fjimenez77/360-MLS-Downloader) to create your own copy.

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR-USERNAME/360-MLS-Downloader.git
cd 360-MLS-Downloader
```

### 3. Create a Branch

Always work on a new branch — never commit directly to `main`.

```bash
git checkout -b my-feature-name
```

Use a descriptive branch name like `fix-download-retry`, `add-batch-mode`, etc.

### 4. Make Your Changes

- Install dependencies: `pip install requests`
- Test your changes against a real tour URL before submitting
- Follow the existing code style (no linting config — just match what's there)

### 5. Commit Your Changes

```bash
git add .
git commit -m "Brief description of what you changed"
```

Write clear commit messages that explain **what** and **why**, not just **how**.

### 6. Push to Your Fork

```bash
git push origin my-feature-name
```

### 7. Open a Pull Request

- Go to your fork on GitHub
- Click **"Compare & pull request"**
- Describe what your PR does and why
- Reference any related issues if applicable

---

## What We're Looking For

Good contributions include:

- **Bug fixes** — something broken? Fix it and include steps to reproduce
- **New features** — new download options, viewer improvements, platform support
- **Documentation** — better instructions, examples, or typo fixes
- **Compatibility** — Windows support improvements, Python version fixes

---

## Guidelines

- **Test before submitting** — make sure the menu and CLI both work
- **Keep it simple** — match the existing code style, don't over-engineer
- **One PR per change** — don't bundle unrelated changes together
- **No breaking changes** — existing CLI flags and menu options should keep working
- **No dependencies** — the only external dependency is `requests`. Keep it that way unless absolutely necessary

---

## Project Structure

| File | Purpose |
|------|---------|
| `mls360_downloader_core.py` | Shared engine — all download logic lives here |
| `mls360-downloader.py` | CLI interface (imports from core) |
| `mls360-menu.py` | Interactive menu interface (imports from core) |
| `mls360_viewer.py` | 360° HTML viewer generator |
| `vendor/` | Vendored Pannellum library (don't modify) |

---

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/fjimenez77/360-MLS-Downloader/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce (include the tour URL if possible)
- Your OS and Python version

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
