# Báo cáo cá nhân · DAY06 Data Ingestion Engineering

**Nguyễn Tuấn Dũng · 2A202603608 · L3A**

## Dữ liệu và pipeline

Đề tài là truy xuất bằng chứng từ tài liệu triển khai và đánh giá VLA cho robot gắp đặt. Corpus gồm 32 tài liệu tiếng Anh từ LeRobot, NVIDIA Isaac GR00T, OpenVLA, Physical Intelligence openpi và NVIDIA Agent Skills. [Manifest](../../data/manifest.json) ghi URL ghim commit, hash, đường dẫn và giấy phép của từng nguồn. Mỗi tệp là một trang logic. Có 31 đơn vị đạt 1.500 ký tự sau khi chuẩn hóa và một nguồn ALOHA mô phỏng ngắn được giữ bổ sung.

Pipeline kiểm tra hash, chuẩn hóa Unicode NFC, bỏ bình luận HTML và gộp khoảng trắng. Cú pháp Markdown, ví dụ lệnh và một số thẻ MDX còn trong chunk. Mỗi chunk giữ ID tài liệu, URL, trang logic, vị trí ký tự và `category`. Category lấy từ nhóm nguồn trong manifest và cho phép người hỏi giới hạn phạm vi theo hệ sinh thái tài liệu.

Ollama 0.40.16 chạy `qwen3-embedding:0.6b` (ID `ac6da0dfba84`, 1.024 chiều) trên Jetson. Câu hỏi có tiền tố hướng dẫn truy xuất. Milvus Standalone 3.0.5 dùng FLAT/COSINE để tìm kiếm chính xác trên CPU. Chi phí gọi API là 0. Lượt benchmark hiện tại không ghi thời gian ingest, token hoặc điện năng. Tái lập bằng `python -m starter.src.benchmark_vla --validate` rồi `python -m starter.src.benchmark_vla`. [Setup](../../SETUP-DAY06.md)

## Cấu hình và benchmark

- **A** dùng cửa sổ 750 ký tự, chồng lấn 75 ký tự trên toàn tài liệu.
- **B** tách tại heading Markdown, rồi áp dụng cùng cửa sổ bên trong từng mục.
- **C** dùng lại collection B. Nếu câu hỏi có phạm vi, truy vấn thêm filter `category`.

Bộ câu hỏi gồm 15 dev và 5 test, có hai câu dev và một câu test kèm filter. Mỗi đáp án có đoạn trích được kiểm tra tồn tại trong tài liệu. Script chấm hit khi chunk khớp ID nguồn, trang và chứa đủ đoạn trích sau chuẩn hóa. Chọn B cho vòng thử tiếp theo dựa trên Evidence Hit@3 dev, sau đó dùng Hit@1 dev để phá hòa và ưu tiên cấu hình ít điều kiện truy vấn hơn khi điểm bằng nhau. Quy tắc này được trình bày sau lượt chạy, nên kết luận chọn B có tính hồi cứu.

## Kết quả

| Cấu hình | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Số chunk | Tổng ký tự | Độ dài min/trung vị/max |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 4/15 | 6/15 | 1/5 | 1/5 | 577 | 422.809 | 77 / 750 / 750 |
| B | 5/15 | 6/15 | 3/5 | 3/5 | 885 | 402.969 | 3 / 457 / 750 |
| C | 5/15 | 6/15 | 3/5 | 3/5 | 885, dùng chung B | 402.969 | 3 / 457 / 750 |

### Audit coherence

Dùng cùng vị trí đầu tài liệu của 10 nguồn đầu theo thứ tự manifest. Chấm 0 cho chunk chỉ có tiêu đề hoặc thiếu ý chính, 1 cho đoạn hiểu được một phần và 2 cho đoạn giữ ý đủ ngữ cảnh. C có cùng mẫu và điểm với B.

