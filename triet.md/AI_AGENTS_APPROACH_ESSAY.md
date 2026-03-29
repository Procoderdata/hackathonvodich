# Atlas Orrery — AI Agents Approach Essay (Submission-ready)

## 0) Mục tiêu tài liệu

Tài liệu này mô tả cách tiếp cận tích hợp AI Agents vào Atlas Orrery theo hướng **triển khai được trong hackathon** và **bảo vệ được trước ban giám khảo kỹ thuật**.

Mục tiêu của hệ thống Agentic AI:
1. ra quyết định có mục tiêu,
2. giải thích được lý do,
3. phản biện rủi ro,
4. cải thiện dần qua vòng lặp tương tác.

---

## 1) Bài toán sản phẩm

Atlas Orrery đã mạnh ở 2 điểm:
- trực quan 3D,
- dữ liệu exoplanet thật.

Nút thắt là `decision intelligence`: người dùng nhìn thấy nhiều dữ liệu nhưng không biết nên làm gì tiếp theo để khám phá hiệu quả.

Vì vậy, AI trong dự án này không phải chatbot chung chung. Nó phải là hệ **task-oriented scientific copilot** có khả năng:
- đề xuất mục tiêu tiếp theo,
- cân bằng cơ hội và rủi ro,
- đưa ra hành động cụ thể ngay vòng kế tiếp.

---

## 2) Triết lý thiết kế

### 2.1 Deterministic-first

Các khối liên quan trực tiếp đến tính đúng khoa học phải deterministic:
- lọc dữ liệu,
- chấm điểm baseline,
- kiểm tra điều kiện hợp lệ,
- đánh dấu thiếu bằng chứng.

### 2.2 Agentic-on-top

Agent tập trung vào:
- planning,
- explanation,
- phản biện,
- đề xuất next action.

### 2.3 Contract-driven

FE và BE giao tiếp qua JSON schema ổn định, không phụ thuộc parsing text tự do.

### 2.4 Evidence-first

Mỗi kết luận phải có `evidence_fields` map về dữ liệu thật. Thiếu dữ liệu thì trả `insufficient_evidence`.

---

## 3) Mô hình AI Council

### 3.1 Council Orchestrator

Nhiệm vụ:
- nhận `mission_context_packet`,
- gọi deterministic tools,
- gọi model router (nếu cần),
- tổng hợp support/caution,
- trả `council_response_package`.

### 3.2 Navigator

Nhiệm vụ:
- chọn mục tiêu ưu tiên,
- đề xuất scan pattern,
- tối ưu theo mode (Sandbox/Challenge/Discovery).

### 3.3 Astrobiologist

Nhiệm vụ:
- đánh giá habitability theo heuristic,
- nêu rationale dựa trên `radius/temp/insolation`.

### 3.4 Climate/Orbital

Nhiệm vụ:
- phản biện rủi ro,
- chỉ ra bất định của dữ liệu,
- ngăn kết luận quá lạc quan.

### 3.5 Archivist

Nhiệm vụ:
- chuyển kết quả kỹ thuật thành narrative dễ hiểu,
- ghi mission log,
- đề xuất lựa chọn tiếp theo.

---

## 4) Vòng quyết định mỗi turn

Mỗi thao tác người dùng kích hoạt vòng OODA biến thể:
1. **Observe**: đọc context hiện tại.
2. **Orient**: lọc/rank candidate theo constraints.
3. **Debate**: tạo support/caution votes.
4. **Decide**: chọn recommendation chính.
5. **Act**: trả action khả thi cho UI.
6. **Reflect**: lưu log để cải thiện vòng kế tiếp.

---

## 5) Mapping với thuộc tính Agentic AI

### Goal-driven
- objective rõ trong payload (`player_goal`).
- response luôn có `primary_recommendation.action`.

### Planning
- recommendation đi kèm `player_options`.
- scan/filter/compare là các plan primitives.

### Autonomy
- context đổi thì thứ tự ưu tiên tự đổi.
- không cần user hỏi từng bước nhỏ.

### Feedback loop
- lưu `recent_actions` và `recent_discoveries`.
- giảm gợi ý lặp lại kém hiệu quả.

---

## 6) Vì sao cách này tránh hallucination

Không chỉ nhắc "đừng hallucinate", mà khóa bằng kiến trúc:
- whitelist fields được phép dùng,
- validate schema trước khi trả,
- buộc nhánh `insufficient_evidence` khi thiếu dữ liệu,
- hiển thị evidence cùng recommendation trên UI.

---

## 7) Chất lượng đầu ra (rubric)

Một response đạt chuẩn khi:
1. có hành động cụ thể (`action` + `target_id`),
2. có lý do bám dữ liệu (`reason` + `evidence_fields`),
3. có phản biện rủi ro (`stance=caution` khi cần),
4. có fallback an toàn khi thiếu dữ liệu,
5. có ngôn ngữ đủ rõ để user hành động ngay.

---

## 8) Lộ trình trưởng thành

### Tier 1 — Deterministic Council (MVP hackathon)
- deterministic tools + schema contract + stable endpoint.
- mục tiêu: chạy chắc, minh bạch, demo được.

### Tier 2 — Hybrid reasoning
- thêm LLM để tăng chất lượng strategy/explanation.
- vẫn bắt buộc evidence mapping.

### Tier 3 — Adaptive mission intelligence
- học từ acceptance rate và hành vi user.
- đề xuất challenge động theo profile.

---

## 9) Tính khả thi với team 3 người

- **Người 1 (Backend/AI)**: orchestrator + tools + model router.
- **Người 2 (Unity)**: mode UI, mission panel, console rendering.
- **Người 3 (Data/Integration)**: dataset pipeline, API contract test, demo hardening.

Điểm mấu chốt để tránh vỡ scope:
- khóa contract sớm,
- làm deterministic trước,
- thêm LLM sau,
- luôn có fallback khi model lỗi.

---

## 10) Kết luận

Cách tiếp cận đúng cho Atlas Orrery không phải "gắn một chatbot", mà là xây **decision engine có trách nhiệm**: có mục tiêu, có bằng chứng, có phản biện, có hành động cụ thể, và đủ ổn định để demo thực chiến.

Đây là hướng vừa bám sát chủ đề Agentic AI, vừa khả thi trong điều kiện hackathon.
