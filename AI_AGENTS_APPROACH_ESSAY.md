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
