# Danh sách công việc triển khai

Đã triển khai nền tảng backend cho công việc 3 và 4: OAuth, proxy HTTP/HTTPS bắt buộc, lưu token mã hóa, chọn MCC và truy vấn tài khoản con có phân trang. Đã có kiểm thử HTTP giả lập; chưa kiểm chứng với OAuth/proxy/Google Ads thật, nên chưa đánh dấu hoàn tất hai công việc. Giao diện hiện tại là API tương tác, chưa có dashboard React. Các công việc khác chưa thực hiện. Vị trí mô-đun đề xuất là tạm thời; mã kết nối hiện nằm trong `adschecking/`. Mỗi phần việc nên giới hạn trong khoảng 3-5 tệp triển khai/kiểm thử; chia nhỏ thêm trước khi viết mã nếu cần.

| ID | Công việc | Phụ thuộc | Tiêu chí nghiệm thu | Cách xác minh | Khu vực đề xuất |
|---|---|---|---|---|---|
| 1 | Bản thử nghiệm khả năng quản lý chiến dịch | Không | Ghi rõ khả năng tạo, báo cáo, nhân bản, tạm dừng theo loại chiến dịch; chặn thao tác không được hỗ trợ | Xác minh trên phiên bản API cố định và tài khoản thử nghiệm được cấp quyền | integrations/ads |
| 2 | Tính khả thi của thanh toán và liên kết | Không | Xác định chế độ thanh toán và bằng chứng số dư; phân biệt liên kết video/kênh; làm rõ phạm vi thực thi thanh toán | Tài liệu chính thức và kiểm tra chỉ đọc trên tài khoản được cấp quyền | integrations/billing |
| 3 | Bản thử nghiệm proxy | Không | Kiểm tra tuyến OAuth và API; ngừng kết nối khi proxy bắt buộc gặp lỗi; che thông tin bí mật | Kiểm thử tích hợp truyền tải và sự cố kết nối | integrations/proxy |
| 4 | Cấp quyền tài khoản quản lý và chọn tài khoản con | 1 | Chỉ chọn được tài khoản con đã cấp quyền; giữ nguyên loại tiền/múi giờ | Kiểm thử tích hợp cách ly quyền truy cập | accounts |
| 5 | Vùng nhập tạm và xem trước Excel | 4 | Hiển thị ánh xạ cột và lỗi từng dòng; nhập lại không tạo yêu cầu trùng | Bộ dữ liệu bảng tính hợp lệ, sai định dạng và trùng lặp | imports |
| 6 | Phân công và trạng thái liên kết | 2,5 | Phân biệt ánh xạ nội bộ với liên kết chính thức; hiển thị trạng thái chờ chấp thuận | Kiểm thử vòng đời liên kết và sai tài khoản | assignments |
| 7 | Bản chụp dữ liệu ban đầu | 6 | Dữ liệu ban đầu từ bảng tính và thực tế bất biến; lưu nguồn/độ mới; giá trị không có giữ là chưa biết | Kiểm thử bản chụp và nhập lại | baselines |
| 8 | Tạo mẫu chiến dịch | 1,4 | Một mẫu được hỗ trợ tạo tài nguyên ở trạng thái tạm dừng với cấu hình đã xác minh | Kiểm tra chỉ xác thực và tích hợp trên tài khoản thử nghiệm | campaigns/templates |
| 9 | Khởi chạy và dừng có xác minh | 8 | Khởi chạy trong phạm vi ngân sách; đọc lại trạng thái tạm dừng; đối soát thao tác ghi chưa rõ kết quả | Kiểm thử hết thời gian chờ, thử lại và trạng thái trên Google | campaigns/actions |
| 10 | Nhân bản có giới hạn | 9 | Ánh xạ tài nguyên mới; ngân sách độc lập; áp dụng giới hạn nhân bản | Kiểm thử tác vụ trùng và tham chiếu giữa các tài khoản | campaigns/cloning |
| 11 | Ước tính chi phí | 7 | Ước tính theo từng chỉ số với mức bất định và nguồn dữ liệu; không cam kết mức tối thiểu được bảo đảm | Kiểm thử công thức, tiến độ bằng không và thiếu dữ liệu | funding/estimates |
| 12 | Giữ chỗ kinh phí | 2,11 | Phân bổ nguyên tử, đúng loại tiền; số dư chưa biết ngăn kết quả kinh phí chính xác | Kiểm thử yêu cầu đồng thời và số dư cũ | funding/reservations |
| 13 | Quy trình yêu cầu cấp kinh phí | 12 | Phân biệt duyệt/gửi/xác nhận; không thử lại thanh toán chưa rõ kết quả | Kiểm thử chuyển trạng thái và đối soát | funding/requests |
| 14 | Bộ quét mười phút có trạng thái bền vững | 3,7,9 | Không chạy chồng; khôi phục lần quét bị lỡ; phân tán lịch tài khoản theo hạn ngạch | Kiểm thử khởi động lại, hạn ngạch và lỗi proxy | monitoring/scanner |
| 15 | Quy tắc mục tiêu và thời gian | 10,14 | Xác định rõ chỉ số/khoảng thời gian; chặn nhân bản khi dừng; chỉ tạm dừng chiến dịch thuộc yêu cầu | Kiểm thử dữ liệu cũ, xử lý đồng thời, hạn chót và nhiều chiến dịch | monitoring/rules |
| 16 | Hàng đợi sự kiện thông báo di động | 13,15 | Loại trùng sự kiện; chỉ hoàn thành sau khi xác minh dừng trên Google | Môi trường thử nghiệm nhà cung cấp và kiểm thử giao thông báo trùng | notifications |
| 17 | Triển khai và kiểm soát vận hành | 16 | Cảnh báo tình trạng hệ thống, bảo vệ thông tin bí mật, nhật ký kiểm toán, sao lưu và quy trình khôi phục | Chủ động tạo lỗi để kiểm thử và diễn tập khôi phục | operations |
| 18 | Thử nghiệm thực tế có giới hạn | 17 | Phạm vi ngân sách rõ ràng; đo độ trễ quét và mức vượt mục tiêu; xác nhận dừng thực tế | Báo cáo thử nghiệm nhiều ngày được cấp quyền | acceptance |

