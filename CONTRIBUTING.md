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

## Scope

Before writing any code that touches the Zillow provider, browser automation, or the CAPTCHA flow, read the **"Design Principles"** section in the README. The human-in-the-loop CAPTCHA step is load-bearing for this project's legal posture and is not up for negotiation — PRs that remove it will be closed. This applies whether the change is framed as performance, UX, automation, "optional," or behind a flag.

PRs that add network egress to third-party services (proxy providers, CAPTCHA-solver APIs, telemetry) will also be closed without review.

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
- **Review the "Design Principles" section** in the README — PRs that remove the human-in-the-loop CAPTCHA step will be closed without review

---

## Project Structure

| File | Purpose |
|------|---------|
| `mls360_downloader_core.py` | Shared engine — provider-agnostic download logic |
| `mls360-downloader.py` | CLI interface (imports from core) |
| `mls360-menu.py` | Interactive menu interface (imports from core) |
| `mls360_viewer.py` | 360° HTML viewer generator |
| `providers/__init__.py` | Provider registry and auto-detection |
| `providers/zillow.py` | Zillow 3D Home + listing data provider |
| `providers/ricoh360.py` | Ricoh360 MLS tour provider |
| `vendor/` | Vendored Pannellum library (don't modify) |

### Adding a New Provider

To add support for a new platform, create `providers/your_provider.py` with:
- `PROVIDER_NAME` and `DISPLAY_NAME` constants
- `detect(url)` — return True if URL matches your platform
- `extract_ids(url)` — extract IDs from URL
- `fetch_tour_data(session, ids)` — fetch raw data from platform
- `parse_tour(raw_data)` — normalize into the standard tour dict

Then register it in `providers/__init__.py`.

---

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/fjimenez77/360-MLS-Downloader/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce (include the tour URL if possible)
- Your OS and Python version

---

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
