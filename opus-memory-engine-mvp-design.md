# Memory Engine MVP — Проектный дизайн

## Executive Summary

Memory Engine — система превращения разрозненных диалогов и заметок в структурированную память с actionable-выводами. MVP за 2 недели: CLI-инструмент на Python, который парсит markdown-файлы (MEMORY.md + дневные логи), извлекает атомарные единицы памяти, хранит их в векторном хранилище, и генерирует weekly summary с верифицированными next actions.

**Ключевой принцип**: каждый факт в output трассируется до конкретной строки в конкретном файле. Нет источника — нет утверждения.

---

## Сравнение вариантов

| Критерий | Вариант A: Lean | Вариант B: Pro-Lite |
|---|---|---|
| **Векторное хранилище** | ChromaDB (встроенный SQLite) | Qdrant (Docker) |
| **Embedding-модель** | `all-MiniLM-L6-v2` (локальная, 384d) | `text-embedding-3-small` (OpenAI API, 1536d) |
| **LLM для extraction** | Claude Sonnet через API | Claude Sonnet через API |
| **Retrieval** | Semantic search only | Hybrid (semantic + BM25 + scoring) |
| **Anti-hallucination** | Source citation + confidence | + cross-reference verification |
| **Хранение** | JSON files + Chroma | JSON files + Qdrant + SQLite metadata |
| **Время разработки** | 8–10 дней | 12–14 дней |
| **Сложность поддержки** | Низкая (pip install, всё локально) | Средняя (Docker для Qdrant) |
| **Качество retrieval** | Хорошее (достаточно для MVP) | Отличное (hybrid search) |
| **Масштабируемость** | До ~5K записей комфортно | До ~100K+ записей |

### Рекомендация: Вариант A (Lean) с миграционным путём на B

**Почему:**
1. 2 недели — жёсткий срок, Lean даёт буфер на отладку
2. ChromaDB достаточен для объёма personal notes (сотни, не миллионы документов)
3. Главная ценность MVP — в extraction pipeline и anti-hallucination, а не в storage engine
4. Абстрагируем storage layer за интерфейсом → переход на Qdrant за 1 день когда понадобится

---

## 1. Архитектура MVP

```
┌─────────────────────────────────────────────────────┐
│                    CLI Interface                     │
│  memory ingest | memory query | memory weekly        │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
           ▼              ▼              ▼
┌──────────────┐ ┌───────────────┐ ┌──────────────────┐
│   Ingestion  │ │   Retrieval   │ │    Reasoning     │
│    Layer     │ │    Layer      │ │     Layer        │
│              │ │               │ │                  │
│ • Parse MD   │ │ • Hybrid      │ │ • Weekly Summary │
│ • Extract    │ │   search      │ │ • Next Actions   │
│   atoms      │ │ • Scoring     │ │ • Verification   │
│ • Embed      │ │ • Ranking     │ │ • Citation       │
│ • Store      │ │ • Filter      │ │ • Confidence     │
└──────┬───────┘ └───────┬───────┘ └────────┬─────────┘
       │                 │                   │
       ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────┐
│                   Storage Layer                      │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │  ChromaDB  │  │ JSON Files │  │  Source Index  │  │
│  │ (vectors)  │  │  (atoms)   │  │ (file:line)   │  │
│  └────────────┘  └────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 1.1 Ingestion Layer

```python
# Pseudocode pipeline
class IngestionPipeline:
    def ingest(self, filepath: str):
        # 1. Parse markdown → chunks с метаданными
        chunks = self.parser.parse(filepath)
        # Каждый chunk знает свой file, line_start, line_end

        # 2. LLM extraction: chunk → atomic memory units
        for chunk in chunks:
            atoms = self.extractor.extract(chunk)
            # extractor использует Claude с structured output
            # каждый atom получает source_ref от chunk

        # 3. Deduplication: проверка на семантические дубли
        unique_atoms = self.deduplicator.filter(atoms)

        # 4. Embed + store
        self.store.upsert(unique_atoms)
```

**Chunking-стратегия:**
- MEMORY.md: по секциям (## headers) — каждая секция = chunk
- Дневные логи: по записям (разделитель `---` или `##` по дате/теме)
- Overlap: 2 предложения между chunks для контекста
- Max chunk size: ~500 токенов (оптимально для extraction quality)

