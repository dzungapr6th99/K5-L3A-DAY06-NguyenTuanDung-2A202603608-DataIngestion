# DAY06 · Truy xuất tài liệu triển khai và đánh giá VLA cho robot gắp đặt bằng LeRobot

Mục tiêu là tìm đoạn hướng dẫn có đủ bằng chứng để trả lời câu hỏi tiếng Việt về quy trình VLA. Phạm vi gồm chuẩn bị dữ liệu và camera, cấu hình policy, chạy inference và đánh giá rollout. Ví dụ, một câu hỏi có thể yêu cầu tìm cách thiết lập inference trên máy riêng hoặc cách ánh xạ tên camera giữa dataset và robot.

## Corpus dự kiến

Dùng tài liệu kỹ thuật chính thức trong [LeRobot docs/source](https://github.com/huggingface/lerobot/tree/fe1c54594f6ba275fccf210b9f7b11f0e2324b89/docs/source), cố định tại commit `fe1c54594f6ba275fccf210b9f7b11f0e2324b89`. Repo công bố [giấy phép Apache-2.0](https://github.com/huggingface/lerobot/blob/fe1c54594f6ba275fccf210b9f7b11f0e2324b89/LICENSE). Corpus dự kiến chỉ lấy văn bản hướng dẫn, bỏ ảnh, video và nội dung nhúng từ bên ngoài. Ghi nguồn, quyền và ngày lấy theo từng tài liệu trong manifest.

| Nhóm | Tài liệu để sàng lọc |
|---|---|
| Policy và huấn luyện | `smolvla`, `pi0`, `pi05`, `pi0fast`, `groot`, `xvla`, `fineart_vla`, `lingbot_vla_v2`, `peft_training`, `multi_gpu_training` |
| Triển khai và phần cứng | `inference`, `remote_inference`, `rtc`, `rename_map`, `action_representations`, `cameras`, `so101`, `so100`, `hardware_guide`, `integrate_hardware`, `il_robots` |
| Dữ liệu | `lerobot-dataset-v3`, `porting_datasets_v3`, `training_dataset_streaming`, `using_dataset_tools`, `streaming_video_encoding`, `video_encoding_parameters`, `annotation_pipeline`, `hil_data_collection` |
| Đánh giá | `simulation`, `libero`, `libero_plus`, `robotwin`, `vlabench`, `adding_benchmarks`, `metaworld`, `robocasa` |

Đã kiểm tra 37 tệp MDX ứng viên đều dài hơn 1.500 ký tự sau khi gộp khoảng trắng. Ở checkpoint 1, đọc và chọn tối thiểu 30 đơn vị độc lập có nội dung hữu ích, bỏ tài liệu trùng hoặc lạc phạm vi, rồi chốt số lượng thực trong manifest. Dùng tên tệp và heading để truy vết từng đoạn. Trường `stage` có thể lọc theo nhóm quy trình khi người hỏi đã nêu phạm vi.

Bài thực hành đánh giá truy xuất tài liệu với Ollama và Milvus. Những câu hỏi về chạy robot được kiểm chứng bằng evidence trong tài liệu.

## Corpus đã lấy

[Manifest](data/manifest.json) ghi 32 tài liệu chính thức theo 5 nhóm: SmolVLA, GR00T, OpenVLA, π0/openpi và NVIDIA Agent Skills. Có 31 tài liệu đạt ngưỡng 1.500 ký tự theo phép đếm đã ghi. Tài liệu ALOHA mô phỏng ngắn hơn được giữ làm nguồn bổ sung. Kiểm tra mức liên quan của từng nguồn khi chốt corpus cho bài.

Nạp bản chia đoạn cố định vào Milvus từ PowerShell tại gốc repo:

```powershell
& .\.venv\Scripts\python.exe -m starter.src.ingest_vla
```

Collection dùng tiền tố `day06_vla_fixed_`, index FLAT/COSINE và trường lọc `category`. Mỗi chunk lưu URL cố định, ID tài liệu, trang logic và vị trí bắt đầu trong văn bản chuẩn hóa. Nạp lại cùng manifest dùng cùng ID chunk. Đây là dữ liệu để thử truy xuất trước khi chốt bộ câu hỏi và các cấu hình benchmark.
