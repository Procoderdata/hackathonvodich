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

# Cách chúng ta tiếp cận để tích hợp AI Agents vào Atlas Orrery

Trong các hệ thống mô phỏng khoa học, thách thức lớn nhất không chỉ là hiển thị dữ liệu, mà là biến dữ liệu thành quyết định có thể hành động. Atlas Orrery vốn đã có nền tảng trực quan 3D tốt, có dữ liệu exoplanet, có API và có luồng tương tác mission-like. Vấn đề còn thiếu là “bộ não điều phối”: làm sao để mỗi thao tác của người dùng không chỉ tạo hiệu ứng giao diện, mà còn tạo ra một chuỗi suy luận có mục tiêu, có phản biện, có bằng chứng, và có khả năng học dần theo phiên sử dụng.

Vì vậy, cách tiếp cận của chúng ta không đi theo hướng gắn một chatbot tổng quát vào sản phẩm. Thay vào đó, chúng ta xây dựng một hệ “AI Council” gồm nhiều agent chuyên trách, nơi mỗi agent có vai trò rõ ràng, dùng cùng một nguồn dữ liệu chuẩn hóa, và hội tụ thành một quyết định cuối cùng thông qua orchestrator. Mục tiêu không phải tạo cảm giác “AI nói chuyện hay”, mà là tạo trải nghiệm “AI hỗ trợ ra quyết định khoa học”. Đây cũng là điểm quan trọng nếu muốn bám sát chủ đề Agentic AI: agents phải có mục tiêu, có kế hoạch, có tính tự chủ và có vòng lặp phản hồi.

## 1. Triết lý thiết kế: deterministic-first, agentic-second

Nguyên tắc trung tâm trong kiến trúc là tách biệt phần nào phải chính xác tuyệt đối và phần nào có thể linh hoạt theo ngữ cảnh.

- Phần deterministic (bắt buộc):
  - Tính toán quỹ đạo.
  - Lọc catalog theo điều kiện người dùng.
  - Chấm điểm baseline habitability.
  - Kiểm tra điều kiện challenge/pass-fail.

- Phần agentic (linh hoạt):
  - Đề xuất mục tiêu ưu tiên kế tiếp.
  - Tranh luận các giả thuyết (support/caution).
  - Giải thích lý do theo ngôn ngữ dễ hiểu.
  - Tạo narrative mission để tăng tương tác.

Cách phân lớp này giúp tránh lỗi phổ biến của các sản phẩm AI demo: model “bịa” dữ liệu khoa học. Ở Atlas Orrery, AI chỉ được quyền suy luận trong biên của dữ liệu đã có, và phải chỉ ra bằng chứng tương ứng.

## 2. Mô hình Council: đa tác nhân thay vì một trợ lý chung

Chúng ta chia hệ thống thành 4 agent chính:

1. **Navigator Agent**
   - Nhiệm vụ: chọn mục tiêu kế tiếp.
   - Tiêu chí: mức ưu tiên khoa học, độ hoàn chỉnh dữ liệu, độ mới của khám phá.

2. **Astrobiologist Agent**
   - Nhiệm vụ: đánh giá khả năng ở được (habitability likelihood).
   - Dựa trên: nhiệt độ cân bằng, bán kính hành tinh, bức xạ nhận được, môi trường sao chủ.

3. **Climate/Orbital Agent**
   - Nhiệm vụ: phản biện, cảnh báo rủi ro, chỉ ra mức độ bất định.
   - Dựa trên: eccentricity, period, tính ổn định quỹ đạo, dữ liệu còn thiếu.

4. **Archivist Agent**
   - Nhiệm vụ: chuyển kết quả thành discovery log, mission summary, và hành động kế tiếp rõ ràng cho người dùng.

Phía trên 4 agent là **Council Orchestrator**, chịu trách nhiệm:
- nhận context từ frontend,
- gọi tools nội bộ,
- phân phối context cho từng agent,
- hợp nhất kết quả và giải quyết xung đột,
- trả về một payload chuẩn hóa cho UI.

## 3. Cấu trúc dữ liệu đầu vào/đầu ra

### 3.1 Mission context packet (input)

Mỗi lượt người dùng thao tác (đổi filter, bắt đầu scan, chọn target, mở planet modal), frontend tạo một packet ngắn gọn gồm:

- mode hiện tại (sandbox/challenge/discovery),
- mục tiêu người dùng,
- target đang chọn,
- filter đang bật,
- trạng thái mô phỏng thời gian,
- challenge state,
- vài hành động gần nhất.

Điểm quan trọng: chỉ gửi context cần thiết; không gửi toàn bộ dataset lên model.

### 3.2 Council response package (output)

Backend trả về payload có cấu trúc ổn định:

