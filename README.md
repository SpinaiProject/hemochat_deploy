# Hemochat
### 1. 필수 라이브러리 설치
    pip install -r requirements.txt
### 2. 서버 실행
    python manage.py runserver
### 3. 현재 접속가능한 URL
#### (1) 관리자
    /admin
#### (2) 소셜 로그인 관련
    * /api/user/kakao/login : 카카오 로그인(최초인 경우 자동 회원가입 동반)
    * /api/user/kakao/logout?access_token=(액세스토큰값): 로그아웃
    * /api/user/google/login/ : 구글 로그인(최초인 경우 자동 회원가입 동반)

#### (2-2) 일반 회원가입 및 로그인 관련
    * /api/user/email/signup/ : 회원가입
    * /api/user/email/login/ : 로그인
    * /api/user/refresh/ : 액세스 토큰 만료 시 재발급
    * /api/user/email/already_exist/: 회원가입 시 이메일 중복검사
    * /api/user/send-verification-code/ : [아이디 찾기] 전화번호 인증 코드 전송(db에 인증코드 저장)
    * /api/user/verify-phone-number/ : [아이디 찾기] 인증코드 일치여부 검증
    * /api/user/request-phone-number/ : [비밀번호 찾기] 전화번호 요청
    * /api/user/verify-phone-and-send-code/ : [비밀번호 찾기] 인증코드 일치여부 검증 및 새 랜덤비밀번호 전송

#### (2-3) 마이페이지 및 회원정보 수정 관련
    * /api/user/my-page/ : 마이페이지(업로드한 검사지, 보유 채팅방 목록, 기본회원정보 사항 등)
    * /api/user/update/ : 회원 정보 업데이트
    * /api/user/delete/ : 회원 탈퇴

    
#### (3) 검사지 관련
    * api/health_records/upload/ : 검사지 이미지 업로드(10mb 이하, png jpg jpeg 확장자 만 허용) 
    * api/health_records/user_records/ : 검사지 리스트 반환(마이페이지용)
    * api/health_records/delete_health_records/ : 검사지 삭제
    * api/health_records/user_health_records_count/ : 유저 보유 중인 검사지(+OCR분석완료된 검사지) 개수 조회
    * api/health_records/general_ocr_analysis/ : 유저의 특정 검사지들에 대해 general ocr 분석
    * api/health_records/template_ocr_analysis/ : 유저의 특정 검사지들에 대해 template ocr 분석(db에 저장된 검사지를 분석) 
    * api/health_records/template_ocr_analysis_for_gpt/ : gpt용 template ocr 분석(이미지 url을 받아 분석, 검사결과 db에 저장 안함) 
#### (4-1) 채팅 서비스 관련(Chat Completion API)
    * api/chat_services/enter_chatroom/<uuid:chatroom_id>/ : 채팅방 입장(DB에서 대화내역 갖고와 캐싱)
    * api/chat_services/create_chatroom/ : 채팅방 생성
    * api/chat_services/delete_chatroom/<uuid:chatroom_id>/ : 채팅방 삭제(대화내역도 같이 삭제)
    * api/chat_services/create_stream/<uuid:chatroom_id>/ : OPEN AI API에 스트리밍 형태의 답변 요청
    * api/chat_services/leave_chatroom/<uuid:chatroom_id>/ : 채팅방 나가기(캐싱된 대화내역 삭제,DB에 대화내역 저장)

#### (4-2) 채팅 서비스 관련(Assistant API-Deprecated)
     * api/chat_services/create_assistant/: Assistant 생성(프롬프팅 된 특화 챗봇 생성)
     * api/chat_services/create_thread/ : Thread(대화내역 자동 저장하는 채팅방 개념) 생성
     * api/chat_services/create_message/ : Thread, Assistant 정보에 기반해 메시지 전송(스트리밍이 안되 응답이 너무 늦음)
