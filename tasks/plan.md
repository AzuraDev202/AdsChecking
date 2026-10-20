# Kế hoạch triển khai AdsChecking

## Phạm vi
Xây dựng ứng dụng hoạt động liên tục cho tài khoản người quản lý, hỗ trợ nhập yêu cầu từ Excel, gán tài khoản Google Ads con được cấp quyền cho kênh/video YouTube, ghi nhận dữ liệu ban đầu, tạo chiến dịch được hỗ trợ, nhân bản cấu hình, ước tính kinh phí, giám sát mỗi mười phút, dừng công việc đã đạt mục tiêu và gửi thông báo trên điện thoại. Đây là tài liệu thiết kế, chưa phải tích hợp đã triển khai.

## Cấu hình chiến dịch đã xác nhận (thay thế các lựa chọn định dạng chung bên dưới)
Người dùng yêu cầu quy trình trong ảnh: Tạo chiến dịch mà không cần hướng dẫn -> Video -> Lượt đăng ký và lượt tương tác trên YouTube. Lựa chọn đầu tiên là tùy chọn của trình tạo chiến dịch; lựa chọn cuối là loại chiến dịch phụ/mục tiêu, không phải chiến dịch con hoặc nhóm quảng cáo. Không thay thế bằng mục tiêu lượt xem video thông thường.

Tài liệu Google Help hiện mô tả kết quả tương tác này thông qua Demand Gen -> YouTube engagements. Giữ nguyên kết quả được yêu cầu và xác minh quy trình thực tế trên tài khoản cùng tài nguyên chiến dịch được tạo trước khi chọn bộ tích hợp API. Chỉ riêng ô Video trong trình tạo không xác định tài nguyên API là VIDEO. Việc Demand Gen được hỗ trợ nói chung không chứng minh API hỗ trợ mọi thiết lập mục tiêu tương tác. Thử nghiệm tạo, cấu hình mục tiêu cụ thể, báo cáo, nhân bản và tạm dừng trên phiên bản API đã cố định; ghi rõ bước nào cần thiết lập thủ công.

Yêu cầu liên kết chính thức giữa tài khoản con và kênh YouTube. Tìm các hành động chuyển đổi lượt đăng ký và lượt xem tiếp theo, xác minh trạng thái chính/phụ, mục tiêu đặt giá thầu và phạm vi phân phối chỉ trên YouTube. Nhân bản mục tiêu đã chọn mà không thay đổi mục tiêu không liên quan của tài khoản. Ước tính chi phí trên mỗi chuyển đổi đăng ký hoặc lượt xem tiếp theo, không dùng CPV video thông thường. Phân biệt hai kết quả trong báo cáo và quy tắc hoàn thành.

Google mô tả việc ghi nhận tương tác trên bất kỳ kênh YouTube nào được liên kết với tài khoản Ads. Với tài khoản liên kết nhiều kênh, phải chứng minh khả năng phân bổ kết quả cho từng kênh trước khi hoàn thành yêu cầu của một kênh; nếu không, yêu cầu ánh xạ tài khoản/kênh riêng biệt hoặc hiển thị tiến độ chưa xác định rõ. Mức tăng tổng số người đăng ký kênh được theo dõi riêng với lượt đăng ký được ghi nhận từ quảng cáo.

Chỉ số hoàn thành đã xác nhận: số lượt đăng ký YouTube được ghi nhận từ quảng cáo đạt mục tiêu của từng yêu cầu. Mục tiêu nhập trong Excel hoặc biểu mẫu phải là số nguyên dương. Lượt xem tiếp theo, mức tăng tổng số người đăng ký kênh và thời gian chạy chỉ mang tính tham khảo, không phải điều kiện thành công. Cấu hình chiến dịch tối ưu lượt đăng ký; không cộng lượt xem tiếp theo vào tổng dùng để xét hoàn thành.