- `mission_status`
- `headline`
- `primary_recommendation` (action + target + reason)
- `council_votes` (agent, stance, confidence, message, evidence_fields)
- `player_options`
- `discovery_log_entry`

Với format này, frontend có thể render trực tiếp thành card, console, highlight scene, hoặc button tương tác mà không phải parse text tự do.

## 4. Luồng xử lý end-to-end

1. Người dùng bấm scan hoặc chỉnh filter trên Command Center.
2. Frontend gửi context tới endpoint council.
3. Orchestrator lấy dữ liệu đã qua chuẩn hóa từ tool layer.
4. Navigator đưa mục tiêu ưu tiên.
5. Astrobiologist ủng hộ/đánh giá xác suất.
6. Climate phản biện/cảnh báo.
7. Archivist đóng gói narrative cho người dùng.
8. Orchestrator hợp nhất và trả về recommendation cuối.
9. Frontend hiển thị kết quả + cho phép hành động tiếp theo.
10. Hành động mới lại tạo context mới: hình thành feedback loop.

Điểm khác biệt ở đây là mỗi vòng lặp đều đóng được thành một “mission decision cycle”, thay vì chỉ là hỏi-đáp.

## 5. Kế hoạch triển khai theo pha

### Phase 1: Foundation (MVP)

- Tạo endpoint council deterministic.
- Trả recommendation + votes + evidence fields.
- Hiển thị kết quả trong console panel.

Mục tiêu: chứng minh được vòng lặp agentic cơ bản chạy ổn định.

### Phase 2: Multi-agent depth

- Tách logic rõ cho Navigator/Astro/Climate.
- Thêm conflict resolution strategy.
- Bổ sung confidence calibration.

Mục tiêu: tạo cảm giác “hội đồng tranh luận thật”, không phải random text.

### Phase 3: Challenge integration

- Gắn challenge engine deterministic.
- Agent dùng challenge state để cá nhân hóa gợi ý.
- Cho phép hint theo tiến độ thay vì hint cố định.

Mục tiêu: tăng replayability và giá trị học tập.

### Phase 4: Learning & observability

- Thêm telemetry: recommendation accepted rate, step depth, time-to-action.
- Thêm memory ngắn hạn theo session.
- Tối ưu prompt/policy theo dữ liệu sử dụng thực.

Mục tiêu: hệ thống tự cải thiện được qua dữ liệu vận hành.

## 6. Guardrails để đảm bảo tính khoa học

Một hệ AI Agents cho khoa học không thể thiếu cơ chế an toàn:

1. Mọi kết luận phải gắn với `evidence_fields`.
2. Nếu dữ liệu thiếu thì bắt buộc trả `insufficient_evidence`.
3. Không cho phép agent tự sinh thông số vật lý không có trong dataset.
4. Có fallback deterministic nếu model timeout/lỗi.
5. Luôn tách “fact” và “interpretation” trong UI.

Nhờ vậy, sản phẩm giữ được tính tin cậy khi đưa vào môi trường giáo dục hoặc trình diễn chuyên môn.

## 7. Vì sao cách tiếp cận này phù hợp chủ đề Agentic AI

Chủ đề Agentic AI yêu cầu hệ thống không chỉ phản hồi mà phải chủ động định hướng hành động. Cách chúng ta làm đáp ứng đầy đủ:

- **Goal-driven**: mọi turn đều nhắm tới một objective mission cụ thể.
- **Planning**: mỗi recommendation kéo theo chuỗi bước tiếp theo.
- **Autonomy**: council tự điều chỉnh đề xuất theo trạng thái mới.
- **Feedback loop**: kết quả hành động vòng trước ảnh hưởng quyết định vòng sau.

Nói cách khác, chúng ta đang chuyển AI từ “công cụ trả lời” thành “hệ thống tác nhân điều phối quyết định”.

## 8. Kết luận

Hướng kết hợp AI Agents cho Atlas Orrery không phải là thêm lớp hội thoại lên giao diện hiện có, mà là xây dựng một kiến trúc ra quyết định có thể kiểm chứng. Kiến trúc đó gồm orchestrator, multi-agent chuyên trách, deterministic tools, contract dữ liệu rõ ràng, và vòng lặp phản hồi liên tục.

Nếu triển khai đúng theo lộ trình, hệ thống sẽ đạt 3 mục tiêu cùng lúc:

1. Trải nghiệm người dùng hấp dẫn hơn (có mục tiêu, có nhịp mission).
2. Giá trị khoa học cao hơn (có bằng chứng, có phản biện, có mức bất định).
3. Giá trị trình diễn/hackathon cao hơn (thể hiện rõ bản chất Agentic AI bằng hành vi thực, không chỉ lời nói).

Đó là hướng đi vừa thực dụng để build nhanh, vừa đủ chiều sâu để cạnh tranh ở các sân chơi đòi hỏi cả kỹ thuật lẫn tác động thực tế.