### 1.2 Storage Layer

```
data/
├── chroma_db/           # Векторное хранилище
├── atoms/               # JSON-файлы атомарных единиц
│   ├── index.json       # Мастер-индекс всех atoms
│   └── 2026-01/         # По месяцам
│       ├── atom_a1b2c3.json
│       └── atom_d4e5f6.json
├── sources/             # Индекс источников
│   └── source_map.json  # atom_id → [{file, line_start, line_end, text}]
└── outputs/             # Сгенерированные отчёты
    └── weekly/
        └── 2026-W09.md
```

### 1.3 Retrieval Layer

Запрос → multi-signal scoring → ranked results с source citations.

### 1.4 Reasoning Layer

Получает ranked atoms + их source citations → генерирует output через LLM с жёстким промптом, запрещающим утверждения без source_ref.

---

## 2. Qdrant vs ChromaDB для MVP

| Фактор | ChromaDB | Qdrant |
|---|---|---|
| **Установка** | `pip install chromadb` | Docker + `pip install qdrant-client` |
| **Локальный запуск** | Встроенный (in-process SQLite) | Docker container (port 6333) |
| **Надёжность** | Хорошая для малых объёмов. Известны баги при >50K записей | Production-grade, используется в проде |
| **Простота** | Минимальная — 5 строк кода для старта | Средняя — нужен Docker, чуть больше конфигурации |
| **Качество retrieval** | Cosine/L2/IP, без built-in hybrid | Cosine/Dot/Euclid + built-in sparse vectors для hybrid |
| **Filtering** | Metadata filtering (базовый) | Payload filtering (мощный, с вложенными условиями) |
| **Persistence** | SQLite (автоматическая) | RocksDB (надёжная) |
| **Python API** | Простой, pythonic | Более verbose, но мощный |
| **Hybrid search** | Нужно реализовать вручную (BM25 отдельно) | Встроенные sparse vectors |
| **Масштабирование** | До ~50K комфортно | До миллионов |

**Решение для MVP: ChromaDB**

Причины:
1. Zero-config: нет Docker-зависимости, проще CI/CD
2. Для personal notes (сотни–тысячи записей) — более чем достаточно
3. Hybrid search реализуем через BM25 (rank_bm25 library) + Chroma cosine → комбинированный score
4. Миграция на Qdrant: абстрагируем за `VectorStore` интерфейсом, переход за ~4 часа

```python
# Абстракция для будущей миграции
class VectorStore(Protocol):
    def upsert(self, atoms: list[MemoryAtom]) -> None: ...
    def search(self, query: str, filters: dict, top_k: int) -> list[SearchResult]: ...
    def delete(self, atom_ids: list[str]) -> None: ...

class ChromaStore(VectorStore): ...   # MVP
class QdrantStore(VectorStore): ...   # Будущее
```

---

## 3. Схема Atomic Memory Unit

```json
{
  "$schema": "memory_atom_v1",

  "id": "atom_a1b2c3d4",
  "type": "decision | commitment | preference | objective | blocker | insight",
  "created_at": "2026-02-20T14:30:00Z",
  "updated_at": "2026-02-20T14:30:00Z",

  "content": {
    "summary": "Краткое описание (1-2 предложения)",
    "detail": "Полное описание с контекстом",
    "entities": ["entity1", "entity2"],
    "tags": ["tag1", "tag2"]
  },

  "source": {
    "file": "memory/2026-02-20.md",
    "line_start": 42,
    "line_end": 47,
    "text_excerpt": "Точная цитата из источника (до 200 символов)",
    "ingested_at": "2026-02-20T15:00:00Z"
  },

  "metadata": {
    "confidence": 0.92,
    "impact": "high | medium | low",
    "status": "active | completed | superseded | cancelled",
    "superseded_by": null,
    "related_atoms": ["atom_x1y2z3"],
    "extraction_model": "claude-sonnet-4-5-20250929"
  },

  "type_specific": {}
}
```

### Type-specific расширения