Ở mỗi lần quét mười phút, so sánh tổng chuyển đổi đăng ký lũy kế hợp lệ mới nhất của các chiến dịch thuộc yêu cầu và các hành động chuyển đổi đăng ký đã chọn với mục tiêu. Tính mỗi bản nhân bản thuộc yêu cầu đúng một lần, loại trừ chiến dịch/hành động không liên quan và hoạt động trước yêu cầu; thay thế số liệu quan sát trước thay vì cộng dồn tổng của các lần quét. Giữ nguyên độ chính xác của báo cáo, không làm tròn lên để đạt mục tiêu. Lưu khoảng thời gian báo cáo, ID hành động chuyển đổi, thiết lập phân bổ, độ mới của nguồn dữ liệu và tổng quan sát làm bằng chứng hoàn thành.

Khi attributed_subscriptions >= target_subscriptions, chặn việc khởi chạy/nhân bản tiếp theo bằng thao tác nguyên tử, tạm dừng mọi chiến dịch thuộc yêu cầu, xác minh trạng thái tạm dừng trên hệ thống Google, sau đó đánh dấu completed và gửi thông báo hoàn thành trên điện thoại. Dữ liệu phân bổ bị thiếu, cũ hoặc không rõ ràng không được kích hoạt hoàn thành. Nếu tạm dừng thất bại, giữ trạng thái stop_requested, thử lại và phát cảnh báo. Việc dừng bảo vệ do ngân sách/hạn chót được phân biệt với hoàn thành thành công. Điều chỉnh chuyển đổi đến muộn cập nhật báo cáo nhưng không tự khởi động lại chiến dịch đã hoàn thành.

Ước tính kinh phí còn lại bằng max(0, target_subscriptions - attributed_subscriptions) nhân với chi phí ước tính trên mỗi lượt đăng ký được ghi nhận từ quảng cáo, cộng dự phòng/phí theo quy tắc hiện có. Cấu hình còn thiếu: giá trị mục tiêu của từng yêu cầu và khoảng thời gian phân bổ/báo cáo. Lựa chọn chiến dịch và chỉ số thành công đã được xác nhận.

Nguồn đã kiểm tra ngày 2026-10-19:
- https://support.google.com/google-ads/answer/2375497?hl=en
- https://support.google.com/google-ads/answer/12301500?hl=en

## Điều kiện xác minh tính khả thi
Đã đối chiếu tài liệu Google ngày 2026-10-19:
- Nhìn chung, không thể tạo hoặc sửa chiến dịch VIDEO tiêu chuẩn qua Google Ads API. Demand Gen hỗ trợ tạo và quản lý. Chọn định dạng cần dùng trước khi cam kết tự động hóa; xác minh từng thao tác trên phiên bản API đã cố định. Với Video tiêu chuẩn, kiểm tra từng thao tác qua Google Ads Scripts; không mặc định rằng tạo, nhân bản hoặc dừng theo chu kỳ mười phút đều được hỗ trợ.
- Quản lý thiết lập thanh toán, ngân sách tài khoản và hóa đơn qua API yêu cầu chế độ lập hóa đơn hằng tháng. Đây không phải API tổng quát để đọc số dư trả trước hoặc thu tiền từ thẻ đã liên kết. Có thể tự động hóa yêu cầu cấp kinh phí nội bộ; việc thanh toán thực tế vẫn chuyển sang giao diện thanh toán trừ khi đã chứng minh có tích hợp được hỗ trợ.
- Gán tài khoản/kênh trong ứng dụng khác với liên kết chính thức của Google. Theo tài liệu, yêu cầu liên kết video cần nhà sáng tạo chấp thuận; khả năng liên kết ở cấp kênh cần được xác minh riêng.

Nguồn:
- https://developers.google.com/google-ads/api/docs/video/overview
- https://developers.google.com/google-ads/api/docs/billing/overview
- https://developers.google.com/google-ads/api/docs/account-management/linking-youtube

## Kiến trúc đề xuất
Giao diện quản trị React/PWA, dịch vụ FastAPI, PostgreSQL, hàng đợi và tiến trình xử lý có trạng thái bền vững, một bộ lập lịch được bầu làm đầu mối, hệ thống quản lý thông tin bí mật và giám sát vận hành. Xác minh lựa chọn công nghệ trong quá trình triển khai. Triển khai trên máy chủ hoạt động liên tục thay vì phụ thuộc máy tính cá nhân luôn bật.

