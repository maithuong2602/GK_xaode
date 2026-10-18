@echo off
chcp 65001 > nul
title TẠO ĐƯỜNG LINK CHIA SẺ TRỰC TUYẾN (CLOUDFLARE TUNNEL)
color 0A

echo =========================================================================
echo    CÔNG CỤ TẠO LINK TRỰC TUYẾN ĐỂ GỬI CHO NGƯỜI KHÁC DÙNG NGAY
echo    (Hoạt động an toàn qua Cloudflare Tunnel - Không cần cài đặt gì thêm)
echo =========================================================================
echo.

echo [*] Đang kiểm tra máy chủ ứng dụng...
powershell -Command "if (!(Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet)) { Write-Host '[!] Chu y: Ban can chay run_app.bat truoc de may chu hoat dong!' -ForegroundColor Yellow }"

echo.
echo [*] Đang khởi tạo đường link Internet bảo mật HTTPS...
echo [*] Vui lòng đợi trong giây lát, đường link sẽ xuất hiện bên dưới...
echo.
.\cloudflared.exe tunnel --url http://127.0.0.1:8000
pause