```json
// decision
"type_specific": {
  "alternatives_considered": ["вариант A", "вариант B"],
  "rationale": "Почему выбрано именно это",
  "reversible": true,
  "deadline": null
}

// commitment
"type_specific": {
  "committed_to": "Кому/чему обязательство",
  "deadline": "2026-03-01",
  "strength": "hard | soft | aspirational",
  "progress": 0.0,
  "dependencies": []
}

// preference
"type_specific": {
  "domain": "tools | workflow | communication | lifestyle",
  "strength": "strong | moderate | weak",
  "context": "В каком контексте применимо"
}

// objective
"type_specific": {
  "timeframe": "week | month | quarter | year",
  "key_results": ["KR1", "KR2"],
  "progress": 0.0,
  "parent_objective": null
}

// blocker
"type_specific": {
  "blocking": ["atom_id целей, которые блокируются"],
  "severity": "critical | significant | minor",
  "resolution_options": ["вариант решения 1"],
  "resolved": false
}

// insight
"type_specific": {
  "domain": "technical | business | personal | meta",
  "actionable": true,
  "applied": false,
  "supporting_evidence": ["ссылка на другие atoms"]
}
```

---

## 4. Гибридный Retrieval и Scoring

### 4.1 Multi-Signal Retrieval

```python
def hybrid_search(query: str, context: SearchContext) -> list[ScoredAtom]:
    # Signal 1: Semantic similarity (ChromaDB)
    semantic_results = chroma.query(
        query_embedding=embed(query),
        n_results=50
    )

    # Signal 2: Keyword overlap (BM25)
    bm25_results = bm25_index.search(query, top_k=50)

    # Signal 3: Расширяем кандидатов через entity/tag overlap
    candidate_ids = set()
    for r in semantic_results + bm25_results:
        candidate_ids.add(r.id)
        candidate_ids.update(r.related_atoms)  # граф связей

    candidates = load_atoms(candidate_ids)

    # Score каждого кандидата
    scored = [score_atom(atom, query, context) for atom in candidates]

    return sorted(scored, key=lambda x: x.final_score, reverse=True)
```

### 4.2 Формула приоритизации

```
final_score = Σ(wi × si) / Σ(wi)

где:
  s1 = semantic_similarity     (cosine, 0..1)        w1 = 0.30
  s2 = keyword_overlap         (BM25 normalized)     w2 = 0.15
  s3 = recency_score           (decay function)      w3 = 0.15
  s4 = impact_score            (high=1, med=0.6, low=0.3)  w4 = 0.15
  s5 = commitment_strength     (hard=1, soft=0.6, asp=0.3) w5 = 0.15
  s6 = repeat_frequency        (normalized count)    w6 = 0.10
```

### Recency decay function

```python
def recency_score(atom_date: datetime, now: datetime) -> float:
    """Экспоненциальный decay с half-life = 14 дней."""
    days_ago = (now - atom_date).days
    half_life = 14  # настраиваемый параметр
    return math.exp(-0.693 * days_ago / half_life)
    # 0 дней → 1.0
    # 7 дней → 0.71
    # 14 дней → 0.50
    # 30 дней → 0.23
```

### Repeat frequency

```python
def repeat_frequency(atom: MemoryAtom, all_atoms: list) -> float:
    """Сколько раз тема/entity упоминалась в разных источниках."""
    mentions = count_entity_mentions(atom.content.entities, all_atoms)
    return min(mentions / 10.0, 1.0)  # cap at 10 mentions = 1.0
```

### Context-aware boosting

```python
# Для weekly summary — бустим commitment и blocker
WEEKLY_WEIGHTS = {
    "commitment": 1.3,  # boost
    "blocker": 1.4,     # highest boost
    "objective": 1.2,
    "decision": 1.0,
    "insight": 0.9,
    "preference": 0.7   # менее релевантно для weekly
}

def context_boost(atom: MemoryAtom, context: str) -> float:
    if context == "weekly_summary":
        return WEEKLY_WEIGHTS.get(atom.type, 1.0)
    return 1.0
```

---

## 5. Анти-галлюцинационный контур

### Принцип: "No source, no claim"

Каждое утверждение в output должно быть трассируемо до source_ref. Если источника нет — утверждение не включается.

### 5.1 Архитектура верификации

