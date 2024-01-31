# Hemochat
### 1. 필수 라이브러리 설치
    pip install -r requirements.txt
### 2. 서버 실행
    python manage.py runserver
### 3. 현재 접속가능한 URL
#### (1) 관리자
    /admin
#### (2) 카카오 관련
    * /api/user/kakao/login : 로그인(최초인 경우 자동 회원가입 동반)
    * /api/user/kakao/logout?access_token=(액세스토큰값): 로그아웃
#### (3) 검사지 관련
    * api/health_records/upload/ : 검사지 이미지 업로드(10mb 이하, png jpg jpeg 확장자 만 허용) 
    * api/health_records/user_records/ : 검사지 리스트 반환(마이페이지용)
    * api/health_records/delete_health_records/ : 검사지 삭제
    * api/health_records/user_health_records_count/ : 유저 보유 중인 검사지(+OCR분석완료된 검사지) 개수 조회
    * api/health_records/general_ocr_analysis/ : 유저의 특정 검사지들에 대해 general ocr 분석
    * api/health_records/template_ocr_analysis/ : 유저의 특정 검사지들에 대해 template ocr 분석(db에 저장된 검사지를 분석) 
    * api/health_records/template_ocr_analysis_for_gpt/ : gpt용 template ocr 분석(이미지 url을 받아 분석, 검사결과 db에 저장 안함) 