Lưu tài khoản người quản lý, tài khoản con, phân công kênh, đợt nhập dữ liệu, yêu cầu, dữ liệu ban đầu bất biến, ánh xạ chiến dịch, số liệu quan sát, ước tính ngân sách, yêu cầu cấp kinh phí, tác vụ thao tác, hàng đợi thông báo gửi đi và sự kiện kiểm toán. Giới hạn mọi thao tác theo tài khoản quản lý, khách hàng, yêu cầu và người dùng được cấp quyền. Lưu tiền dưới dạng số nguyên đơn vị micro kèm loại tiền; không cộng các loại tiền khác nhau.

## Các quy trình
### Excel và dữ liệu ban đầu
Nhập dữ liệu vào vùng tạm, có xem trước, ánh xạ cột, lỗi theo từng dòng và phát hiện trùng lặp. Các cột đề xuất: ID yêu cầu, ID khách hàng, ID/URL kênh, ID/URL video, chỉ số mục tiêu, giá trị mục tiêu, chế độ mục tiêu (tuyệt đối hoặc tăng thêm), hạn chót, mức chi tối đa, loại tiền, mẫu cấu hình, người nhận thông báo và tham chiếu hồ sơ proxy. Không nhập thông tin xác thực hoặc số thẻ.

Xác minh tài khoản con thuộc tài khoản quản lý, danh tính video/kênh, quyền truy cập và giá trị mục tiêu. Giữ nguyên dữ liệu ban đầu từ bảng tính và tạo riêng bản chụp trước khi chạy có thời điểm, nguồn và độ mới dữ liệu. Không ghi đè dữ liệu ban đầu khi nhập lại. Báo cáo thay đổi toàn kênh riêng với kết quả được ghi nhận từ quảng cáo; tăng trưởng kênh tự nó không chứng minh hiệu quả được phân bổ cho quảng cáo. Dữ liệu phân tích riêng tư cần quyền phù hợp từ chủ sở hữu. Chỉ số bị thiếu phải giữ là chưa biết, không coi là không.

### Tạo và nhân bản chiến dịch
Tạo từ mẫu có phiên bản, kiểm tra tính hợp lệ, tạo ở trạng thái tạm dừng, xác minh cấu hình và chỉ bật trong phạm vi ngân sách đã duyệt của yêu cầu. Nhân bản cấu hình được hỗ trợ sang tài nguyên mới, ánh xạ lại thành phần quảng cáo, ngân sách và tham chiếu chuyển đổi khi cần. Không sao chép lịch sử hoặc mặc định tài nguyên có thể dùng lại giữa các tài khoản. Mặc định dùng ngân sách độc lập. Giới hạn nhân bản tự động bằng số lượng tối đa, tổng mức chi và thời gian chờ giữa các lần. Đối soát thao tác ghi chưa rõ kết quả trước khi thử lại.

### Ngân sách và cấp kinh phí
Kết quả là kinh phí cần thiết theo ước tính, không phải mức giá tối thiểu được bảo đảm:

remaining_units = max(0, target_units - verified_progress)
estimated_remaining_cost = remaining_units * estimated_cost_per_unit
required_funds = estimated_remaining_cost + uncertainty_reserve + applicable_fees
available_funds = verified_available_balance - other_request_reservations
suggested_top_up = max(0, required_funds - available_funds)

Dùng CPV cho lượt xem, CPM/1000 cho lượt hiển thị và CPA cho chuyển đổi. Chỉ thời gian chạy không đủ xác định ngân sách theo kết quả. Ước tính từ lịch sử tài khoản có tính tương đồng hoặc thử nghiệm giới hạn; hiển thị khoảng thấp/cơ sở/cao, ngày nguồn dữ liệu và giả định. Tính phần chi chưa được báo cáo theo hướng thận trọng và tránh tính hai lần khoản chi đã phản ánh trong số dư. Phân bổ kinh phí bằng thao tác nguyên tử giữa các yêu cầu đồng thời.

