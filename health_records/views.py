import base64
import datetime
import json
import os
import time
import uuid
from urllib.parse import urlparse, unquote

import requests
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import *
from .serializers import *
from openai import OpenAI
import openai


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def upload_images(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated."}, status=401)
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
            health_record_image = HealthRecordImage(image=image_file, user=user)
            health_record_image.save()
            # cloudfront_domain_name = os.environ.get('IMAGE_CUSTOM_DOMAIN')
            # s3_object_key = health_record_image.image.name
            # cloudfront_url = f'{cloudfront_domain_name}/{s3_object_key}'
            # urls.append(cloudfront_url)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    return Response({'message': '이미지가 정상 업로드 되었습니다'})


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
        return Response({'error': '존재하지 않는 검사지에 대한 요청입니다'}, status=404)

    records_to_delete.delete()
    return Response({'message': '성공적으로 삭제되었습니다'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def user_health_records_count(request):
    user = request.user
    total_records_count = user.healthrecordimage_set.count()
    analyzed_records_count = user.healthrecordimage_set.exclude(ocr_text='').count()

    return Response({
        'total_records_count': total_records_count,
        'analyzed': analyzed_records_count,
        'unanalyzed': total_records_count - analyzed_records_count,
    })


def extract_table_data(res):
    cell_data_list = []
    ban_words = ['□', '의심']
    for cell in res["images"][0]["tables"][0]["cells"]:
        if cell['cellTextLines']:
            infer_text_fragments = []
            for text_line in cell['cellTextLines']:
                for cell_word in text_line['cellWords']:
                    if not any(ban_word in cell_word['inferText'] for ban_word in ban_words):
                        infer_text_fragments.append(cell_word['inferText'])
            infer_text = ' '.join(infer_text_fragments)
        else:
            infer_text = None

        cell_data = {
            "inferText": infer_text,
            "rowSpan": cell.get('rowSpan', 1),
            "rowIndex": cell.get('rowIndex', 0),
            "columnSpan": cell.get('columnSpan', 1),
            "columnIndex": cell.get('columnIndex', 0)
        }
        cell_data_list.append(cell_data)

    return cell_data_list


def structure_table_data(raw_data):
    sorted_cell_data = sorted(raw_data, key=lambda x: (x['rowIndex'], x['columnIndex']))
    structured_data = {}
    current_row = None
    cell_texts = []
    key = ''

    for cell in sorted_cell_data:
        if cell['rowSpan'] > 1 or cell['rowIndex'] == 0:
            continue

        cell_text = cell['inferText'] if cell['inferText'] is not None else ''

        if cell['rowIndex'] != current_row:
            if current_row is not None and len(cell_text) > 0:
                structured_data[key] = ' '.join(cell_texts)
                cell_texts = []

            current_row = cell['rowIndex']
            key = cell_text
            structured_data[key] = ''
        else:
            cell_texts.append(cell_text)

    if cell_texts:
        structured_data[key] += ''.join(cell_texts)

    return structured_data


def refine_table_data(structured_data):
    print("재구조화된 정보")
    print(structured_data)
    print("================")
    api_key = os.environ.get('OPEN_AI_API_KEY')
    client = OpenAI(api_key=api_key)

    system_feature = {
        "role": "system",
        "content": "실제 환자의 건강검사지 정보를 key:value 페어로 요약했다. key또는 value가 더미인 것들은 omit해라. "
                   "value는 환자의 값, 평균치, 상태 분류 등으로 이루어지는데 이 중 환자값과 상태분류로 추정되는 값만 남기고 "
                   "평균치에 대한 정보는 제외시켜라 평균치는 보통 괄호 내의 숫자범위로 제시된다. "
                   "너의 응답은 오로지 깔끔하게 정리한 key-pair쌍으로만 이루어져야하고, 그외 다른 어떠한 말도 포함시키지마라"
    }
    query = [system_feature, {"role": "user", "content": structured_data}]

    response = client.chat.completions.create(
        model="gpt-4-0613",
        messages=query,
        temperature=0,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


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


def perform_general_ocr_analysis(record):
    api_url = os.environ.get('GENERAL_OCR_API_URL')
    secret_key = os.environ.get('GENERAL_OCR_SECRET_KEY')

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def general_ocr_analysis(request):
    api_key = os.environ.get('OPEN_AI_API_KEY')
    client = OpenAI(api_key=api_key)

    record_id = request.data.get('record_id', None)
    if not record_id:
        return Response({'error': '이미지를 선택해주세요'}, status=400)

    try:
        target_record = HealthRecordImage.objects.get(user=request.user, pk=record_id)
        structured_data = perform_general_ocr_analysis(target_record)
    except Exception as e:
        return Response({'errors': '이미지 분석 오류 발생'}, status=500)

    instruction = os.environ.get('OPEN_AI_INSTRUCTION')
    system_feature = {
        "role": "system",
        "content": instruction
    }
    query = [system_feature, {"role": "user", "content": structured_data}]

    complete_analysis_result = ""
    def event_stream():
        nonlocal complete_analysis_result
        for chunk in client.chat.completions.create(
                model="gpt-4-0613",
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

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
# def template_ocr_analysis(request):
#     api_url = os.environ.get('TEMPLATE_OCR_API_URL')
#     secret_key = os.environ.get('TEMPLATE_OCR_SECRET_KEY')
#
#     headers = {
#         'X-OCR-SECRET': secret_key,
#     }
#
#     record_ids = request.data.get('record_ids', None)
#     if not record_ids:
#         return Response({'error': '검사지를 선택해주세요'}, status=400)
#
#     records_to_analyze = HealthRecordImage.objects.filter(user=request.user, id__in=record_ids)
#     if not records_to_analyze:
#         return Response({'error': '존재하지 않는 이미지입니다'}, status=404)
#
#     for record in records_to_analyze:
#         image_name = record.image.name
#         file_extension = os.path.splitext(image_name)[1][1:]
#         with open(record.image.path, 'rb') as img_file:
#             files = [('file', img_file)]
#             request_json = {
#                 'images': [
#                     {
#                         'format': file_extension,
#                         'name': image_name,
#                         'templateIds': []
#                     }
#                 ],
#                 'requestId': str(uuid.uuid4()),
#                 'version': 'V2',
#                 'timestamp': int(round(time.time() * 1000))
#             }
#             payload = {'message': json.dumps(request_json).encode('UTF-8')}
#             response = requests.request("POST", api_url, headers=headers, data=payload, files=files)
#             if response.status_code == 200:
#                 json_response = response.json()
#                 if not json_response['images'][0]['inferResult'] == 'FAILURE':
#                     fields = json_response['images'][0]['fields']
#                     ocr_data = {field['name']: field['inferText'] for field in fields}
#                     ocr_text_json = json.dumps(ocr_data, ensure_ascii=False)
#                     record.ocr_text = ocr_text_json
#                     record.save()
#                 else:
#                     errors, status = perform_general_ocr_analysis(record)
#                     if errors:
#                         return Response({'errors': errors}, status=status)
#             else:
#                 return Response({'error': '검사지 분석 실패'}, status=response.status_code)
#
#     return Response({'message': '검사지 분석이 완료되었습니다'})
