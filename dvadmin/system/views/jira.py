from dvadmin.system.models import Users, JiraProject, JiraIssue
from dvadmin.system.views.user import UserSerializer

from dvadmin.utils.serializers import CustomModelSerializer

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from rest_framework.decorators import action
from enum import Enum


class JiraProjectSerializer(CustomModelSerializer):
    class Meta:
        model = JiraProject
        fields = '__all__'


class JiraIssueSerializer(CustomModelSerializer):
    class Meta:
        model = JiraIssue
        fields = '__all__'


class JiraViewSet(CustomModelViewSet):
    queryset = JiraProject.objects.all()
    serializer_class = JiraProjectSerializer

    @action(methods=['GET'], detail=False)
    def get_project_list(self, request):
        queryset = JiraProject.objects.all()
        serializer = JiraProjectSerializer(queryset, many=True)
        data = serializer.data
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def get_all_issue(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return ErrorResponse(msg='项目不存在')
        status = request.query_params.get('status')
        queryset = JiraProject.objects.filter(project_id=project_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        issues = queryset.all()
        queryset = JiraProject.objects.all()
        serializer = JiraProjectSerializer(queryset, many=True)
        data = serializer.data
        return DetailResponse(data=data)

    @action(methods=['POST'], detail=False)
    def get_issue_detail(self, request):
        data = request.data
        issue_id = data.get('id')
        issue = JiraIssue.objects.get(id=issue_id)
        serializer = JiraIssueSerializer(issue)
        data = serializer.data
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def get_issue_list(self, request):
        queryset = JiraIssue.objects.all()
        serializer = JiraIssueSerializer(queryset, many=True)
        serialized_data = serializer.data
        return DetailResponse(data=serialized_data)

    @action(methods=['GET'], detail=False)
    def get_jira_user(self, request):
        queryset = Users.objects.all()
        serializer = UserSerializer(queryset, many=True)
        serialized_data = serializer.data
        processed_data = [{'id': user['id'], 'name': user['name']} for user in serialized_data]
        return DetailResponse(data=processed_data)

    @action(methods=['POST'], detail=False)
    def add_issue(self, request):
        data = request.data
        project_id = data.get('project_id')
        project = JiraProject.objects.get(id=project_id)
        count = JiraIssue.objects.filter(project_id=project_id).count()
        count = count + 1
        data['signal_number'] = str(project.key) + '-' + str(count)
        data['creator_id'] = request.user.id
        data['modifier'] = request.user.id
        data['status'] = 1
        JiraIssue.objects.create(**data)
        return DetailResponse(data='创建成功')

    @action(methods=['POST'], detail=False)
    def update_issue(self, request):
        data = request.data
        issue = JiraIssue.objects.filter(id=data.get('id'))
        if not issue:
            return ErrorResponse(msg='issue不存在')
        data.pop('id', None)
        data['modifier'] = request.user.id
        issue.update(**data)
        return DetailResponse(data='保存成功')