## Tiêu chí nghiệm thu bắt buộc cho chiến dịch
Các tiêu chí sau bổ sung cho công việc hiện có theo quy trình đã xác nhận: không cần hướng dẫn -> Video -> Lượt đăng ký và lượt tương tác trên YouTube:
- Công việc 1: Xác minh loại chiến dịch thực tế được tạo và hỗ trợ API cho mục tiêu tương tác cụ thể; không thay bằng lượt xem video thông thường. Kiểm thử tạo, báo cáo, nhân bản và tạm dừng.
- Công việc 8 (cũng phụ thuộc công việc 6): Yêu cầu liên kết kênh chính thức, xác minh hành động chuyển đổi đăng ký/lượt xem tiếp theo và phạm vi phân phối trên YouTube; giữ nguyên mục tiêu không liên quan của tài khoản.
- Công việc 10: Giữ mục tiêu chuyển đổi đã chọn khi nhân bản và xác minh lại liên kết/hành động của tài khoản đích.
- Công việc 11: Ước tính chi phí còn lại từ mục tiêu đăng ký và chi phí trên mỗi lượt đăng ký được ghi nhận từ quảng cáo, có tính mức bất định và kinh phí đã giữ chỗ.
- Công việc 15: Chỉ hoàn thành khi đạt mục tiêu lượt đăng ký được ghi nhận từ quảng cáo của yêu cầu. Kiểm thử dưới/bằng/trên ngưỡng, tổng có phần thập phân không làm tròn lên, loại trừ lượt xem tiếp theo và hoạt động trước yêu cầu/không liên quan, tổng hợp các bản nhân bản không tính trùng và thay thế bản chụp lũy kế. Kết quả cũ hoặc phân bổ nhiều kênh chưa rõ ràng không được hoàn thành yêu cầu. Xác minh mọi chiến dịch thuộc yêu cầu đã tạm dừng trước khi thông báo hoàn thành; điều chỉnh báo cáo đến muộn không được khởi động lại công việc đã hoàn thành.
- Công việc 5: Khi xác thực dữ liệu nhập/biểu mẫu, yêu cầu mục tiêu đăng ký của từng yêu cầu là số nguyên dương.
- Công việc 8: Dùng hành động chuyển đổi đăng ký để tối ưu; lượt xem tiếp theo chỉ mang tính tham khảo và không được dùng để xét hoàn thành.

## Tiến độ giao diện desktop

- Đã bổ sung giao diện desktop tiếng Việt trong `adschecking/desktop.py`, khởi chạy qua `start-desktop.ps1`.
- Bắt buộc nhập và kiểm tra proxy trước khi mở khóa thông tin Google và đăng nhập. Đổi proxy xóa phiên cũ; đổi MCC yêu cầu xác minh lại trước khi tải tài khoản con.
- Có đăng nhập qua trình duyệt hệ thống, callback loopback, hủy/ngắt kết nối, bảng tài khoản con và tác vụ mạng nền.
- Token desktop chỉ tồn tại theo phiên dưới dạng mã hóa; cấu hình proxy trình duyệt tách biệt với proxy backend.
- Đã kiểm thử giao diện và OAuth bằng dữ liệu giả lập; chưa xác minh Google Ads/proxy thật và chưa đóng gói EXE. Dashboard React vẫn chưa triển khai.

## Các mốc kiểm tra
- [ ] Sau công việc 1-3: đã rà soát định dạng chiến dịch và phạm vi cấp kinh phí; giải quyết trở ngại về tính khả thi.
- [ ] Sau công việc 4-7: đã xác minh quy trình từ Excel đến tài khoản con và dữ liệu ban đầu.
- [ ] Sau công việc 8-10: đã xác minh khởi chạy, nhân bản và dừng chiến dịch được hỗ trợ.
- [ ] Sau công việc 11-13: đã xác minh ước tính và đối soát kinh phí, không thanh toán trùng.
- [ ] Sau công việc 14-16: đã xác minh phối hợp giám sát, dừng theo mục tiêu và thông báo di động.
- [ ] Sau công việc 17-18: đã nghiệm thu khôi phục vận hành và thử nghiệm thực tế trong phạm vi xác định.

## Trạng thái hoàn thành công việc
- [ ] 1
- [ ] 2
- [ ] 3
- [ ] 4
- [ ] 5
- [ ] 6
- [ ] 7
- [ ] 8
- [ ] 9
- [ ] 10
- [ ] 11
- [ ] 12
- [ ] 13
- [ ] 14
- [ ] 15
- [ ] 16
- [ ] 17
- [ ] 18
