# Hemochat
### 1. 필수 라이브러리 설치
    pip install -r requirements.txt
### 2. 서버 실행
    python manage.py runserver
### 3. 현재 접속가능한 URL

#### (1) 스웨거(전체 api 명세서 및 테스트 가능 플랫폼)
- `swagger/`
- `redoc/`
#### (2) 소셜 로그인 관련
- `user/kakao/login`: 카카오 로그인(최초인 경우 자동 회원가입 동반)
- `user/google/login`: 구글 로그인(최초인 경우 자동 회원가입 동반)

- `user/refresh`: JWT 토큰 갱신

#### (2-2) 일반 회원가입 및 로그인 관련
- `user/email/signup`: 이메일 회원가입
- `user/email/login`: 이메일 로그인 (JWT 토큰 발급)
- `user/send-verification-code`: 휴대폰 인증 코드 발송
- `user/verify-phone-number`: 휴대폰 번호 인증


#### (2-3) 마이페이지 및 회원정보 수정 관련
- `user/my-page`: 마이페이지 조회
- `user/update`: 사용자 정보(프로필 사진) 업데이트
- `user/delete`: 사용자 삭제

#### (2-4) 아이디 및 비번 찾기
* `find-email/send-verification-code/` (이메일 찾기 인증 코드 발송)
* `find-email/return/` (인증된 휴대폰 번호로 이메일 반환)
* `find-password/send-verification-code/` (비밀번호 찾기 휴대폰 인증)
* `find-password/reset/` (비밀번호 재설정)
    
#### (3) 검사지 관련
- `api/health_records/upload`: 검사지 이미지 업로드(10mb 이하, png jpg jpeg 확장자 만 허용)
- `api/health_records/user_records`: 검사지 리스트 반환(마이페이지용)
- `api/health_records/delete_health_records`: 검사지 삭제
- `api/health_records/general_ocr_analysis`: 유저의 특정 검사지들에 대해 general ocr 분석

#### (4-1) 채팅 서비스 관련(OPEN AI Assistant API 기반)
- `api/chat_services/enter_chatroom/<str:chatroom_id>/`: 채팅방 입장(DB에서 대화내역 가져와 캐싱)
- `api/chat_services/create_chatroom/`: 채팅방 생성
- `api/chat_services/delete_chatroom/<str:chatroom_id>/`: 채팅방 삭제(대화내역도 같이 삭제)
- `api/chat_services/create_message/<str:chatroom_id>/`: 메시지 생성 및 전송
- `api/chat_services/create_temp_chatroom/`: 임시 채팅방 생성
- `api/chat_services/upload_temp_image/<str:chatroom_id>/`: 임시 채팅방에 이미지 업로드
- `api/chat_services/list_chatroom/`: 채팅방 리스트 반환
