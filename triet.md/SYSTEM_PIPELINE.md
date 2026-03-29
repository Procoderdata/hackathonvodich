# Atlas Orrery — System Pipeline (Submission-ready)

> File này chỉ tập trung vào pipeline thực thi: data refresh, runtime decision loop, UI update, test/release.

---

## 1) Pipeline A — Data refresh (offline)

```mermaid
flowchart LR
    T[Trigger: schedule or manual] --> E[Extract NASA archive]
    E --> N[Normalize columns]
    N --> V[Validate required fields]
    V -->|pass| W1[Write orbital_elements.csv]
    V -->|pass| W2[Write orbital_elements.meta.json]
    V -->|fail| F[Keep previous dataset]
    W1 --> C[Warm runtime cache]
    W2 --> C
```

### Input
- Raw rows từ NASA Exoplanet Archive.

### Output
- `data/orbital_elements.csv`
- `data/orbital_elements.meta.json`

### Failure behavior
- Validation fail -> không overwrite dataset cũ.
- Runtime API vẫn dùng dataset/cached version trước.

---

## 2) Pipeline B — User interaction to council response (online)

```mermaid
flowchart LR
    U[User action: scan/filter/select] --> FE[Frontend state aggregation]
    FE --> P[Build mission_context_packet]
    P --> API[POST /api/council/respond]
    API --> OR[Orchestrator parse and policy]
    OR --> TL1[rank_targets_for_context]
    OR --> TL2[compute_habitability_score]
    OR --> TL3[build_council_votes]
    TL1 --> OR
    TL2 --> OR
    TL3 --> OR
    OR --> R[council_response_package]
    R --> UI[Console + recommendation + options]
    UI --> U
```

### Step-by-step execution
1. FE bắt event từ scan/filter/selection.
2. FE gom state thành `mission_context_packet`.
3. API validate payload.
4. Orchestrator gọi tools deterministic.
5. Nếu không có candidate -> trả `insufficient_evidence`.
6. Nếu có candidate -> build votes + recommendation.
7. Trả response có cấu trúc ổn định.
8. FE render headline, votes, options cho vòng tiếp theo.

---

## 3) Pipeline C — Council branching logic

```mermaid
flowchart TD
    A[Input payload + objects] --> B[Normalize mission context]
    B --> C[Rank candidates by filters]
    C --> D{Candidates empty?}
    D -->|Yes| E[Return insufficient_evidence package]
    D -->|No| F[Pick primary target]
    F --> G[Build per-agent votes]
    G --> H[Compose recommendation and evidence summary]
    H --> I[Return council_response_package]
```

---

## 4) Pipeline D — UI update

```mermaid
sequenceDiagram
    participant FE as Unity UI
    participant API as Flask Council API
    participant Panel as Mission and Console Panels

    FE->>API: POST mission_context_packet
    API-->>FE: council_response_package
    FE->>Panel: render headline
    FE->>Panel: render recommendation
    FE->>Panel: render votes (support/caution)
```

UI policy:
- `command` cho headline chính.
- `info` cho support votes.
- `warning` cho caution votes.

---

## 5) Pipeline E — Quality and release gate

```mermaid
flowchart LR
    C1[Code change] --> C2[Unit tests: tools and orchestrator]
    C2 --> C3[API smoke: /api/council/respond]
    C3 --> C4[Client smoke: scan/filter/select flow]
    C4 --> C5[Build check]
    C5 --> C6[Demo rehearsal]
```

Minimum gates:
- Unit tests pass.
- Response contract keys luôn đủ.
- `insufficient_evidence` branch không lỗi.
- Client render được support + caution logs.

---

## 6) Pipeline SLO targets (demo)

- Council response p95 < 1200ms (local env).
- UI update after response < 200ms.
- Council endpoint error rate < 1% trong demo session.

---

## 7) Pipeline risk controls

1. Spam request khi đổi filter liên tục
- FE debounce + loading guard.

2. Response đến muộn làm lệch state
- Chỉ apply response mới nhất theo `request_id`/timestamp.

3. Candidate rỗng gây dead-end UX
- Trả gợi ý tự động: widen filters hoặc compare analogs.

4. Model provider lỗi trong lúc demo
- Fallback chain: `Grok -> DeepSeek -> Qwen`.
- Nếu lỗi toàn bộ -> deterministic fallback response.

---

## 8) Definition of done (MVP)

- [ ] Hoàn thành 1 vòng user-action -> council-response -> UI-update ổn định.
- [ ] Có nhánh xử lý lỗi và thiếu dữ liệu.
- [ ] Có log đủ để debug realtime demo.
- [ ] Chạy được đầy đủ trong 3 mode: Sandbox, Challenge, Discovery.