```
Atoms (scored, ranked)
        │
        ▼
┌───────────────────┐
│  Source Verifier   │   ← Проверяет: существует ли файл?
│                    │     Совпадает ли цитата с файлом?
│  • file_exists?    │     Не устарел ли atom?
│  • text_matches?   │
│  • not_superseded? │
└────────┬──────────┘
         │
    verified_atoms
         │
         ▼
┌───────────────────┐
│  Summary Generator │   ← LLM с жёстким system prompt
│                    │
│  "Каждое утверж-   │
│   дение ОБЯЗАНО    │
│   содержать [src]" │
└────────┬──────────┘
         │
    draft_summary
         │
         ▼
┌───────────────────┐
│  Claim Validator   │   ← Второй LLM-проход:
│                    │     "Найди утверждения без [src]"
│  • has_citation?   │     "Найди утверждения, не подкреплённые atoms"
│  • matches_atom?   │
│  • confidence_ok?  │
└────────┬──────────┘
         │
    validated_summary
         │
         ▼
┌───────────────────┐
│  Confidence Tagger │   ← Каждому блоку summary:
│                    │     🟢 high (>0.85): прямая цитата
│  [🟢/🟡/🔴]       │     🟡 medium (0.6-0.85): inference
│                    │     🔴 low (<0.6): помечен как uncertain
└───────────────────┘
```

### 5.2 System Prompt для Summary Generator

```
Ты генерируешь weekly summary на основе ТОЛЬКО предоставленных memory atoms.

ЖЕЛЕЗНЫЕ ПРАВИЛА:
1. Каждое утверждение ОБЯЗАНО иметь ссылку [src: atom_id]
2. Если атом имеет confidence < 0.6, пометь как "⚠️ uncertain"
3. НИКОГДА не выдумывай факты, даты, имена, числа
4. Если информации недостаточно, напиши "Недостаточно данных для вывода"
5. Для next actions — только те, что следуют из commitments/objectives/blockers
6. Не делай выводов, которые не поддерживаются минимум 1 атомом

ФОРМАТ КАЖДОГО УТВЕРЖДЕНИЯ:
"<утверждение> [src: <atom_id>, confidence: <0.XX>]"
```

### 5.3 Claim Validator (второй проход)

```python
def validate_summary(summary: str, atoms: dict[str, MemoryAtom]) -> ValidationResult:
    """
    Парсим summary, находим все [src: ...] ссылки,
    проверяем что atom существует и утверждение ему соответствует.
    """
    claims = extract_claims(summary)

    for claim in claims:
        # Check 1: Есть ли ссылка?
        if not claim.source_ref:
            claim.status = "UNSOURCED"
            continue

        # Check 2: Существует ли atom?
        atom = atoms.get(claim.source_ref)
        if not atom:
            claim.status = "BROKEN_REF"
            continue

        # Check 3: Соответствует ли утверждение атому?
        similarity = cosine_sim(embed(claim.text), embed(atom.content.summary))
        if similarity < 0.65:
            claim.status = "MISMATCH"
            continue

        # Check 4: Confidence threshold
        if atom.metadata.confidence < 0.6:
            claim.status = "LOW_CONFIDENCE"
            continue

        claim.status = "VERIFIED"

    return ValidationResult(claims)
```

### 5.4 Fallback Behavior

| Ситуация | Действие |
|---|---|
| Утверждение без source_ref | Удалить из финального output |
| Atom confidence < 0.6 | Пометить ⚠️, включить только если критично |
| Противоречивые atoms | Показать оба с пометкой "⚡ conflict" |
| Нет данных за неделю | "Нет записей за период. Рекомендация: обновить дневной лог" |
| Broken source ref | Логировать ошибку, исключить из output |

### 5.5 Формат финального weekly summary

```markdown
# Weekly Summary: 2026-W09 (24 Feb — 2 Mar)

## Ключевые решения
- Выбран ChromaDB для MVP Memory Engine
  [src: atom_a1b2, confidence: 0.95, file: memory/2026-02-25.md:42-47]

## Активные commitments
- ⏰ Сдать MVP Lead Finder до 1 марта (hard commitment)
  [src: atom_c3d4, confidence: 0.88, file: MEMORY.md:120-125]
  Progress: ~60%

## Blockers
- 🔴 Заморозка счёта клиента X задерживает оплату
  [src: atom_e5f6, confidence: 0.91, file: memory/2026-02-24.md:15-20]
  Варианты решения: [подождать | эскалировать | переключиться]

## Top Next Actions
1. [ACTION] Завершить extraction pipeline (из objective atom_g7h8)
2. [ACTION] Связаться с клиентом Y по поводу нового проекта (из commitment atom_i9j0)

## Insights недели
- 💡 Hybrid search даёт +15% precision vs pure semantic
  [src: atom_k1l2, confidence: 0.78, ⚠️ single source]

## Confidence Report
- 🟢 High confidence claims: 8/10
- 🟡 Medium confidence: 1/10
- 🔴 Low/uncertain: 1/10
- Sources verified: 9/10
```