Phân biệt tiền trả trước, nghĩa vụ thanh toán tự động, phần ngân sách còn lại theo chế độ hóa đơn hằng tháng và hạn mức chi nội bộ. Nếu số dư bị thiếu hoặc cũ, hiển thị kinh phí cần thiết là chưa xác định và yêu cầu đối soát; không suy diễn số dư từ chỉ số chi phí.

Vòng đời cấp kinh phí: requested -> approved -> submitted -> confirmed/failed/unknown, tương ứng đã yêu cầu -> đã duyệt -> đã gửi -> đã xác nhận/thất bại/chưa rõ. Lưu tài khoản, số tiền, loại tiền, tham chiếu phương thức thanh toán đã che thông tin, người duyệt và bằng chứng. Đã gửi không đồng nghĩa đã xác nhận thanh toán. Không tự thử lại khoản thanh toán chưa rõ kết quả. Không lưu thông tin thẻ thực tế trong ứng dụng. Thanh toán qua giao diện thanh toán có thể yêu cầu người dùng xác thực.

### Giám sát và dừng theo chu kỳ mười phút
Lập lịch 144 lần quét/tài khoản/ngày, phân tán thời điểm bắt đầu, lấy báo cáo theo lô, tuân thủ hạn ngạch và ngăn các tác vụ cùng tài khoản chạy chồng lên nhau. Mỗi lần quét cập nhật điều kiện đủ để chạy, trạng thái, hiệu suất, độ mới dữ liệu, thời gian và bằng chứng kinh phí trước khi đánh giá quy tắc có phiên bản. Khôi phục các lần quét bị bỏ lỡ sau khi khởi động lại mà không lặp thao tác.

Theo dõi riêng thời gian theo lịch, thời gian đã bật sau khi loại trừ các khoảng tạm dừng đã biết, lần đầu và lần cuối quan sát thấy phân phối quảng cáo. Việc thăm dò định kỳ không xác định chính xác số giây thực sự phân phối. Mục tiêu phải xác định chỉ số, nguồn, khoảng thời gian và cách kết hợp AND/OR nếu có nhiều điều kiện.

Vòng đời yêu cầu: draft -> validated -> awaiting_link/funding -> ready -> running -> stop_requested -> stopped_verified -> completed, tương ứng bản nháp -> đã xác thực -> chờ liên kết/kinh phí -> sẵn sàng -> đang chạy -> đã yêu cầu dừng -> đã xác minh dừng -> hoàn thành; ngoại lệ chuyển sang needs_attention (cần xử lý). Khi đạt mục tiêu, chặn bản nhân bản mới bằng thao tác nguyên tử và đưa yêu cầu tạm dừng tất cả chiến dịch thuộc yêu cầu vào hàng đợi. Không tạm dừng công việc không liên quan trong cùng tài khoản con. Xác minh trạng thái tạm dừng trên Google trước khi ghi nhận hoàn thành. Mặc định hủy nghĩa là PAUSED để giữ lịch sử; xóa là thao tác riêng phải được yêu cầu rõ ràng.

Dùng tác vụ hạn chót độc lập để dừng theo thời gian nếu được hỗ trợ. Chu kỳ thăm dò mười phút cộng độ trễ báo cáo và cập nhật có thể khiến kết quả vượt mục tiêu; hiển thị giới hạn này và dùng ngưỡng thận trọng. Dữ liệu hiệu suất cũ không được dẫn đến tuyên bố thành công hoặc tăng ngân sách. Dừng bảo vệ theo giới hạn an toàn và hạn chót độc lập với việc đạt mục tiêu hiệu suất.

