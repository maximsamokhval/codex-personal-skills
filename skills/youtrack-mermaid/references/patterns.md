# Verified Mermaid patterns for Interstarch YouTrack

These patterns use syntax and visual conventions successfully rendered in `interstarch.youtrack.cloud`. Adapt identifiers and labels to the article. Do not copy illustrative domain values as facts unless the user supplied them.

## Pattern 1: two source lanes converging on one consumer

Use when two independent operations or regional sources pass through equivalent stages and converge on a shared component.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 110, "rankSpacing": 75, "curve": "basis"}, "themeVariables": {"fontSize": "15px"}}}%%
flowchart TD
    subgraph LEFT_FLOW["Джерело A"]
        direction TB
        A0["Документ A"] --> A1["Завантаження A"]
        A1 --> AQ["Виконавець черги"]
        AQ --> AR["Фонове читання"]
        AR --> AT["Перетворення A"]
        AT --> AF["Факт A-F1"]
        AF --> AE["Подія A-E1"]
    end

    subgraph RIGHT_FLOW["Джерело B"]
        direction TB
        B0["Документ B"] --> B1["Завантаження B"]
        B1 --> BQ["Виконавець черги"]
        BQ --> BR["Фонове читання"]
        BR --> BT["Перетворення B"]
        BT --> BF["Факт B-F1"]
        BF --> BE["Подія B-E1"]
    end

    AE --> C["Споживач"]
    BE --> C
    C --> RA["Результат A"]
    C --> RB["Результат B"]

    classDef source fill:#E8F1FF,stroke:#2563EB,color:#172554,stroke-width:2px
    classDef loading fill:#FFF7E6,stroke:#D97706,color:#451A03,stroke-width:2px
    classDef queue fill:#F3E8FF,stroke:#7E22CE,color:#3B0764,stroke-width:2px
    classDef transform fill:#EAFBF1,stroke:#15803D,color:#052E16,stroke-width:2px
    classDef fact fill:#ECFEFF,stroke:#0E7490,color:#164E63,stroke-width:2px
    classDef event fill:#F5F3FF,stroke:#6D28D9,color:#2E1065,stroke-width:2px
    classDef consumer fill:#FFE4E6,stroke:#BE123C,color:#4C0519,stroke-width:3px
    classDef result fill:#F0FDF4,stroke:#16A34A,color:#14532D,stroke-width:2px

    class A0,B0 source
    class A1,B1 loading
    class AQ,BQ queue
    class AR,AT,BR,BT transform
    class AF,BF fact
    class AE,BE event
    class C consumer
    class RA,RB result

    style LEFT_FLOW fill:#F8FAFC,stroke:#93C5FD,stroke-width:2px
    style RIGHT_FLOW fill:#F8FAFC,stroke:#A7F3D0,stroke-width:2px
    linkStyle default stroke:#64748B,stroke-width:2px
