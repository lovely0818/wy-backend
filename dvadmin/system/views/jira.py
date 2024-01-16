from dvadmin.system.models import Users, JiraProject, JiraIssue, IssueComment
from dvadmin.system.views.user import UserSerializer

from dvadmin.utils.serializers import CustomModelSerializer

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from rest_framework.decorators import action
from dingtalkchatbot.chatbot import DingtalkChatbot
from enum import Enum


class JiraProjectSerializer(CustomModelSerializer):
    class Meta:
        model = JiraProject
        fields = '__all__'


class IssueCommentSerializer(CustomModelSerializer):
    author = UserSerializer()

    class Meta:
        model = IssueComment
        fields = '__all__'


class JiraIssueSerializer(CustomModelSerializer):
    comments = IssueCommentSerializer(many=True, read_only=True)

    class Meta:
        model = JiraIssue
        fields = '__all__'


class JiraViewSet(CustomModelViewSet):
    queryset = JiraProject.objects.all()
    serializer_class = JiraProjectSerializer

    @action(methods=['GET'], detail=False)
    def get_project_list_page(self, request):
        queryset = JiraProject.objects.all()
        serializer = JiraProjectSerializer(queryset, many=True)
        data = serializer.data
        return SuccessResponse(data=data, total=len(data), msg="获取成功")

    @action(methods=['POST'], detail=False)
    def update_project(self, request):
        data = request.data
        data1 = {
            'name': data.get('name'),
            'key': data.get('key'),
            'description': data.get('description'),
            'manager_id': data.get('manager'),
            'ding_webhook': data.get('ding_webhook')
        }
        JiraProject.objects.filter(id=data.get('id')).update(**data1)
        return DetailResponse(msg='更新成功')

    @action(methods=['POST'], detail=False)
    def delete_project(self, request):
        data = request.data
        JiraProject.objects.filter(id=data.get('id')).delete()
        return DetailResponse(msg='更新成功')


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
        comment = IssueComment.objects.filter(issue_id=issue_id)
        comment_serializer = IssueCommentSerializer(comment, many=True)
        serialized_data = serializer.data
        serialized_data['comments'] = comment_serializer.data
        return DetailResponse(data=serialized_data)

    @action(methods=['GET'], detail=False)
    def get_issue_list(self, request):
        queryset = JiraIssue.objects.filter(project_id=request.query_params.get('project_id'))
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
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
        send_dingtalk_message(project.ding_webhook, '有新的issue：' + data['signal_number'] + ':' + data['name'])
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

    @action(methods=['POST'], detail=False)
    def resolve_issue(self, request):
        data = request.data
        issue_id = data.get('id')
        issue = JiraIssue.objects.filter(id=issue_id)
        if not issue:
            return ErrorResponse(msg='issue不存在')
        update_data = {'resolve_datetime': data.get('deadline'), 'modifier': request.user.id, 'status': 2}
        JiraIssue.objects.filter(id=issue_id).update(**update_data)
        if data.get('comment'):
            obj = {
                'body': data.get('comment'),
                'author_id': request.user.id,
                'issue_id': issue_id
            }
            print(111, obj)
            IssueComment.objects.create(**obj)
        return DetailResponse(data='保存成功')


def send_dingtalk_message(webhook, msg):
    try:
        bot = DingtalkChatbot(webhook)
        bot.send_text(msg=msg)
        print("Dingtalk message sent successfully!")
    except Exception as e:
        print(f"Error sending Dingtalk message: {str(e)}")