---

## 6. План реализации на 2 недели

### Неделя 1: Core Pipeline

| День | Задача | Артефакты | Проверки |
|---|---|---|---|
| **Д1** | Скаффолдинг проекта, CLI каркас, конфиги | `pyproject.toml`, CLI entry points, config.yaml | `memory --help` работает |
| **Д2** | Markdown parser + chunking | `parser.py`, тесты на MEMORY.md | Chunks содержат корректные line_start/line_end |
| **Д3** | Atom extraction через LLM | `extractor.py`, промпт для extraction | 10 manual examples: extraction quality ≥ 80% |
| **Д4** | ChromaDB integration + embedding | `store.py`, `VectorStore` protocol | Upsert + search roundtrip работает |
| **Д5** | Ingestion pipeline end-to-end | `pipeline.py`, `memory ingest` command | `memory ingest ./memory/` парсит все файлы |
| **Д6-7** | Тестирование + отладка extraction quality | Тест-сьют, tuned промпты | Precision/recall на 20 hand-labeled atoms ≥ 75% |

### Неделя 2: Retrieval + Reasoning + Output

| День | Задача | Артефакты | Проверки |
|---|---|---|---|
| **Д8** | BM25 индекс + hybrid search | `retrieval.py`, `memory query` command | Hybrid search возвращает более релевантные результаты vs pure semantic |
| **Д9** | Scoring formula + ranking | `scorer.py`, weight config | Top-5 результатов субъективно корректны на 5 тестовых запросах |
| **Д10** | Weekly summary generator | `summary.py`, system prompts | Генерирует summary с citations |
| **Д11** | Anti-hallucination: claim validator | `validator.py` | 0 unsourced claims в output |
| **Д12** | `memory weekly` command end-to-end | Weekly markdown output | Full pipeline: ingest → query → summary → validated output |
| **Д13** | Edge cases + error handling | Error logs, fallback behaviors | Graceful handling: пустые файлы, битые ссылки, дубли |
| **Д14** | Documentation + dogfooding | README.md, USAGE.md | Прогнать на реальных данных, зафиксировать issues |

---

## 7. Definition of Done

### Функциональные критерии

| # | Критерий | Метрика | Порог |
|---|---|---|---|
| F1 | CLI commands работают | `ingest`, `query`, `weekly` — без crashes | 100% |
| F2 | Extraction quality | Precision на hand-labeled set (30 atoms) | ≥ 75% |
| F3 | Retrieval relevance | Top-5 precision на 10 test queries | ≥ 70% |
| F4 | Source traceability | % claims в weekly summary с валидным source_ref | 100% |
| F5 | No hallucinations | % unsourced claims в финальном output | 0% |
| F6 | Weekly summary usefulness | Субъективная оценка автора (1-5) | ≥ 4 |

### Технические критерии

| # | Критерий | Метрика | Порог |
|---|---|---|---|
| T1 | Ingestion speed | Время обработки 50 markdown файлов | < 5 минут |
| T2 | Query latency | Время ответа на query | < 3 секунды |
| T3 | Weekly generation | Время генерации weekly summary | < 2 минуты |
| T4 | Storage efficiency | Размер ChromaDB для 1000 atoms | < 100 MB |
| T5 | Idempotent ingestion | Повторный ingest не создаёт дубли | Δ atoms = 0 |

### Acceptance test

Прогнать полный цикл на реальных данных (собственные MEMORY.md + 2 недели дневных логов):
1. `memory ingest ./data/` → atoms извлечены корректно
2. `memory query "мои текущие commitments"` → релевантные результаты
3. `memory weekly` → summary без выдуманных фактов, с actionable next steps
4. Ручная проверка: каждый claim в summary → найти source в исходных файлах

---

## Риски и митигации

