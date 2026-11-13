# Chạy DAY06 từ Windows

Mở PowerShell tại thư mục gốc của repo. Tạo môi trường Python riêng và cài SDK:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ollama và Milvus chạy trên Jetson. Lệnh checkpoint dùng mặc định `http://192.168.1.246:11434` và `http://192.168.1.246:19530`. Nếu PowerShell còn giữ địa chỉ tunnel cũ, đặt lại địa chỉ trong cửa sổ hiện tại:

```powershell
$py = ".\.venv\Scripts\python.exe"
$env:OLLAMA_URL = "http://192.168.1.246:11434"
$env:MILVUS_URI = "http://192.168.1.246:19530"
```

Mở [danh sách model Ollama](http://192.168.1.246:11434/api/tags) hoặc [Milvus WebUI](http://192.168.1.246:9091/webui/). Attu dùng địa chỉ `192.168.1.246:19530`.

## Chạy theo từng checkpoint

```powershell
& $py -m starter.checkpoint
```

| Mốc | Việc cần làm |
|---|---|
| 0:25 | Chạy lệnh kiểm tra trên, chọn nguồn theo [đề tài VLA](TOPIC-VLA.md), đọc và lập manifest. |
| 1:00 | Điền [file câu hỏi](benchmark/questions.json), chốt split dev/test và đối chiếu evidence từ tài liệu VLA. |
| 1:50 | Chuẩn hóa văn bản, lưu metadata theo nguồn và xuất mẫu chunk A/B. |
| 2:00 | Nghỉ. |
| 2:40 | Tạo embedding, nạp Milvus, kiểm tra nạp lại và truy xuất top-3 cho A/B/C. |
| 3:30 | Đọc trace, tính Hit@1 và Evidence Hit@3, chấm thủ công coherence, metadata và grounding. |
| 4:00 | Hoàn thiện báo cáo và đối chiếu [checklist](SUBMISSION.md). |

Sau khi điền câu hỏi, chạy từ gốc repo:

```powershell
& $py -m starter.src.benchmark_vla --validate
& $py -m starter.src.benchmark_vla
```
