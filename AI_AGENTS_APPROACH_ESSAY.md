# Atlas Orrery — Bản thiết kế tư duy tích hợp AI Agents (phiên bản chi tiết để triển khai code)

## 0) Mục tiêu của tài liệu

Tài liệu này mô tả **cách tiếp cận thực thi** (implementation mindset) để chuyển Atlas Orrery từ một ứng dụng mô phỏng dữ liệu thành hệ thống **Agentic Mission Control** có thể:

1. ra quyết định có mục tiêu,
2. giải thích được vì sao quyết định như vậy,
3. phản biện rủi ro,
4. học dần từ hành vi người dùng.

Đây là “tầng tư duy kiến trúc” song hành với file `TECH_FEASIBILITY_ARCHITECTURE.md` (tập trung flow kỹ thuật và blueprint hạ tầng).

---

## 1) Bài toán thực tế và ngữ cảnh sản phẩm

Atlas Orrery đang mạnh ở 2 điểm:
- mô phỏng trực quan (3D/interaction),
- dữ liệu exoplanet có thật.

Nút thắt là phần “decision intelligence”: người dùng nhìn thấy rất nhiều đối tượng nhưng không biết **nên làm gì tiếp theo** để khám phá có hiệu quả.

Vì vậy, AI agent trong dự án này **không** là chatbot để nói chuyện cho hay; mà là hệ “task-oriented scientific copilot” giúp:
- Ưu tiên target kế tiếp.
- Cân bằng giữa cơ hội và rủi ro.
- Cho người dùng một hành động cụ thể ngay vòng tiếp theo.

---

## 2) Design principles (nguyên tắc thiết kế bất di bất dịch)

## 2.1 Deterministic-first

Các phần liên quan trực tiếp đến dữ liệu khoa học phải deterministic:
- lọc dữ liệu,
- chấm điểm baseline,
- kiểm tra điều kiện hợp lệ,
- đánh dấu thiếu bằng chứng.

## 2.2 Agentic-on-top

Agent hoạt động như lớp điều phối và diễn giải:
- đề xuất chiến lược,
- phản biện,
- đóng gói narrative,
- tạo next action.

## 2.3 Contract-driven

Mọi tương tác FE ↔ BE đi qua JSON schema ổn định.
Không phụ thuộc parsing text tự do.

## 2.4 Evidence-first

Mỗi kết luận cần kèm `evidence_fields`.
Thiếu dữ liệu => trả `insufficient_evidence`.

---

## 3) Mô hình AI Council (vai trò + trách nhiệm)

## 3.1 Council Orchestrator

Vai trò:
- nhận `mission_context_packet`,
- gọi tools,
- điều phối votes,
- resolve mâu thuẫn,
- trả payload cuối cùng.

Output bắt buộc:
- headline,
- primary_recommendation,
- council_votes,
- discovery_log_entry.

## 3.2 Navigator Agent

Mục tiêu:
- chọn mục tiêu ưu tiên kế tiếp.

Dựa trên:
- điểm baseline,
- độ phủ dữ liệu,
- khoảng cách/khả năng quan sát.

## 3.3 Astrobiologist Agent

Mục tiêu:
- đánh giá khả năng ở được theo heuristic.

Dựa trên:
- radius, temp, insolation,
- metadata môi trường sao.

## 3.4 Climate/Orbital Agent

Mục tiêu:
- phản biện rủi ro,
- chặn kết luận quá lạc quan.

Dựa trên:
- eccentricity,
- period,
- mức bất định dữ liệu.

## 3.5 Archivist Agent

Mục tiêu:
- biến kết quả kỹ thuật thành mission language dễ dùng.

Dựa trên:
- recommendation final,
- session history,
- challenge state.

---

## 4) Quy trình ra quyết định của 1 turn (decision cycle)

Mỗi thao tác của người dùng kích hoạt một vòng:

1. **Observe**: đọc context hiện tại.
2. **Orient**: lọc/rank candidate theo constraints.
3. **Debate**: tạo votes theo vai trò.
4. **Decide**: chọn 1 recommendation chính.
5. **Act**: trả action khả thi cho UI.
6. **Reflect**: ghi lại log để vòng sau dùng.

Đây là OODA-loop biến thể cho sản phẩm khoa học tương tác.

---

## 5) Mapping với 4 thuộc tính Agentic AI

## 5.1 Goal-driven

- objective rõ trong context (`player_goal`).
- mọi response đều có `primary_recommendation.action`.

## 5.2 Planning

- recommendation luôn kéo theo option list (next steps).
- scan/filter/compare được xem là plan primitives.

## 5.3 Autonomy

- context đổi → council tự tái xếp hạng.
- không cần user phải hỏi từng bước mới phản hồi.

## 5.4 Feedback loop

- lưu recent actions,
- cập nhật discovery log,
- lần sau dùng lịch sử để tránh lặp gợi ý kém hiệu quả.

---

## 6) Khung “để code không vỡ trận”

## 6.1 Tách module theo ranh giới rõ ràng

- `council_schemas.py`: typing + dataclass + normalize input.
- `council_tools.py`: toàn bộ deterministic calculations.
- `council_orchestrator.py`: glue logic và policy.
- `server.py`: transport layer (HTTP/API only).

## 6.2 Quy tắc side-effect

- tools phải pure-function tối đa.
- orchestrator có thể chứa policy, nhưng không tự đọc file trực tiếp.
- data loading vẫn nằm ở server/service layer.

## 6.3 Quy tắc test

- test unit cho tools.
- test contract cho orchestrator.
- test smoke endpoint cho API.

---

## 7) Chất lượng đầu ra (response quality rubric)

Một response đạt chuẩn khi:

1. Có hành động cụ thể (`action` + `target_id`).
2. Có lý do gắn dữ liệu (`reason` + `evidence_fields`).
3. Có phản biện rủi ro (`stance=caution` khi cần).
4. Có fallback an toàn khi thiếu dữ liệu.
5. Có ngôn ngữ đủ rõ để người dùng hành động ngay.

---

## 8) Chống hallucination bằng kỹ thuật sản phẩm

Không chỉ nói “đừng hallucinate”, mà phải khóa bằng cơ chế:

- Whitelist fields được phép sử dụng.
- Schema validation trước khi trả response.
- If missing data => forced insufficient_evidence branch.
- UI hiển thị evidence ở cùng vùng với recommendation.

---

## 9) Kế hoạch nâng cấp theo 3 tầng trưởng thành

## Tier 1 — Deterministic Council (đã có thể demo)

- score/rank/vote hoàn toàn deterministic.
- mục tiêu: ổn định, minh bạch.

## Tier 2 — Hybrid reasoning

- giữ deterministic tools,
- thêm LLM để cải thiện wording/strategy abstraction,
- vẫn bắt buộc evidence mapping.

## Tier 3 — Adaptive mission intelligence

- học từ acceptance rate,
- tự tối ưu pattern scan,
- sinh challenge động theo profile phiên.

---

## 10) Kết luận tư duy triển khai

Nếu xem AI agent là “một model”, dự án sẽ dừng ở mức demo trò chuyện.
Nếu xem AI agent là “hệ thống ra quyết định có contract + evidence + loop”, dự án sẽ đi được tới production-lite.

Atlas Orrery nên theo hướng thứ hai: **decision engine có trách nhiệm**, nơi mỗi vòng tương tác đều tạo ra hành động tiếp theo rõ ràng, kiểm chứng được, và cải thiện được qua dữ liệu vận hành.