| Nguồn | A | B | Lý do |
|---|---:|---:|---|
| SmolVLA | 1 | 2 | A cắt giữa hướng dẫn cài. B giữ phần giới thiệu và mô tả đầu vào cùng đầu ra. |
| LeRobotDataset v3 | 1 | 1 | Cùng giữ định nghĩa và cắt giữa phần giới thiệu nội dung tiếp theo. |
| Remote inference | 1 | 1 | Cùng giữ lý do dùng remote inference và cắt giữa danh sách. |
| RTC | 1 | 1 | Cùng giải thích vấn đề khi chạy theo chunk và cắt giữa ý. |
| Rename map | 1 | 2 | A cắt giữa ví dụ. B giữ mục đích và phạm vi của ánh xạ. |
| SO-101 | 1 | 1 | A cắt đầu mục kế tiếp. B giữ phần giới thiệu lắp ráp ngắn, với ít hướng dẫn cụ thể. |
| GR00T README | 1 | 1 | Đầu trang chủ yếu là markup, tiêu đề và liên kết. |
| GR00T FAQ | 1 | 0 | A giữ một phần FAQ. B chỉ giữ tiêu đề ở vị trí này. |
| GR00T data config | 1 | 0 | A giữ một phần giải thích cấu hình. B chỉ có tiêu đề. |
| GR00T data preparation | 1 | 0 | A giữ phần mở đầu về chuẩn bị dữ liệu. B chỉ có tiêu đề. |
| **Trung bình** | **1,0/2** | **0,9/2** | 10 vị trí mỗi cấu hình. |

### Audit metadata và grounding

Đối chiếu ID, URL, trang, category, vị trí và nội dung từng chunk top 3 test với manifest và văn bản tạo lại. Mỗi cấu hình khớp **15/15**. C áp dụng filter đúng ở **2/2 dev** và **1/1 test**. Với A và B, mức tuân thủ khi áp dụng filter là N/A. Trên ba câu có phạm vi, top 3 của B vốn đã cùng category và có cùng thứ tự ID như C.

| Câu test | A | B | C | Nhận xét từ top 3 |
|---|---:|---:|---:|---|
| q16 | 0 | 1 | 1 | A lấy tài liệu GR00T và LeRobot. B/C thấy ví dụ gọi openpi trả chuỗi hành động nhưng thiếu shape. |
| q17 | 0 | 2 | 2 | A tìm đúng README nhưng trả đoạn dữ liệu hoặc fine-tune. B/C đưa ví dụ 7-DoF và khóa unnormalization lên hạng 1. |
| q18 | 1 | 2 | 2 | A có thông tin từng phần về replay và độ dài dự đoán. B/C trả đoạn nêu quan hệ giữa thực thi, lập kế hoạch lại và giới hạn horizon. |
| q19 | 0 | 0 | 0 | B/C tìm đúng tài liệu Jetson memory-audit nhưng lấy phần giới thiệu, mục đích hoặc lưu ý sandbox. Đoạn mô tả bộ nhớ sau khi dừng CUDA nằm ngoài top 3. |
| q20 | 2 | 2 | 2 | Cả ba lấy đủ thời gian, số bước và GPU của ví dụ SmolVLA. |

Grounding A có **3/1/1** câu ở mức 0/1/2, trung bình **0,6/2**. B và C đều có **1/1/3**, trung bình **1,4/2**. Nhãn do Codex đọc trace theo thang điểm của đề, sau khi benchmark đã chạy. Học viên nên xác nhận nhãn trước khi nộp. [Trace](../../results/traces.json) · [Điểm tự động](../../results/metrics.json)

## Phân tích và kết luận

A→B tăng Hit@1 dev từ 4 lên 5 câu và giữ Evidence Hit@3 dev ở 6 câu. Test tăng từ 1 lên 3 câu có evidence. B tạo thêm 308 chunk dù tổng số ký tự giảm 19.840. Nhiều chunk ngắn làm tăng số vector và có thể đưa tiêu đề rời vào index. q17 và q18 là ví dụ B đưa đúng mục lên đầu khi A chỉ tìm đúng tài liệu hoặc đúng chủ đề.

B→C giữ nguyên kết quả trên cả ba câu có filter. Bộ lọc có tác dụng ràng buộc phạm vi theo metadata, còn lợi ích đối với chất lượng truy xuất chưa xuất hiện trong lượt này. q19 minh họa trường hợp đúng nhóm và đúng tài liệu nhưng sai đoạn. q16 cho thấy cụm từ action chunk dễ dẫn đến các tài liệu cùng thuật ngữ dù câu hỏi cần shape từ một API cụ thể.

Tập test chỉ có năm câu, một số chủ đề và nguồn xuất hiện ở cả dev và test, và điểm tự động dựa trên khớp đoạn trích. Lần tiếp theo có thể giữ heading làm ngữ cảnh cho chunk, ghép các mục chỉ có tiêu đề và kiểm tra trên bộ test mới tách theo tài liệu. Codex hỗ trợ viết mã, chuẩn bị corpus, câu hỏi, phân tích trace và soạn báo cáo. Số liệu lấy từ artifact benchmark thực tế và thống kê tái tạo từ corpus.
