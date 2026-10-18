# 📚 Phần Mềm Xáo Đề Thi Word & PDF Bảo Toàn Định Dạng Gốc (OOXML Exam Shuffler)

Ứng dụng web chuyên nghiệp dành cho Giáo viên và Nhà trường giúp xáo đề thi trắc nghiệm từ file Microsoft Word (`.docx`) và PDF với cam kết **Bảo toàn 100% định dạng gốc**: giữ nguyên vẹn bảng biểu, in đậm, in nghiêng, công thức, lề trang, section và font chữ.

---

## 🌟 Tính Năng Nổi Bật

1. **Bảo Toàn Định Dạng OOXML Tuyệt Đối:**
   - Di chuyển nguyên khối các thẻ XML gốc của từng câu hỏi và phương án.
   - Không bị vỡ bảng biểu, không mất style in đậm, in nghiêng hay kích thước chữ.
2. **Dàn Trang Tự Nhiên & Tiết Kiệm Giấy In:**
   - Dòng chữ chảy liên tục theo chuẩn tự nhiên của file gốc, loại bỏ hoàn toàn hiện tượng khoảng trắng thừa lớn ở cuối trang.
3. **Theo Dõi Vị Trí Câu Hỏi Gốc Thông Minh:**
   - Hiển thị rõ ràng vị trí câu hỏi mới là câu số mấy so với file đề gốc (ví dụ: `Câu 1 (Gốc: Câu 17)`).
   - Tích hợp **Ma trận vị trí tổng hợp**: Tra cứu chéo tức thì một câu gốc đang nằm ở vị trí câu số mấy trong từng mã đề (Mã 101, 102, 103, 104...).
4. **Hỗ Trợ 2 Bản Xuất Độc Lập:**
   - **👨‍🎓 Bản học sinh (Chỉ đề thi):** Đề thi sạch sẽ, các câu hỏi đánh số từ 1 đến N, tự động xóa bỏ bảng đáp án / hướng dẫn chấm ở cuối đề thi, sẵn sàng in phát cho học sinh làm bài mà không sợ lộ đáp án.
   - **📑 Bản giáo viên (Kèm đáp án & đối chiếu):** Có chú thích vị trí câu gốc ngay tại câu hỏi, tự động cập nhật bảng hướng dẫn chấm theo đáp án mới và bổ sung bảng đối chiếu chi tiết ở trang cuối.
5. **Xuất Đa Dạng Định Dạng:**
   - Tải nhanh trọn bộ gói nén `.ZIP` (chứa riêng 2 thư mục cho Học sinh và Giáo viên).
   - Xuất file Ma trận ánh xạ và tổng hợp điểm bằng Excel (`.xlsx`).
   - Xuất file Bảng đáp án chấm thi riêng bằng Word (`.docx`).

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### Cách 1: Khởi Chạy Nhanh 1-Click (Dành cho Giáo viên trên Windows)

1. Tải toàn bộ mã nguồn về máy tính (bằng cách chọn **Code** -> **Download ZIP** trên GitHub và giải nén).
2. Nhấp đúp chuột vào tệp tin **`run_app.bat`**.
3. Hệ thống sẽ tự động kiểm tra môi trường, cài đặt các thư viện cần thiết và tự động mở trình duyệt web tại địa chỉ: `http://localhost:8000`.

---

### Cách 2: Khởi Chạy Bằng Dòng Lệnh (Command Line)

#### Bước 1: Clone mã nguồn từ GitHub
```bash
git clone https://github.com/maithuong2602/GK_xaode.git
cd GK_xaode
```

#### Bước 2: Cài đặt các thư viện phụ thuộc
Đảm bảo máy tính đã cài đặt Python 3.9 trở lên, sau đó chạy lệnh:
```bash
pip install -r requirements.txt
```

#### Bước 3: Khởi động máy chủ
```bash
python main.py
```
Mở trình duyệt web và truy cập: **`http://localhost:8000`** để bắt đầu sử dụng.

---

## 🛠️ Quy Trình 6 Bước Xáo Đề Thi

1. **Bước 1: Nạp đề thi:** Tải lên file Word (`.docx`) hoặc chọn file mẫu có sẵn.
2. **Bước 2: Phân tích cấu trúc:** Hệ thống tự động nhận diện số câu hỏi, dạng trắc nghiệm, đúng/sai, tự luận và các bảng đáp án.
3. **Bước 3: Kiểm tra câu hỏi & Quản lý đáp án:** Khóa câu không muốn xáo (🔒), chọn đáp án đúng hoặc dán nhanh chuỗi đáp án (Paste nhanh).
4. **Bước 4: Cấu hình xáo đề:** Chọn số lượng mã đề cần sinh, mã số bắt đầu (ví dụ: 101, 102...), cấu hình xáo theo từng phần (Section).
5. **Bước 5: Xem trước & Đối chiếu:** Kiểm tra ma trận chuyển đổi câu hỏi giữa các mã đề, chuyển đổi chế độ xem Bản học sinh / Bản giáo viên.
6. **Bước 6: Tải xuống:** Tùy chọn tải gói ZIP trọn bộ, tải lẻ từng mã đề thi, file ma trận Excel hoặc bảng đáp án Word.

---

## 🧪 Chạy Kiểm Thử Tự Động (Automated Testing)

Dự án đi kèm bộ 14 bài kiểm tra tự động toàn diện:
```bash
python -m unittest tests/test_shuffler.py
```

---

## 📄 Giấy Phép & Tác Quyền

Dự án được phát triển nhằm hỗ trợ quý Thầy Cô giáo và các nhà trường trong công tác kiểm tra, đánh giá học sinh một cách nhanh chóng, công bằng và chính xác.
Mọi đóng góp, phản hồi hoặc yêu cầu tính năng mới xin vui lòng gửi qua mục **Issues** trên GitHub.
