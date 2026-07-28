from django.core.exceptions import ImproperlyConfigured
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.permissions import AllowAny

from utils import Message, QueryParams, Constants
from utils.Permissions import IsAdminPermission


class SmartAPIView(APIView):

    def post(self, request):
        data = request.data
        return self.post_response(data)

    def not_found(self):
        return self.respond_with("Object not found", "detail", status.HTTP_404_NOT_FOUND)

    def post_response(self, data, instance=None):
        return Response(data, status=status.HTTP_201_CREATED)

    def respond_with(self, text, key=None, status_code=status.HTTP_200_OK):
        return Response(Message.create(text=text, key=key), status=status_code)

    def get(self, request, **kwargs):
        if not self.has_permission(request):
            return self.respond_with(Message.create("You do not have permission to access this."), status_code=status.HTTP_403_FORBIDDEN)
        return Response(status.HTTP_200_OK)

    def has_permission(self, request):
        return True


class PageBasedPagination(PageNumberPagination):
    page_size = 20
    page_query_param = "page"
    max_page_size = 50


class CustomCursorPagination(CursorPagination):
    max_page_size = 100
    page_size = 20
    ordering = '-created_at'


class PaginationAPIView(SmartAPIView):
    max_page_size = 50
    min_page_size = 10
    default_page_size = 15

    pagination_class = CustomCursorPagination
    disable_pagination = False

    @property
    def paginator(self):

        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                pagination_type = QueryParams.get_str(self.request, "pagination_type")
                if pagination_type == Constants.PAGINATION_TYPE_PAGE:
                    self._paginator = PageBasedPagination()
                else:
                    self._paginator = self.pagination_class()

        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None

        self.set_page_size()

        order_by = QueryParams.get_str(self.request, "order_by")
        if order_by:
            queryset = queryset.order_by(order_by)

        page = self.paginator.paginate_queryset(queryset, self.request, view=self)
        return page

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def set_page_size(self, extra=None):

        page_size = self.request.GET.get('page_size')

        if not page_size:
            return

        size = int(page_size)

        if size < self.min_page_size:
            size = self.min_page_size

        if size > self.max_page_size:
            size = self.max_page_size

        self.paginator.page_size = size

    def paginated_response(self, queryset, serializer_class, return_data=False, paginate=True):

        if hasattr(serializer_class, "select_related_fields") or hasattr(serializer_class,
                                                                         "prefetch_related_fields"):
            queryset = serializer_class().optimize(queryset)
        else:
            print(f"{serializer_class} query not optimised")
            pass

        if self.disable_pagination and QueryParams.get_bool(self.request, 'paginated') is False:

            order_by = QueryParams.get_str(self.request, "order_by")
            if order_by:
                queryset = queryset.order_by(order_by)
            elif isinstance(self.paginator.ordering, list):
                queryset = queryset.order_by(*self.paginator.ordering)
            else:
                queryset = queryset.order_by(self.paginator.ordering)

            data = serializer_class(queryset, many=True).data

            return Response(data)

        if paginate:
            page = self.paginate_queryset(queryset)
        else:
            page = queryset

        serializer = serializer_class(page, many=True)

        if return_data:
            return serializer.data

        return self.get_paginated_response(serializer.data)


class SmartPaginationAPIView(PaginationAPIView):

    model = None
    create_serializer = None
    list_serializer = None
    detail_serializer = None

    def get_create_serializer(self):
        """
        :return: Create serializer
        """
        if not self.create_serializer:
            return Response({"message": "Create serializer missing"}, status=status.HTTP_400_BAD_REQUEST)
        return self.create_serializer

    def get_detail_serializer(self):
        """
        :return: Detail serializer
        """
        if not self.detail_serializer:
            return Response({"message": "Detail serializer missing"}, status=status.HTTP_400_BAD_REQUEST)
        return self.detail_serializer

    def get_response(self, query, serializer_class):
        return self.paginated_response(query, serializer_class)

    def post(self, request, *args, **kwargs):
        """
        Creates an item and saves it in the application database.
        :param request:
        :return: Data object
        """
        if not self.has_permission(request):
            return self.respond_with(
                "You do not have permission to perform this action.",
                key="detail", status_code=status.HTTP_403_FORBIDDEN)

        data = request.data

        data = self.override_post_data(data)

        serializer = self.create_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        detail_serializer = self.get_detail_serializer()
        data = detail_serializer(instance).data
        return self.post_response(data, instance=instance)

    def override_post_data(self, data):
        return data

    def filter_queryset(self, **kwargs):
        queryset = self.model.objects.filter(**kwargs)
        return queryset

    def add_filters(self, queryset):
        return queryset

    def get(self, *args, **kwargs):
        queryset = self.filter_queryset()
        queryset = self.add_filters(queryset)
        serializer_class = self.list_serializer
        return self.get_response(queryset, serializer_class)

    def has_permission(self, request):
        return True