### Thông báo trên điện thoại
Dùng thông báo đẩy PWA hoặc một nhà cung cấp thông báo di động đã chọn. Gửi sự kiện đã loại trùng cho các mốc xác nhận khởi chạy, xác nhận kinh phí, đạt mục tiêu/đang dừng, hoàn thành đã xác minh và lỗi. Kèm định danh yêu cầu/tài khoản, kết quả đo được, độ mới dữ liệu chi phí và liên kết đến giao diện quản trị. Lưu bền vững hàng đợi gửi đi cùng trạng thái thử lại và giao nhận; thử lại thông báo không được chạy lại chiến dịch hoặc thanh toán.

### Cấu hình proxy
Hỗ trợ hồ sơ proxy có tên và xác thực, có thể ánh xạ vào tuyến kết nối của tiến trình xử lý tài khoản con. Xác minh HTTP CONNECT với cơ chế truyền tải Google Ads đã chọn; chỉ thêm SOCKS5 sau khi kiểm thử truyền tải. Kiểm tra riêng kết nối OAuth, Ads API và YouTube. Mã hóa thông tin xác thực, xác minh TLS, che thông tin nhạy cảm trong nhật ký, kiểm tra kết nối ra ngoài và mặc định không chuyển sang kết nối trực tiếp khi bắt buộc dùng proxy. Định tuyến proxy ổn định không thay thế quyền OAuth hoặc nhắm mục tiêu địa lý của chiến dịch. Sự cố proxy phải phát cảnh báo vì cũng có thể ngăn việc dừng chiến dịch.

## Thứ tự triển khai
1. Chứng minh khả năng tạo chiến dịch, dừng, liên kết, thanh toán và proxy cho các loại tài khoản đã chọn.
2. Hoàn thiện truy xuất danh sách tài khoản, xác thực Excel, phân công và dữ liệu ban đầu bất biến.
3. Hoàn thiện một mẫu chiến dịch được hỗ trợ với khởi chạy/dừng đã xác minh, sau đó thêm nhân bản có giới hạn.
4. Hoàn thiện ước tính ngân sách, giữ chỗ kinh phí và đối soát yêu cầu cấp kinh phí.
5. Hoàn thiện quét liên tục, quy tắc hoàn thành và thông báo trên điện thoại.
6. Kiểm thử khôi phục lỗi và thử nghiệm thực tế có giới hạn, được cấp quyền trước khi mở rộng.

Công việc và mốc kiểm tra chi tiết: [todo.md](todo.md).

## Nghiệm thu và rủi ro
Không cam kết đưa vào vận hành thực tế trước khi định dạng chiến dịch đã chọn hỗ trợ cả tạo và dừng theo yêu cầu. Chứng minh cách ly tài khoản, chống trùng sau khi hết thời gian chờ, giữ chỗ ngân sách đồng thời, không xác nhận sai thanh toán, xử lý dữ liệu cũ, khôi phục sau khởi động lại, cảnh báo lỗi proxy và xác minh dừng trước thông báo hoàn thành. Kiểm thử thực tế cần phạm vi tài khoản và chi tiêu rõ ràng. Tài khoản thử nghiệm không chứng minh được phân phối quảng cáo hoặc thanh toán thực tế.

## Các điểm cần xác định
- Xác minh tài nguyên API được tạo bởi quy trình chiến dịch đã xác nhận và mức hỗ trợ mục tiêu tương tác.
- Mục tiêu số lượt đăng ký được ghi nhận từ quảng cáo cho từng yêu cầu và khoảng thời gian phân bổ/báo cáo.
- Các cột Excel và ý nghĩa liên kết kênh: phân công nội bộ hay liên kết chính thức của Google.
- Chế độ thanh toán, quốc gia, loại tiền và nguồn số dư đáng tin cậy cho từng tài khoản con.
- Số tài khoản con, nhà cung cấp thông báo di động, giao thức proxy và hành vi dự phòng cần thiết.

Ước tính ban đầu: 8-12 tuần kỹ thuật cho một lập trình viên có kinh nghiệm sau khi xác định tính khả thi và phạm vi; chưa bao gồm thời gian duyệt quyền truy cập bên ngoài và các tích hợp thanh toán chưa được hỗ trợ. Ước tính lại sau bản thử nghiệm khả năng tích hợp.