```

Follow it with a detail table:

| Потік | Вхід | Перетворення | Канонічний факт | Результат |
| --- | --- | --- | --- | --- |
| A | Exact example fields | What the adapter reads | Key fact fields | Consumer output |
| B | Exact example fields | What the adapter reads | Key fact fields | Consumer output |

## Pattern 2: the same entity across two exchanges

Use when a mutable 1C document and its movements are overwritten by a later exchange. Keep the normal paths solid and cross-version effects dashed.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 110, "rankSpacing": 75, "curve": "basis"}, "themeVariables": {"fontSize": "15px"}}}%%
flowchart TD
    subgraph EX1["Обмін 1"]
        direction TB
        V1["Значення A"] --> D1["Документ: стан A"]
        D1 --> M1["Рухи A"]
        M1 --> Q1["Черга: посилання"]
        Q1 --> T1["ACL: відбиток H1"]
        T1 --> F1["Факт F1"]
        F1 --> E1["Подія E1"]
    end

    subgraph EX2["Обмін 2"]
        direction TB
        V2["Значення B"] --> D2["Документ: стан B"]
        D2 --> M2["Рухи B"]
        M2 --> Q2["Черга: посилання"]
        Q2 --> T2["ACL: відбиток H2"]
        T2 --> F2["Факт F2"]
        F2 --> E2["Подія E2"]
    end

    D1 -. "перезапис" .-> D2
    M1 -. "заміна" .-> M2
    Q1 -. "затримка" .-> T2

    E1 --> C["Споживач"]
    E2 --> C
    C --> OLD["F1 неактуальний"]
    C --> CURRENT["F2 поточний"]
    T2 -.-> LOSS["H1 не зафіксовано"]

    classDef source fill:#E8F1FF,stroke:#2563EB,color:#172554,stroke-width:2px
    classDef loading fill:#FFF7E6,stroke:#D97706,color:#451A03,stroke-width:2px
    classDef queue fill:#F3E8FF,stroke:#7E22CE,color:#3B0764,stroke-width:2px
    classDef transform fill:#EAFBF1,stroke:#15803D,color:#052E16,stroke-width:2px
    classDef fact fill:#ECFEFF,stroke:#0E7490,color:#164E63,stroke-width:2px
    classDef event fill:#F5F3FF,stroke:#6D28D9,color:#2E1065,stroke-width:2px
    classDef consumer fill:#FFE4E6,stroke:#BE123C,color:#4C0519,stroke-width:3px
    classDef result fill:#F0FDF4,stroke:#16A34A,color:#14532D,stroke-width:2px
    classDef warning fill:#FFF1F2,stroke:#E11D48,color:#881337,stroke-width:2px,stroke-dasharray:5 3

    class V1,V2,D1,D2 source
    class M1,M2 loading
    class Q1,Q2 queue
    class T1,T2 transform
    class F1,F2 fact
    class E1,E2 event
    class C consumer
    class OLD,CURRENT result
    class LOSS warning

    style EX1 fill:#F8FAFC,stroke:#93C5FD,stroke-width:2px
    style EX2 fill:#F8FAFC,stroke:#A7F3D0,stroke-width:2px
    linkStyle default stroke:#64748B,stroke-width:2px
```

State in prose what the dashed delayed path means. In particular, do not let a dashed annotation imply that data loss occurs on the normal path.

## Compact palette block

Copy only the classes used by a chart:

```text
classDef source fill:#E8F1FF,stroke:#2563EB,color:#172554,stroke-width:2px
classDef loading fill:#FFF7E6,stroke:#D97706,color:#451A03,stroke-width:2px
classDef queue fill:#F3E8FF,stroke:#7E22CE,color:#3B0764,stroke-width:2px
classDef transform fill:#EAFBF1,stroke:#15803D,color:#052E16,stroke-width:2px
classDef fact fill:#ECFEFF,stroke:#0E7490,color:#164E63,stroke-width:2px
classDef event fill:#F5F3FF,stroke:#6D28D9,color:#2E1065,stroke-width:2px
classDef consumer fill:#FFE4E6,stroke:#BE123C,color:#4C0519,stroke-width:3px
classDef result fill:#F0FDF4,stroke:#16A34A,color:#14532D,stroke-width:2px
classDef warning fill:#FFF1F2,stroke:#E11D48,color:#881337,stroke-width:2px,stroke-dasharray:5 3
linkStyle default stroke:#64748B,stroke-width:2px
```

## Failure patterns to avoid

- HTML line breaks in labels: YouTrack may strip them and concatenate all text.
- Full payloads inside nodes: boxes grow, text clips, and the process becomes unreadable.
- One color for every role: readers cannot scan boundaries.
- Different colors for the same role in adjacent diagrams: the visual vocabulary becomes misleading.
- Very long edge labels: they cross nodes and other connectors.
- A single chart mixing independent entities, revisions, retries, and quarantine: split by question.
- Claiming visual success after only reading article Markdown: inspect the rendered page.