| # | Риск | Вероятность | Импакт | Митигация |
|---|---|---|---|---|
| R1 | LLM extraction нестабильного качества | Высокая | Высокий | Structured output (JSON mode), few-shot examples в промпте, валидация схемы |
| R2 | Chunking теряет контекст | Средняя | Средний | Overlap между chunks, metadata о parent section |
| R3 | Deduplication ломает связи | Средняя | Средний | Conservative threshold (cosine > 0.95 для дедупа), merge вместо delete |
| R4 | API costs на extraction | Низкая | Средний | Batch processing, кэширование embeddings, инкрементальный ingest |
| R5 | ChromaDB instability на росте | Низкая (для MVP) | Низкий | VectorStore abstraction, migration path на Qdrant готов |
| R6 | Weekly summary слишком generic | Средняя | Высокий | Контекстный буст для commitments/blockers, конкретные промпты |
| R7 | 2 недели — мало | Средняя | Высокий | Lean вариант, scope cut: hybrid search опционален |

---

## Минимальный Backlog

| # | Задача | Приоритет | Оценка | Зависимости |
|---|---|---|---|---|
| 1 | Скаффолдинг проекта (CLI, config, структура) | P0 | 3h | — |
| 2 | Markdown parser с line-level tracking | P0 | 4h | #1 |
| 3 | Atom extraction prompt engineering | P0 | 6h | #2 |
| 4 | JSON schema validation для atoms | P0 | 2h | #3 |
| 5 | ChromaDB integration (VectorStore) | P0 | 4h | #1 |
| 6 | Embedding pipeline (local model) | P0 | 3h | #5 |
| 7 | Ingestion pipeline (end-to-end) | P0 | 4h | #2, #3, #5, #6 |
| 8 | Deduplication engine | P1 | 4h | #6, #7 |
| 9 | BM25 index + hybrid search | P1 | 4h | #7 |
| 10 | Scoring/ranking formula | P1 | 3h | #9 |
| 11 | Weekly summary generator (LLM) | P0 | 5h | #7 |
| 12 | Source verifier | P0 | 3h | #7 |
| 13 | Claim validator (anti-hallucination) | P0 | 4h | #11, #12 |
| 14 | `memory weekly` CLI command | P0 | 2h | #11, #13 |
| 15 | Dogfooding + tuning на реальных данных | P0 | 8h | #14 |

**Итого: ~59 часов → при 4-5 часах/день = 12-14 рабочих дней** ✓

---

## Структура проекта

```
memory-engine/
├── pyproject.toml
├── config.yaml
├── README.md
├── src/
│   └── memory_engine/
│       ├── __init__.py
│       ├── cli.py              # Click/Typer CLI
│       ├── config.py           # Settings
│       ├── parser.py           # Markdown → chunks
│       ├── extractor.py        # Chunks → atoms (LLM)
│       ├── models.py           # Pydantic models (MemoryAtom, etc.)
│       ├── store/
│       │   ├── __init__.py
│       │   ├── protocol.py     # VectorStore protocol
│       │   ├── chroma.py       # ChromaDB implementation
│       │   └── json_store.py   # JSON file storage
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── hybrid.py       # Hybrid search
│       │   ├── bm25.py         # BM25 index
│       │   └── scorer.py       # Multi-signal scoring
│       ├── reasoning/
│       │   ├── __init__.py
│       │   ├── summary.py      # Weekly summary generator
│       │   ├── verifier.py     # Source verifier
│       │   └── validator.py    # Claim validator
│       └── utils/
│           ├── embeddings.py   # Embedding helpers
│           └── dedup.py        # Deduplication
├── tests/
│   ├── test_parser.py
│   ├── test_extractor.py
│   ├── test_retrieval.py
│   └── test_summary.py
├── prompts/
│   ├── extraction.md           # Промпт для atom extraction
│   ├── summary.md              # Промпт для weekly summary
│   └── validation.md           # Промпт для claim validation
└── data/
    ├── test_fixtures/          # Тестовые markdown файлы
    └── labeled/                # Hand-labeled atoms для eval
```

---

## Ключевые зависимости (Python)

```toml
[project]
dependencies = [
    "typer>=0.9",            # CLI framework
    "chromadb>=0.4",         # Vector store
    "sentence-transformers", # Local embeddings
    "anthropic>=0.30",       # Claude API
    "pydantic>=2.0",         # Data models
    "rank-bm25>=0.2",        # BM25 search
    "rich>=13.0",            # Pretty CLI output
]
```
