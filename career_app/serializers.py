from rest_framework import serializers
from .models import Opportunity, ProfileMatch, StudentProfile

class OpportunitySerializer(serializers.ModelSerializer):
    required_skills = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='skill_name'
    )

    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'provider', 'opportunity_type', 'is_free',
            'stipend_or_cost', 'mode', 'location', 'deadline', 'url',
            'description', 'eligibility', 'required_skills'
        ]

class ProfileMatchSerializer(serializers.ModelSerializer):
    opportunity = OpportunitySerializer(read_only=True)

    class Meta:
        model = ProfileMatch
        fields = ['id', 'relevance_score', 'matching_skills', 'reasoning', 'is_bookmarked', 'opportunity']

class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = '__all__'