import base64,datetime,json,os,time,uuid,requests

import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import *
from .serializers import *
from chat_services.models import TempChatroom

from openai import OpenAI
import openai

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

OPEN_AI_API_KEY = os.environ.get('OPEN_AI_API_KEY')
OPEN_AI_CHAT_INSTRUCTION = os.environ.get('OPEN_AI_CHAT_INSTRUCTION')
GENERAL_OCR_API_URL = os.environ.get('GENERAL_OCR_API_URL')
GENERAL_OCR_SECRET_KEY = os.environ.get('GENERAL_OCR_SECRET_KEY')
OPEN_AI_INSTRUCTION = os.environ.get('OPEN_AI_INSTRUCTION')
client = OpenAI(api_key=OPEN_AI_API_KEY)


@swagger_auto_schema(
    method='post',
    manual_parameters=[
        openapi.Parameter(
            'images',
            openapi.IN_FORM,
            description="form-data 형식의 이미지/폴더",
            type=openapi.TYPE_FILE,
            required=True,
            multiple=True
        ),
    ],
    responses={
        200: openapi.Response(description="이미지가 정상 업로드 되었습니다"),
        400: openapi.Response(description="Bad request"),
        500: openapi.Response(description="Internal server error")
    },
    operation_description="""
    사용자가 이미지를 업로드합니다.(체험판, 로그인 전제 공용)
    업로드된 이미지는 해당 사용자의 HealthRecordImage 모델과 연결됩니다.
    인증되지 않은 사용자의 경우 이미지는 익명 사용자 디렉토리에 저장됩니다.
    
    [헤더에 jwt 인증 토큰]
    체험판 페이지에서는 부착할 필요없고, 로그인 전용 페이지에서 시도하는 경우 붙여주세요.
    jwt 토큰은 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def upload_images(request):
    if 'images' not in request.FILES:
        return Response({'error': 'No image files provided'}, status=400)

    images_files = request.FILES.getlist('images')
    valid_extensions = ['.png', '.jpg', '.jpeg']

    for image_file in images_files:
        if not any(image_file.name.endswith(ext) for ext in valid_extensions):
            return Response({'error': ".png, .jpg .jpeg 확장자만 업로드 가능합니다."}, status=400)
        if image_file.size > 10 * 1024 * 1024:
            return Response({'error': "각 이미지 사이즈는 10MB를 넘길 수 없습니다."}, status=400)

        try:
            health_record_image = HealthRecordImage(image=image_file, user=request.user if request.user.is_authenticated else None)
            health_record_image.save()
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    return Response({'message': '이미지가 정상 업로드 되었습니다'})

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description="사용자의 건강 기록 목록",
            schema=HealthRecordImageSerializer(many=True)
        ),
        401: openapi.Response(description="Unauthorized")
    },
    operation_description="""
    이미지 id(여러개 가능) 리스트를 받아 그에 해당하는 이미지 목록을 반환합니다.
    
    [헤더에 jwt 인증 토큰] 
    로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다.""",
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def user_health_records(request):
    records = HealthRecordImage.objects.filter(user=request.user)
    serializer = HealthRecordImageSerializer(records, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def date_filtered_user_health_records(request):
    query_params = request.query_params
    start_date = query_params.get('start_date', None)
    end_date = query_params.get('end_date', None)

    records = HealthRecordImage.objects.filter(user=request.user)
    if start_date and end_date:
        # ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD 형태로 쿼리파라미터를 담아 요청해야 함
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        records = records.filter(created_at__range=(start, end))

    serializer = HealthRecordImageSerializer(records, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='delete',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'record_ids': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description='삭제할 검사지 ID 리스트'
            )
        },
        required=['record_ids']
    ),
    responses={
        200: openapi.Response(description="성공적으로 삭제되었습니다"),
        400: openapi.Response(description="삭제할 검사지를 선택하세요"),
        404: openapi.Response(description="존재하지 않는 검사지에 대한 요청입니다"),
    },
    operation_description="""
    이미지 삭제 API 입니다.
    
    [리퀘스트 바디]
    이미지 id(여러개 가능) 리스트를 담아 요청해야합니다.
    
    [헤더에 jwt 인증 토큰]
    로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다.""",
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def delete_health_records(request):
    record_ids = request.data.get('record_ids', None)  # request 바디에 삭제할 검사지 ID를 리스트로(raw json) 담아서 넘겨줘야 함

    if not record_ids:
        return Response({'error': '삭제할 검사지를 선택하세요'}, status=400)

    records_to_delete = HealthRecordImage.objects.filter(user=request.user, id__in=record_ids)
    existing_ids = records_to_delete.values_list('id', flat=True)
    non_existing_ids = set(record_ids) - set(existing_ids)

    if non_existing_ids:
        return Response({'error': '존재하지 않거나 권한 없는 이미지에 대한 요청입니다'}, status=404)

    records_to_delete.delete()
    return Response({'message': '성공적으로 삭제되었습니다'})



def format_ocr_data(ocr_data, row_threshold=10, column_threshold=50):
    # 결과 텍스트 초기화
    result_text = ""

    # 각 행을 구성하는 텍스트 블록을 담을 딕셔너리 초기화
    rows = {}

    # OCR 데이터 파싱
    for item in ocr_data['images'][0]['fields']:
        # 각 항목의 중앙점 계산
        vertices = item['boundingPoly']['vertices']
        y_center = sum(vertex['y'] for vertex in vertices) / len(vertices)
        x_center = sum(vertex['x'] for vertex in vertices) / len(vertices)

        # 가장 가까운 행 찾기
        matched_row = None
        for row_key in rows.keys():
            if abs(row_key - y_center) < row_threshold:
                matched_row = row_key
                break

        if matched_row is None:
            matched_row = y_center
            rows[matched_row] = []

        rows[matched_row].append((x_center, item['inferText']))

    # 각 행을 x_center에 따라 정렬
    for row in rows.values():
        row.sort()

    # 각 행의 텍스트를 결과에 추가
    for y_center in sorted(rows.keys()):
        row = rows[y_center]
        for i, (x_center, text) in enumerate(row):
            if i > 0 and x_center - row[i - 1][0] <= column_threshold:
                # 표의 열로 간주, '|'로 구분
                result_text += f" | {text}"
            else:
                # 표가 아닌 경우 또는 첫 번째 열
                result_text += text + " "
        result_text += "\n"

    return result_text.strip()


def extract_ocr_texts(record):
    api_url = GENERAL_OCR_API_URL
    secret_key = GENERAL_OCR_SECRET_KEY

    headers = {
        'X-OCR-SECRET': secret_key,
        'Content-Type': 'application/json'
    }

    image_name = record.image.name
    file_extension = os.path.splitext(image_name)[1][1:]
    try:
        base64_image = base64.b64encode(record.image.file.read()).decode('utf-8')
    except Exception as e:
        return "파일을 처리하는 도중 오류가 발생했습니다.", None

    body = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(round(time.time() * 1000)),
        "lang": "ko",
        "images": [
            {
                "format": file_extension,
                "data": base64_image,
                "name": image_name,
                "templateIds": [0]
            }
        ],
        "enableTableDetection": False
    }
    response = requests.post(api_url, headers=headers, json=body)
    if response.status_code != 200:
        return None
    else:
        res = response.json()
        structured_table_data = format_ocr_data(res)
        return json.dumps(structured_table_data, ensure_ascii=False)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'record_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Record ID'),
        },
        required=['record_id'],
        description="이미지 레코드 ID를 제공해야 합니다."
    ),
    responses={
        200: openapi.Response(description="OCR 분석이 성공적으로 완료되었습니다"),
        400: openapi.Response(description="record_id를 제공해야 합니다. 또는 OCR 텍스트가 이미 존재합니다."),
        401: openapi.Response(description="로그인이 필요합니다."),
        403: openapi.Response(description="해당 이미지에 접근할 권한이 없습니다. 또는 체험판 이미지를 분석할 수 없습니다."),
        404: openapi.Response(description="해당 이미지를 찾을 수 없습니다."),
        500: openapi.Response(description="이미지 분석 오류 발생")
    },
    operation_description="""
    업로드한 이미지의 OCR 분석 요청을 처리하고 그 결과를 chatgpt응답과 같이 스트리밍된 형태로 제공하는 API입니다.(체험판, 로그인 전용 공용)
    
    [UI 요구사항]
    AI 응답이 완료되기 전까지, 재차 이 질문 API를 사용할 수 없도록, 분석요청 버튼을 비활성화해주세요.
    
    [리퀘스트 바디]
    요청 시, 이미지 '하나'의 id(여러개 불가)인 record_id 제공해야 합니다.
    
    [헤더에 jwt 인증 토큰]
    체험판 페이지에서는 부착할 필요없고, 로그인 전용 페이지에서 시도하는 경우 붙여주세요.
    jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def general_ocr_analysis(request):
    record_id = request.data.get('record_id', None)

    if not record_id:
        return Response({'error': 'record_id를 제공해야 합니다.'}, status=400)

    target_record = get_object_or_404(HealthRecordImage, pk=record_id)

    if target_record.ocr_text:
        return Response({'error': '이미 OCR 분석이 완료된 이미지입니다.'}, status=400)

    user = request.user
    if target_record.user:
        if not user.is_authenticated or target_record.user != user:
            return Response({'error': '로그인이 필요합니다.' if not user.is_authenticated else '해당 이미지에 접근할 권한이 없습니다.'},
                            status=401 if not user.is_authenticated else 403)
    elif user.is_authenticated:
        return Response({'error': '체험판 이미지를 분석할 수 없습니다.'}, status=403)

    try:
        structured_data = extract_ocr_texts(target_record)
    except Exception as e:
        return Response({'errors': '이미지 분석 오류 발생'}, status=500)

    query = [{"role": "system", "content": OPEN_AI_INSTRUCTION}, {"role": "user", "content": structured_data}]
    complete_analysis_result = ""

    def event_stream():
        nonlocal complete_analysis_result
        for chunk in client.chat.completions.create(
                model="gpt-4-turbo",
                messages=query,
                stream=True,
        ):
            chunk_message = chunk.choices[0].delta.content
            state = chunk.choices[0].finish_reason
            if state == 'stop':
                target_record.ocr_text = complete_analysis_result
                target_record.save()
                break
            else:
                complete_analysis_result += chunk_message
            yield f"data: {chunk_message}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response