class SmartDetailView(SmartAPIView):
    model = None
    deletable = False
    edit_serializer = None
    detail_serializer = None
    permission_classes = None

    def post(self, *args, **kwargs):
        return self.respond_with(Message.create('Post method not allowed'), status_code=status.HTTP_403_FORBIDDEN)

    def get(self, request, *args, **kwargs):
        if not self.has_permission("GET"):
            return self.get_permission_denied_response(request, "GET")

        queryset = self.queryset(**kwargs)
        queryset = self.add_filters(queryset)

        instance = queryset.first()

        if not instance:
            return self.get_instance_not_found_response()
        data = self.detail_serializer(instance).data
        return Response(data, status.HTTP_200_OK)

    def patch(self, request, **kwargs):
        request_data = request.data

        if not self.has_permission("PATCH"):
            return self.get_permission_denied_response(request, "PATCH")

        queryset = self.queryset(**kwargs)
        queryset = self.add_filters(queryset)
        instance = queryset.first()

        if not instance:
            return self.get_instance_not_found_response()

        if not self.has_object_permission(request, instance, "PATCH"):
            return self.get_permission_denied_response(request, "PATCH")
        self.check_object_permissions(request, instance)

        serializer = self.edit_serializer(instance, data=request_data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        data = self.detail_serializer(instance).data
        return self.patch_response(instance, data)

    def delete(self, request, *args, **kwargs):
        if not self.has_permission("DELETE"):
            return self.get_permission_denied_response(request, "DELETE")

        queryset = self.queryset(**kwargs)
        queryset = self.add_filters(queryset)
        model_instance = queryset.first()

        if not model_instance:
            return self.get_instance_not_found_response()

        if not self.has_object_permission(request, model_instance, "DELETE"):
            return self.get_permission_denied_response(request, "DELETE")
        self.check_object_permissions(request, model_instance)

        handle_delete = self.handle_delete(model_instance)

        if isinstance(handle_delete, Response):
            return handle_delete

        return self.delete_response()

    def delete_response(self):
        return Response(status.HTTP_204_NO_CONTENT)

    def handle_delete(self, model_instance):
        model_instance.delete()

    def queryset(self, **kwargs):
        # Without a lookup this would filter on nothing and match every row in
        # the table, so a subclass that forgets to scope itself must fail loudly
        # rather than quietly hand back (or delete) another user's records.
        if not kwargs:
            raise ImproperlyConfigured(
                f"{type(self).__name__} called the default queryset() with no lookup kwargs. "
                f"Override queryset() to scope the lookup to the requesting user."
            )
        return self.model.objects.filter(**kwargs)

    def add_filters(self, queryset):
        return queryset

    def has_permission(self, method):
        if not self.deletable and method == "DELETE":
            return False
        return True

    def get_permission_denied_response(self, request, action):
        message = (
            "Delete not permitted on this route."
            if action == "DELETE"
            else "You do not have permission to access this endpoint."
        )
        return self.respond_with(message, key="detail", status_code=status.HTTP_403_FORBIDDEN)

    def get_instance_not_found_response(self):
        return self.respond_with(
            Message.create("An object with id does not exist"), status_code=status.HTTP_404_NOT_FOUND)

    def has_object_permission(self, request, instance, method):
        return True

    def patch_response(self, instance, data):
        return Response(data, status=status.HTTP_200_OK)


class AdminWriteMixin:
    """Allows any user to read; requires admin for write operations."""

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAdminPermission()]
        return [AllowAny()]

    def has_permission(self, request):
        return True
