# Atlas Orrery — Kiến trúc hệ thống chi tiết (Architecture-only)

> File này chỉ mô tả **kiến trúc hệ thống** (thành phần, ranh giới, trách nhiệm, interfaces). Pipeline runtime/offline đã tách riêng sang `SYSTEM_PIPELINE.md`.

---

## 1) System architecture (layered view)

```mermaid
flowchart TB
    subgraph FE[Frontend Layer]
      FE1[Command Center Page]
      FE2[Orrery Engine]
      FE3[Console and Mission UI]
    end

    subgraph API[Application Layer]
      AP1[Orbital Objects Endpoint]
      AP2[Planet Detail Endpoint]
      AP3[Council Respond Endpoint]
      AP4[Orbital Meta Endpoint]
    end

    subgraph CORE[Reasoning Core]
      RC1[Council Orchestrator]
      RC2[Council Schemas]
      RC3[Council Tools]
    end

    subgraph DATA[Data Layer]
      D1[Orbital Elements CSV]
      D2[Orbital Elements Meta JSON]
      D3[TOI and K2 Catalog CSV]
    end

    subgraph JOB[ETL Layer]
      J1[Refresh Orbital Catalog Script]
    end

    FE1 --> AP3
    FE2 --> AP1
    FE1 --> AP2
    AP3 --> RC1
    RC1 --> RC2
    RC1 --> RC3
    AP1 --> D1
    AP4 --> D2
    AP2 --> D1
    J1 --> D1
    J1 --> D2
    J1 --> D3
```

---

## 2) Module architecture (code map)

```mermaid
graph TD
    subgraph Frontend[Frontend Modules]
      F1[Command Center Page File]
      F2[Console Panel File]
      F3[Orrery Engine File]
    end

    subgraph Backend[Backend Modules]
      B1[Server File]
      B2[Council Orchestrator File]
      B3[Council Schemas File]
      B4[Council Tools File]
    end

    subgraph Data[Data Assets]
      D1[Orbital Elements Data]
      D2[Orbital Elements Metadata]
      D3[TOI and K2 Data]
    end

    F1 --> B1
    B1 --> B2
    B2 --> B3
    B2 --> B4
    B1 --> D1
    B1 --> D2
    B1 --> D3
    F3 --> B1
```

---

## 3) Responsibility matrix (RACI-lite)

| Component | Responsibility chính | Không làm |
|---|---|---|
| `CommandCenterPage.jsx` | Thu user interactions, gọi API council, render log/action | Không tính score/ranking |
| `server.py` | Boundary HTTP + load datasets/cache + route responses | Không chứa policy phức tạp của council |
| `council_orchestrator.py` | Điều phối logic decision, chọn branch fallback/candidate | Không đọc file trực tiếp |
| `council_tools.py` | Pure deterministic functions (score/filter/rank/votes) | Không side effects/network I/O |
| `council_schemas.py` | Parse/normalize payload + typed response | Không business logic ranking |
| `scripts/refresh_orbital_catalog.py` | ETL refresh dữ liệu | Không phục vụ runtime API |

---

## 4) Interface boundaries

### 4.1 FE -> API
- Giao tiếp qua JSON contract (request/response council).
- FE không phụ thuộc implementation nội bộ orchestrator.

### 4.2 API -> Core
- API chỉ delegate sang orchestrator.
- Orchestrator nhận `objects + payload`, trả structured dict.

### 4.3 Core -> Data
- Core dùng data đã load sẵn từ API layer.
- Không tự truy cập filesystem.

---

## 5) Non-functional architecture constraints

- Deterministic-first cho lớp reasoning tools.
- Graceful degradation khi thiếu candidate (`insufficient_evidence`).
- Contract-stable để FE render không parse text tự do.
- Tách ranh giới module để dễ test độc lập.

---

## 6) Architecture readiness checklist

- [ ] Module boundaries rõ ràng, không chồng trách nhiệm.
- [ ] Endpoint council không nhúng logic khó test.
- [ ] Tools có thể test độc lập bằng unit tests.
- [ ] Không có dependency vòng giữa modules core.
- [ ] Dễ mở rộng thêm challenge engine mà không phá contract.
