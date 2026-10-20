# AdsChecking

## Tải ứng dụng Windows

Bản desktop dành cho Windows 10/11 x64, không cần cài Python.

**Trạng thái kiểm tra ngày 20/10/2026:** repository chưa có release công khai. Link tải trực tiếp hiện trả về “Not Found”; maintainer cần phát hành theo hướng dẫn bên dưới trước khi người dùng tải được EXE từ Releases.

1. Mở [GitHub Releases](https://github.com/AzuraDev202/AdsChecking/releases).
2. Khi đã có release, chọn **AdsChecking-windows-x64.zip** trong mục **Assets**. **Code → Download ZIP** và **Source code (zip)** chỉ chứa mã nguồn, không có app EXE đã đóng gói.
3. Giải nén toàn bộ ZIP rồi mở `AdsChecking/AdsChecking.exe`. Giữ nguyên thư mục `_internal` bên cạnh EXE.
4. Chuẩn bị proxy HTTP/HTTPS, OAuth Client ID, Client secret và Google Ads developer token của bạn. Ứng dụng không kèm thông tin đăng nhập.

Bản build chưa ký số; Windows có thể hiển thị cảnh báo nhà phát hành chưa xác định. Kiểm tra nguồn tải và đối chiếu SHA-256 với `SHA256SUMS.txt` trên cùng release bằng `Get-FileHash .\AdsChecking-windows-x64.zip -Algorithm SHA256`.

### Nếu link tải hiện “Not Found”

Đây là lỗi tải file trên GitHub, ứng dụng chưa được khởi chạy. Link `/releases/latest/download/...` chỉ hoạt động sau khi có release ổn định đã xuất bản và đính kèm đúng file `AdsChecking-windows-x64.zip`; commit hoặc push mã nguồn chưa tạo ra file tải.

- Mở [danh sách Releases](https://github.com/AzuraDev202/AdsChecking/releases) và tải ZIP trong **Assets**. Nếu danh sách trống, chưa có bản phát hành để tải; đổi đường dẫn hoặc tải lại trang không tạo ra file ZIP.
- Nếu repository chuyển sang riêng tư, cần đăng nhập GitHub bằng tài khoản có quyền truy cập. Kiểm tra cập nhật tự động trong app dùng API công khai nên cần repository và release công khai.
- Sau khi tải, giải nén toàn bộ trước khi mở EXE; không chạy EXE trực tiếp từ cửa sổ xem nội dung ZIP.

### Đóng gói và phát hành

```powershell
.venv/Scripts/python -m pip install -r requirements-build.txt
./build-desktop.ps1
```

Script tạo `dist/AdsChecking-windows-x64.zip` và `dist/SHA256SUMS.txt`, đồng thời kiểm tra EXE khởi động và trạng thái khóa đăng nhập ban đầu. Chỉ mã ứng dụng cùng dependency được đóng gói; không thu thập `.env`, dữ liệu phiên hay thư mục kiểm thử.

Workflow [Windows desktop](.github/workflows/desktop-release.yml) chạy kiểm thử, build và kiểm tra EXE trên Windows. Sau khi đưa thay đổi workflow và README lên GitHub, maintainer có quyền ghi thực hiện:

1. Vào **Actions → Windows desktop → Run workflow**, chọn nhánh chứa mã nguồn cần phát hành.
2. Bật **Publish the Windows ZIP and checksum to GitHub Releases** (`publish = true`), rồi chạy workflow. Nếu không bật, workflow chỉ tạo artifact kiểm tra; tải artifact trong trang lần chạy Actions (cần đăng nhập GitHub), giải nén artifact để lấy ZIP ứng dụng bên trong.
3. Chờ cả job **build** và **release** hoàn tất. Workflow lấy phiên bản từ `APP_VERSION`, tạo tag tương ứng tại commit được build, tải ZIP và checksum vào release nháp rồi mới công khai thành bản mới nhất. Phiên bản phải chưa có release; nếu đã phát hành, tăng `APP_VERSION` trước khi chạy.
4. Kiểm tra [Releases](https://github.com/AzuraDev202/AdsChecking/releases) có đủ `AdsChecking-windows-x64.zip` và `SHA256SUMS.txt`. Job release tải lại ZIP bằng URL công khai và đối chiếu checksum. Khi đã xác minh thành công, cập nhật dòng trạng thái tải ở đầu README.

Sau khi phát hành thành công, đường dẫn tải ổn định là `https://github.com/AzuraDev202/AdsChecking/releases/latest/download/AdsChecking-windows-x64.zip`. Chỉ dùng đường dẫn này làm link tải chính sau khi kiểm tra thực tế thành công.

Maintainer cũng có thể push tag khớp phiên bản (ví dụ `v0.1.0`) để tự chạy cùng quy trình. Build tại máy không tự xuất bản release; file tại `dist/` phải được tải lên GitHub Releases mới có link tải công khai.

### Thông báo cập nhật desktop

App kiểm tra GitHub Releases khi mở và mỗi giờ khi đang chạy. Nút **Kiểm tra cập nhật** cho phép thử lại thủ công. Khi có bản ổn định mới hơn kèm ZIP Windows sẵn sàng, app hiển thị phiên bản và nút **Tải bản mới**. Lỗi mạng không chặn thao tác Google Ads.

Kiểm tra chạy nền qua HTTPS trực tiếp đến API GitHub công khai, không gửi thông tin Google hay proxy đã nhập. Nút tải mở trình duyệt hệ thống. Sau khi kiểm tra SHA-256, đóng app rồi giải nén ZIP vào thư mục mới và mở EXE trong đó.

Trước mỗi release, cập nhật `APP_VERSION` trong `adschecking/updates.py` và dùng tag tương ứng dạng `v1.2.3`. CI từ chối tag không khớp phiên bản. Link tải trực tiếp cần một release công khai có asset `AdsChecking-windows-x64.zip`; app không tự ghi đè EXE.

## Giao diện desktop

Giao diện chia hai vùng: thiết lập proxy và đăng nhập ở bên trái, chọn MCC và cây tài khoản ở bên phải. Trạng thái kết nối và hướng dẫn bước tiếp theo cập nhật theo phiên; thanh tiến trình chạy trong lúc xử lý. Khu vực cập nhật phiên bản nằm riêng ở cuối cửa sổ.

Sau khi cài dependency theo phần dưới, chạy `./start-desktop.ps1` trong PowerShell hoặc `.venv/Scripts/python -m adschecking.desktop`.

1. **Nhập và kiểm tra proxy trước tiên.** Các ô Google và nút kết nối bị khóa đến khi proxy được xác minh. Nhập URL `http://user:password@host:port` hoặc proxy HTTPS; trường này được che để bảo vệ mật khẩu.
2. Nhập OAuth Client ID, Client secret và developer token trực tiếp trên desktop; không cần thiết lập biến môi trường cho chế độ desktop.
3. Bấm **Đăng nhập Google**, hoàn tất cấp quyền trên trình duyệt hệ thống. OAuth client loại Web phải đăng ký redirect URI `http://127.0.0.1:8000/oauth/callback`. Không chạy backend cổng 8000 cùng lúc.
4. Bấm **Tải tài khoản truy cập**, chọn hoặc nhập MCC, bấm **Xác minh MCC**, rồi **Tải tài khoản con**.

Đổi proxy sẽ xóa phiên kết nối cũ và yêu cầu kiểm tra lại. Các thao tác mạng chạy nền để giao diện vẫn phản hồi. Có nút hủy/ngắt kết nối OAuth. Chế độ desktop lưu token mã hóa trong thư mục tạm theo phiên; khóa nằm trong bộ nhớ, đóng ứng dụng sẽ xóa dữ liệu phiên. Không có lưu mật khẩu hoặc tự đăng nhập lại sau khi đóng. Nếu ứng dụng bị tắt cưỡng bức, có thể còn tệp tạm đã mã hóa nhưng khóa phiên không được lưu.

Proxy desktop áp dụng cho kết nối backend đến Google. **Trình duyệt đăng nhập dùng cấu hình mạng riêng**: cấu hình proxy trình duyệt nếu cần và cho phép callback `127.0.0.1` đi trực tiếp. Kiểm tra proxy thành công chưa chứng minh tài khoản có quyền Google Ads; thao tác xác minh MCC kiểm tra quyền đó. Chưa hỗ trợ SOCKS5. Bản EXE portable được đóng gói theo hướng dẫn ở trên.

## Kết nối tài khoản quản lý Google Ads và proxy

Bản đầu tiên là backend FastAPI cho một người vận hành, một kết nối OAuth và một MCC được chọn. Có giao diện API tương tác tại `http://127.0.0.1:8000/docs`; chưa có dashboard React. Không tạo tài khoản con mới hoặc gửi lời mời liên kết MCC: chức năng hiện tại đọc tài khoản đã được cấp quyền và cây tài khoản con hiện có.

### Cài đặt

Yêu cầu Python 3.12 trở lên. Trong PowerShell tại thư mục dự án:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

Thiết lập biến môi trường trong phiên PowerShell chạy ứng dụng (không gửi thông tin thật vào chat hoặc commit):

```powershell
$env:GOOGLE_CLIENT_ID = '<OAuth client ID>'
$env:GOOGLE_CLIENT_SECRET = '<OAuth client secret>'
$env:GOOGLE_ADS_DEVELOPER_TOKEN = '<developer token>'
$env:ADS_PROXY_URL = 'http://username:password@proxy-host:8080'
$env:ADS_ADMIN_TOKEN = '<chuỗi bí mật ngẫu nhiên ít nhất 32 ký tự>'
$env:ADS_ENCRYPTION_KEY = '<khóa Fernet>'
$env:GOOGLE_ADS_API_VERSION = 'v25'
```

Tạo khóa Fernet một lần bằng `.venv/Scripts/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`; giữ khóa ổn định và lưu riêng an toàn. Có thể tạo admin token bằng `.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(32))"`. Mất khóa mã hóa sẽ cần kết nối OAuth lại. Ứng dụng không tự đọc tệp `.env`.

Trong Google Cloud, bật Google Ads API, thiết lập OAuth consent và tạo OAuth client loại Web application. Đăng ký chính xác redirect URI `http://127.0.0.1:8000/oauth/callback`; tài khoản đăng nhập phải có quyền trên MCC. Developer token cần mức truy cập phù hợp với tài khoản thử nghiệm/thực tế.

```powershell
.venv/Scripts/python -m uvicorn adschecking.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Chỉ chạy một worker vì phiên OAuth dùng một lần được giữ trong bộ nhớ. Tắt access log để URL callback chứa authorization code không bị ghi vào nhật ký. Bản này dành cho máy cục bộ; chưa triển khai xác thực nhiều người dùng hay máy chủ công khai.

### Các bước sử dụng

1. Mở `http://127.0.0.1:8000/docs`, chọn **Authorize**, nhập `ADS_ADMIN_TOKEN`.
2. Gọi `POST /proxy/check`. Thành công chỉ chứng minh truy cập endpoint nhận diện Google qua proxy, chưa chứng minh quyền Google Ads.
3. Gọi `POST /oauth/start`, mở `authorization_url` trong cùng trình duyệt đã gọi API để cookie xác thực phiên được giữ nguyên; đăng nhập và cấp quyền.
4. Gọi `GET /accounts` để xem tài khoản truy cập trực tiếp. Danh sách này không phải toàn bộ tài khoản con.
5. Gọi `PUT /manager` với `{"customer_id":"123-456-7890"}`. Ứng dụng kiểm tra quyền truy cập và xác minh tài khoản là MCC trước khi lưu lựa chọn. Có thể nhập MCC lồng trong cây mà người dùng có quyền, dù không xuất hiện ở danh sách truy cập trực tiếp.
6. Gọi `GET /manager/clients` để đọc các tài khoản trong cây, gồm thông tin cấp độ, trạng thái, tài khoản quản lý, loại tiền và múi giờ. Kết quả có thể chứa MCC trung gian.
7. `GET /connection` xem trạng thái đã lưu; `DELETE /connection` xóa kết nối cục bộ. Xóa cục bộ không thu hồi quyền ứng dụng tại Google; có thể thu hồi trong trang quyền truy cập của tài khoản Google.

### Phạm vi proxy và bảo mật

- Proxy HTTP/HTTPS là bắt buộc; hỗ trợ thông tin xác thực trong URL. Mã hóa phần username/password theo URL nếu có ký tự đặc biệt. Chưa hỗ trợ SOCKS5.
- Mọi HTTP request do backend gửi đến Google, gồm đổi/làm mới token và truy vấn Ads, dùng proxy đã cấu hình; không dùng proxy môi trường và không tự chuyển sang kết nối trực tiếp khi lỗi. TLS luôn được xác minh.
- Trang đăng nhập Google mở trong trình duyệt sử dụng cấu hình mạng của trình duyệt, không tự nhận proxy backend. Nếu cần cùng tuyến kết nối, cấu hình proxy trình duyệt riêng; callback loopback phải truy cập trực tiếp được.
- Refresh token và MCC đã chọn lưu mã hóa tại `data/connection.enc`; có thể đổi đường dẫn bằng `ADS_TOKEN_FILE`. Bảo vệ quyền đọc thư mục và khóa trên máy. Không bật nhật ký HTTP mức debug.
- Đổi OAuth thành công xóa lựa chọn MCC cũ, buộc xác minh lại. Phiên OAuth hết hạn sau 10 phút, ràng buộc cookie trình duyệt và chỉ sử dụng một lần.

### Kiểm thử

```powershell
.venv/Scripts/python -m pytest -q
```

Kiểm thử dùng HTTP giả lập cho OAuth, phân trang và quyền MCC; không chứng minh OAuth, proxy nhà cung cấp hay dữ liệu Google Ads thật hoạt động. Cần kiểm tra thực tế với cấu hình của người vận hành.

Tài liệu tham chiếu: [OAuth web server](https://developers.google.com/identity/protocols/oauth2/web-server), [HTTP headers Google Ads](https://developers.google.com/google-ads/api/rest/auth), [danh sách tài khoản truy cập](https://developers.google.com/google-ads/api/docs/account-management/listing-accounts).
