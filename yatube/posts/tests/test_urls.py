from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.cache import cache

from ..models import Post, Group, Follow

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.user = User.objects.create_user(username='lev')
        cls.user_following = User.objects.create_user(username='test')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.post_url = f'/posts/{cls.post.id}/'
        cls.post_create_url = '/create/'
        cls.post_edit_url = f'/posts/{cls.post.id}/edit/'
        cls.public_urls = {
            '/': 'index.html',
            f'/group/{cls.group.slug}/': 'group_list.html',
            f'/profile/{cls.user.username}/': 'profile.html',
            cls.post_url: 'post_detail.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.following_client = Client()
        self.following_client.force_login(self.user_following)

    def test_pages_url_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        for url in self.public_urls.keys():
            with self.subTest():
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_url_exists_at_desired_location(self):
        """Страница доступна автору."""
        response = self.authorized_client.get(self.post_edit_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_exists_at_desired_location(self):
        """Страница доступна авторизованному пользователю."""
        response = self.authorized_client.get(self.post_create_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_guest_on_admin_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get(self.post_create_url, follow=True)
        self.assertRedirects(
            response, f'/auth/login/?next={self.post_create_url}'
        )

    def test_edit_url_redirect_guest_on_admin_login(self):
        """Страница по адресу /edit/ перенаправит анонимного
        пользователя на информацию о посте.
        """
        response = self.guest_client.get(self.post_edit_url, follow=True)
        self.assertRedirects(
            response, f'/auth/login/?next={self.post_edit_url}'
        )

    def test_url_404_guest_authorized(self):
        response_clients = {
            self.guest_client: '/wrongurl/',
            self.authorized_client: '/wrongurl/',
        }
        for client, url in response_clients.items():
            with self.subTest():
                response = client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        url_templates_names = {'/': 'posts/index.html',
                               f'/group/{self.group.slug}/':
                                   'posts/group_list.html',
                               f'/profile/{self.user.username}/':
                                   'posts/profile.html',
                               self.post_url: 'posts/post_detail.html',
                               self.post_create_url: 'posts/create_post.html',
                               self.post_edit_url: 'posts/create_post.html'}
        for url, template in url_templates_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_follow(self):
        follows_count = Follow.objects.count()
        response = self.following_client.get(
            f'/profile/{self.user.username}/follow/')
        self.assertEqual(Follow.objects.count(), follows_count + 1)
        self.assertTrue(Follow.objects.filter(
            user=self.user_following,
            author=self.user).exists())
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unfollow(self):
        self.following_client.get(
            f'/profile/{self.user.username}/follow/')
        follows_count = Follow.objects.count()
        response = self.following_client.get(
            f'/profile/{self.user.username}/unfollow/')
        self.assertEqual(Follow.objects.count(), follows_count - 1)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
