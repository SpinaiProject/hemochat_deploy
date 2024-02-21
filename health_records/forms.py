# from django import forms
# from rest_framework.exceptions import ValidationError
#
# from .models import *
#
#
# class HealthRecordForm(forms.ModelForm):
#     class Meta:
#         model = HealthRecord
#         fields = ['image', 'ocr_text']
#
#     def clean_image(self):
#         image = self.cleaned_data.get('image')
#         if image:
#             if not image.name.endswith(('.png', '.jpg', '.jpeg')):  # 파일 형식 검증
#                 raise ValidationError("Only .png, .jpg and .jpeg formats are supported.")
#             if image.size > 10 * 1024 * 1024:  # 파일 사이즈 10메가로 제한
#                 raise ValidationError("The image size cannot exceed 10MB.")
#         return image
