import base64
import datetime
import json
import os
import time
import uuid
from urllib.parse import urlparse, unquote

import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import *
from .serializers import *


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
    folder = HealthRecordFolder(user=request.user)
    folder.save()

    urls = []

    for image_file in images_files:
        if not any(image_file.name.endswith(ext) for ext in valid_extensions):
            return Response({'error': "Only .png, .jpg and .jpeg formats are supported."}, status=400)
        if image_file.size > 10 * 1024 * 1024:
            return Response({'error': "Each image size cannot exceed 10MB."}, status=400)

        try:
            health_record_image = HealthRecordImage(folder=folder, image=image_file, user=user)
            health_record_image.save()
            cloudfront_domain_name = os.environ.get('IMAGE_CUSTOM_DOMAIN')
            s3_object_key = health_record_image.image.name
            cloudfront_url = f'https://{cloudfront_domain_name}/{s3_object_key}'
            urls.append(cloudfront_url)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    return Response({'message': 'Images uploaded successfully!', 'urls': urls})


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def delete_health_records(request):
    record_ids = request.data.get('record_ids', None)  # request 바디에 삭제할 검사지 ID를 리스트로(raw json) 담아서 넘겨줘야 함

    if not record_ids:
        return Response({'error': 'No record IDs provided'}, status=400)

    records_to_delete = HealthRecordImage.objects.filter(user=request.user, id__in=record_ids)
    existing_ids = records_to_delete.values_list('id', flat=True)
    non_existing_ids = set(record_ids) - set(existing_ids)

    if non_existing_ids:
        return Response({'error': f'Record IDs not found: {non_existing_ids}'}, status=404)

    records_to_delete.delete()
    return Response({'message': 'Records deleted successfully'})


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def general_ocr_analysis(request):
    record_ids = request.data.get('record_ids', None)
    if not record_ids:
        return Response({'error': 'No record IDs provided'}, status=400)

    records_to_analyze = HealthRecordImage.objects.filter(user=request.user, id__in=record_ids)
    if not records_to_analyze:
        return Response({'error': 'provided record IDs do not exists'}, status=400)

    api_url = os.environ.get('GENERAL_OCR_API_URL')
    secret_key = os.environ.get('GENERAL_OCR_SECRET_KEY')

    headers = {
        'X-OCR-SECRET': secret_key,
        'Content-Type': 'application/json'
    }

    for record in records_to_analyze:
        image_name = record.image.name
        file_extension = os.path.splitext(image_name)[1][1:]

        with open(record.image.path, 'rb') as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

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
            "enableTableDetection": True
        }

        response = requests.post(api_url, headers=headers, json=body)
        if response.status_code == 200:
            # res = response.json()
            # infer_texts_generator = extract_infer_text(res)
            # infer_texts_list = list(infer_texts_generator)
            # final_text = ' '.join(infer_texts_list)
            # record.ocr_text = final_text
            # record.save()
            res = response.json()
            record.ocr_text = json.dumps(res, ensure_ascii=False, indent=4)
            record.save()
        else:
            return Response({'error': 'OCR API request failed'}, status=response.status_code)

    return Response({'message': 'OCR analysis complete'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def template_ocr_analysis(request):
    api_url = os.environ.get('TEMPLATE_OCR_API_URL')
    secret_key = os.environ.get('TEMPLATE_OCR_SECRET_KEY')

    headers = {
        'X-OCR-SECRET': secret_key,
    }

    record_ids = request.data.get('record_ids', None)
    if not record_ids:
        return Response({'error': 'No record IDs provided'}, status=400)

    records_to_analyze = HealthRecordImage.objects.filter(user=request.user, id__in=record_ids)
    if not records_to_analyze:
        return Response({'error': 'provided record IDs do not exists'}, status=400)

    for record in records_to_analyze:
        image_name = record.image.name
        file_extension = os.path.splitext(image_name)[1][1:]
        with open(record.image.path, 'rb') as img_file:
            files = [('file', img_file)]
            request_json = {
                'images': [
                    {
                        'format': file_extension,
                        'name': image_name,
                        'templateIds': []
                    }
                ],
                'requestId': str(uuid.uuid4()),
                'version': 'V2',
                'timestamp': int(round(time.time() * 1000))
            }
            payload = {'message': json.dumps(request_json).encode('UTF-8')}
            response = requests.request("POST", api_url, headers=headers, data=payload, files=files)
            if response.status_code == 200:
                json_response = response.json()
                fields = json_response['images'][0]['fields']
                ocr_data = {field['name']: field['inferText'] for field in fields}
                ocr_text_json = json.dumps(ocr_data, ensure_ascii=False)
                record.ocr_text = ocr_text_json
                record.save()
            else:
                return Response({'error': 'OCR API request failed'}, status=response.status_code)

    return Response({'message': 'OCR analysis complete'})


def is_url_safe(url, allowed_domains):
    parsed_url = urlparse(url)
    return parsed_url.netloc in allowed_domains


def template_ocr_analysis_for_gpt(request):
    print("Function start")

    api_url = os.environ.get('TEMPLATE_OCR_API_URL')
    secret_key = os.environ.get('TEMPLATE_OCR_SECRET_KEY')

    print(f"API URL: {api_url}, Secret Key: {'Present' if secret_key else 'Absent'}")

    headers = {
        'X-OCR-SECRET': secret_key,
    }

    # try:
    #     image_url = request.POST.get('image_url', None)
    #     if not image_url:
    #         raise ValueError("No image URL provided")
    #
    #     allowed_domains = os.environ.get('IMAGE_CUSTOM_DOMAIN')
    #     if not is_url_safe(image_url, allowed_domains):
    #         raise ValueError("URL is not safe")
    #
    #     print(f"Image URL received: {image_url}")
    #
    # except ValueError as ve:
    #     print(f"Error: {str(ve)}")
    #     return JsonResponse({'error': str(ve)}, status=400)
    #
    # except Exception as e:
    #     print(f"Unexpected Error: {str(e)}")
    #     return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    try:
        # JSON 데이터를 파싱합니다.
        data = json.loads(request.body)
        image_url = data.get('image_url')

        if not image_url:
            raise ValueError("No image URL provided")

        allowed_domains = os.environ.get('IMAGE_CUSTOM_DOMAIN')
        if not is_url_safe(image_url, allowed_domains):
            raise ValueError("URL is not safe")

        print(f"Image URL received: {image_url}")

    except ValueError as ve:
        print(f"Error: {str(ve)}")
        return JsonResponse({'error': str(ve)}, status=400)

    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"Error: Unable to download image from URL with status code {response.status_code}")
            return JsonResponse({'error': 'Unable to download image'}, status=response.status_code)

        parsed_url = urlparse(image_url)
        file_name = os.path.basename(unquote(parsed_url.path))
        file_extension = os.path.splitext(file_name)[1][1:]

        print(f"File downloaded: {file_name}, Extension: {file_extension}")

        with open(file_name, 'wb') as img_file:
            img_file.write(response.content)

        with open(file_name, 'rb') as img_file:
            files = [('file', img_file)]
            request_json = {
                'images': [
                    {
                        'format': file_extension,
                        'name': file_name,
                        'templateIds': []
                    }
                ],
                'requestId': str(uuid.uuid4()),
                'version': 'V2',
                'timestamp': int(round(time.time() * 1000))
            }
            payload = {'message': json.dumps(request_json).encode('UTF-8')}
            print("Sending request to OCR API")
            response = requests.request("POST", api_url, headers=headers, data=payload, files=files)

            if response.status_code == 200:
                json_response = response.json()
                fields = json_response['images'][0]['fields']
                ocr_data = {field['name']: field['inferText'] for field in fields}

                return JsonResponse({'ocr_data': ocr_data})

            else:
                print(f"Error: OCR API request failed with status code {response.status_code}")
                print(f"Response Body: {response.text}")
                return JsonResponse({'error': 'OCR API request failed'}, status=response.status_code)

    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
