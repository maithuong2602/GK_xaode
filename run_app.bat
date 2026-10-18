@echo off
chcp 65001 > nul
title PHẦN MỀM XÁO ĐỀ THI WORD / PDF GIỮ NGUYÊN ĐỊNH DẠNG (OOXML)
color 0B

echo =========================================================================
echo    PHẦN MỀM XÁO ĐỀ THI BẢO TOÀN ĐỊNH DẠNG GỐC DÀNH CHO GIÁO VIÊN
echo    Bảo toàn 100%% Bảng biểu, In đậm, Công thức, Section, Căn lề
echo =========================================================================
echo.

echo [1/3] Đang kiểm tra môi trường Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Máy tính chưa cài đặt Python hoặc chưa thêm Python vào biến môi trường PATH!
    echo Vui lòng tải và cài đặt Python từ https://www.python.org/downloads/ (nhớ tích chọn 'Add python.exe to PATH').
    pause
    exit /b 1
)

echo [2/3] Đang kiểm tra và tự động cập nhật các thư viện phụ thuộc...
python -m pip install -q -r requirements.txt

echo [3/3] Đang khởi động hệ thống máy chủ và mở giao diện trình duyệt...
start "" http://localhost:8000
python main.py
pause
