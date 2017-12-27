from django.conf.urls import url

from . import views

app_name = 'blog'
urlpatterns = [
    # 主页
    url(r'^$', views.IndexView.as_view(), name='index'),

    # 文章内容页
    url(r'^post/(?P<pk>[0-9]+)/$',
        views.PostDetailView.as_view(), name='detail'),

    # 文章日期归档页
    url(r'^archives/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/$',
        views.ArchivesView.as_view(), name='archives'),

    # 文章分类页
    url(r'^category/(?P<pk>[0-9]+)/$',
        views.CategoryView.as_view(), name='category'),

    # 标签分类页
    url(r'^tag/(?P<pk>[0-9]+)/$',
        views.TagView.as_view(), name='tag'),
]
