# Персональні Codex Skills

## Призначення

Цей репозиторій — єдине джерело істини для моїх персональних Codex Skills. Він зберігає їхню версійну історію та дає змогу однаково встановлювати skills на macOS, Linux і Windows.

## Доступні Skills

| Skill | Призначення |
| --- | --- |
| requirements-extract | витяг вимог із джерел |
| requirements-critic | незалежна критика вимог |
| specification-compiler | REQ → INV / AC / FAIL |
| youtrack-mermaid | Mermaid-схеми для статей YouTrack |

`python-project-harness` не включено: його не знайдено у локальному джерелі під час створення репозиторію.

## Встановлення macOS / Linux

```bash
git clone <PRIVATE_REPOSITORY_URL>
cd codex-personal-skills
./scripts/install.sh
```

Скрипт обирає `$HOME/.codex/skills`, якщо існує `$HOME/.codex` (або немає `$HOME/.agents`); інакше використовує `$HOME/.agents/skills`. Щоб явно задати каталог, використайте `CODEX_SKILLS_DIR`:

```bash
CODEX_SKILLS_DIR="$HOME/.codex/skills" ./scripts/install.sh
```

Скрипт встановлює лише директорії з цього репозиторію, зберігає сторонні skills і перевіряє наявність `SKILL.md` у кожному встановленому skill.

## Встановлення Windows

Потрібні Windows 11, PowerShell 7+, Git for Windows і Codex. WSL не потрібен.

```powershell
git clone <PRIVATE_REPOSITORY_URL>
cd codex-personal-skills
.\scripts\install.ps1
```

Скрипт використовує `$HOME`, а якщо він недоступний — `$env:USERPROFILE`. За тією самою логікою він обирає `.codex\skills` або наявний `.agents\skills`. Каталог можна перевизначити змінною `$env:CODEX_SKILLS_DIR`.

## Оновлення

На macOS / Linux:

```bash
./scripts/update.sh
```

На Windows:

```powershell
.\scripts\update.ps1
```

Обидва скрипти виконують `git pull --ff-only`, після чого запускають установлення та валідацію. Вони не використовують `git reset --hard` або `git clean -fd`.

## Розробка нового Skill

```text
створити або змінити skill у цьому репозиторії
        ↓
перевірити локально
        ↓
commit
        ↓
push
        ↓
на інших машинах виконати update
```

## Правила

- Репозиторій є source of truth; локальні правки встановленої копії не є постійними.
- Зміни слід робити в цьому репозиторії, а не в установленій копії.
- У репозиторії не зберігаються secrets, credentials, `.env` або персональні конфігурації Codex.
- Project-specific skills не належать до цього репозиторію.

Детальні критерії розмежування наведено у [docs/skill-development.md](docs/skill-development.md).
