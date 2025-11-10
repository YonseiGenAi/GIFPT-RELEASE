from rest_framework import serializers

class AnalyzeRequestSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    file_path = serializers.CharField()
    prompt = serializers.CharField()

class ChatMessage(serializers.Serializer):
    role = serializers.ChoiceField(choices=['system', 'user', 'assistant'])
    content = serializers.CharField()

class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=False, allow_blank=True)
    file_path = serializers.CharField(required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    messages = ChatMessage(many=True)
