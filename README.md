# Персональні Codex Skills

## Призначення

Цей репозиторій — єдине джерело істини для моїх персональних Codex Skills. Він зберігає їхню версійну історію та дає змогу однаково встановлювати skills на macOS, Linux і Windows.

## Доступні Skills

| Skill | Коли використовувати |
| --- | --- |
| [`requirements-extract`](skills/requirements-extract/) | витягнути вимоги з неструктурованих джерел |
| [`requirements-critic`](skills/requirements-critic/) | знайти дефекти, суперечності та прогалини у вимогах |
| [`specification-compiler`](skills/specification-compiler/) | перетворити затверджені вимоги на інваріанти, критерії приймання та сценарії відмов |
| [`youtrack-mermaid`](skills/youtrack-mermaid/) | створити або оновити Mermaid-схему в статті YouTrack |
| [`iso-29148-requirements`](skills/iso-29148-requirements/) | витягнути, нормалізувати та трасувати вимоги за практичною методикою ISO/IEC/IEEE 29148 |
| [`quint-formal-modeling`](skills/quint-formal-modeling/) | створити або рецензувати виконувану Quint-модель поведінки |

## Триетапний конвеєр вимог

`requirements-extract`, `requirements-critic` і `specification-compiler` використовують спільний контракт `requirements-pipeline/v1`. JSON є редагованим джерелом істини, а Markdown — автоматично згенерованим представленням.

| Етап | Вхід | JSON-результат | Markdown-представлення |
| --- | --- | --- | --- |
| 1. Extract | вихідні матеріали | `requirements.json` | `requirements.md` |
| 2. Critic | `requirements.json` | `review.json`, після явного затвердження — `baseline.json` | `review.md` |
| 3. Compile | `requirements.json`, `review.json`, `baseline.json` | `specification.json` | `specification.md` |

Між етапами можна редагувати основний JSON і повторно запускати відповідний skill. Повторний запуск не перезаписує ручні зміни: він створює `*.candidate.json`. Зміна вимог або критики після затвердження робить baseline неактуальним через розбіжність SHA-256.

**Мініприклад процесу:**

```text
1. Використай $requirements-extract для materials/brief.md і створи docs/requirements/requirements.json.
2. Після моїх правок використай $requirements-critic для docs/requirements/requirements.json.
3. Коли зауваження усунуті, я явно затверджу baseline.
4. Використай $specification-compiler для затвердженого docs/requirements/baseline.json.
```

### `requirements-extract`

Перетворює брифи, специфікації, нотатки зустрічей і описи процесів на валідований `requirements.json` та похідний `requirements.md`. Розрізняє бізнес-цілі, бізнес-вимоги, функціональні й нефункціональні вимоги, обмеження та відкриті питання; зберігає джерела й походження тверджень. Не вигадує відсутні деталі, а повторний запуск захищає ручні правки через candidate-файл.

**Мініприклад:** `Використай $requirements-extract: витягни вимоги з brief.md у docs/requirements/requirements.json і створи Markdown-представлення.`

### `requirements-critic`

Читає `requirements.json`, не змінюючи його, та створює валідований `review.json` із похідним `review.md`. Виявляє неоднозначності, суперечності, приховані припущення, невизначені терміни, нетестовані твердження й пропущені сценарії відмов. Після усунення блокерів і тільки за явним рішенням людини створює `baseline.json`, прив'язаний до вимог і критики хешами.

**Мініприклад:** `Використай $requirements-critic: перевір docs/requirements/requirements.json, створи review.json і не змінюй вимоги.`

### `specification-compiler`

Перевіряє `baseline.json`, SHA-256 вхідних файлів і відсутність відкритих блокерів, після чого створює `specification.json` та похідний `specification.md`. Компілює вимоги в інваріанти `INV-*`, спостережувані критерії приймання `AC-*`, сценарії відмов `FAIL-*` і прогалини `GAP-*`, зберігаючи трасування до вихідних requirement ID.

**Мініприклад:** `Використай $specification-compiler для docs/requirements/baseline.json і створи трасований specification.json.`

### `youtrack-mermaid`

Створює та редагує Mermaid-діаграми для статей Interstarch YouTrack. Узгоджує схему з текстом статті, використовує безпечний для рендерера синтаксис, короткі підписи й семантичні кольори; після дозволеного оновлення повторно читає статтю та перевіряє візуальний результат.

**Мініприклад:** `Використай $youtrack-mermaid: додай до статті YouTrack схему потоку погодження заявки та перевір її рендеринг.`

### `iso-29148-requirements`

Витягує, нормалізує та трасує вимоги зі вставленого тексту або локальних `PDF`, `DOCX`, `XLSX`, `Markdown` і `TXT`. Створює канонічний `requirements.json`, реєстр вимог, документи `BRS` / `StRS` / `SyRS` / `SRS`, матрицю трасування та список відкритих питань; зберігає джерела й локатори та відокремлює цілі, припущення, рішення, визначення й межі системи. Методика спирається на публічні принципи ISO/IEC/IEEE 29148:2018 і не заявляє сертифікованої відповідності стандарту.

Це окремий розширений процес: його `requirements.json` не є проміжним артефактом нейтрального триетапного конвеєра.

**Мініприклад:** `Використай $iso-29148-requirements: опрацюй materials/specification.pdf і notes.xlsx, сформуй нормалізований реєстр вимог та матрицю трасування українською.`

### `quint-formal-modeling`

Створює або рецензує виконувані Quint (`.qnt`) моделі протоколів, бізнес-процесів, алгоритмів і машин станів за вимогами чи кодом. Відокремлює модель від її джерел і припущень, фіксує `OPEN-*`, перевіряє досяжність сценаріїв через witnesses, інваріанти безпеки й коректно розрізняє вибіркову симуляцію від bounded model checking.

**Мініприклад:** `Використай $quint-formal-modeling: побудуй виконувану модель процесу розподілу ресурсу, перевір відсутність подвійного розподілу та окремо покажи відкриті припущення.`

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

Перевірити контракти й runtime-утиліти:

```bash
python scripts/sync_requirements_contracts.py --check
python -m unittest discover -s tests -v
```

## Правила

- Репозиторій є source of truth; локальні правки встановленої копії не є постійними.
- Зміни слід робити в цьому репозиторії, а не в установленій копії.
- У репозиторії не зберігаються secrets, credentials, `.env` або персональні конфігурації Codex.
- Project-specific skills не належать до цього репозиторію.

Детальні критерії розмежування наведено у [docs/skill-development.md](docs/skill-development.md).
