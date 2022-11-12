import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms
from django.core.cache import cache

from ..models import Post, Group

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='forest.jpg',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='lev')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.objects = [Post(author=cls.user,
                            text='Тестовый пост',
                            group=cls.group,
                            image=cls.image,
                            id=f'{i}') for i in range(12)]
        cls.posts = Post.objects.bulk_create(cls.objects)
        cls.group1 = Group.objects.create(title='Другая группа',
                                          slug='test1-slug',
                                          description='Другое описание')
        cls.templates_pages = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:group_list',
                                             kwargs={'slug': cls.group.slug}),
            'posts/profile.html': reverse(
                'posts:profile', kwargs={'username': cls.user.username}),
            'posts/post_detail.html': reverse('posts:post_detail',
                                              kwargs={'post_id': '1'}),
            'posts/create_post.html': reverse('posts:post_edit',
                                              kwargs={'post_id': '1'}),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        for template, reverse_name in self.templates_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_shows_correct_context(self):
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_author = first_object.author
        post_text = first_object.text
        post_group = first_object.group
        post_image = first_object.image
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_text, self.posts[11].text)
        self.assertEqual(post_group, self.group)
        self.assertEqual(post_image, self.posts[11].image)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                author=self.user,
                image='posts/forest.jpg'
            ).exists())
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_page_shows_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn('page_obj', response.context)
        first_object = response.context['page_obj'][0]
        post_author = first_object.author
        post_text = first_object.text
        post_group = first_object.group
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_text, self.posts[11].text)
        self.assertEqual(post_group, self.group)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                author=self.user,
                image='posts/forest.jpg'
            ).exists())
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_page_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertIn('page_obj', response.context)
        first_object = response.context['page_obj'][0]
        post_author = first_object.author
        post_text = first_object.text
        post_group = first_object.group
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_text, self.posts[11].text)
        self.assertEqual(post_group, self.group)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                author=self.user,
                image='posts/forest.jpg'
            ).exists())
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_post_detail_page_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'}))
        self.assertEqual(
            response.context['post'].author, self.user)
        self.assertEqual(
            response.context['post'].text, self.posts[11].text)
        self.assertEqual(
            response.context['post'].group, self.group)
        self.assertEqual(
            response.context['post'].id, int(self.posts[1].id))
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                author=self.user,
                image='posts/forest.jpg'
            ).exists())

    def test_post_edit_page_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_create_page_shows_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_appears_on_selected_page(self):
        """Пост, созданный в Тестовой группе,
        окажется в index, group_list, profile"""
        cache.clear()
        reverse_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        }
        for page in reverse_names:
            with self.subTest():
                response = self.authorized_client.get(page)
                self.assertIn('page_obj', response.context)
                post = response.context['page_obj'][0]
                post_id = post.id
                post_group = post.group.title
                self.assertEqual(post_id, 11)
                self.assertEqual(post_group, self.group.title)

    def test_post_doesnt_appear_on_selected_page(self):
        """Пост, созданный в Тестовой группе,
        не окажется в другой группе"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group1.slug}))
        self.assertIn('page_obj', response.context)
        all_posts = response.context.get('page_obj').paginator.count
        self.assertEqual(all_posts, 0)

    def test_index_cache(self):
        cache.clear()
        post_test = Post.objects.create(
            author=self.user,
            text='Тестовый пост1',
            group=self.group
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        response1 = response.content
        post_test.delete()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        response2 = response.content
        self.assertEqual(response1, response2)
        cache.clear()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        response3 = response.content
        self.assertNotEqual(response1, response3)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cache.clear()
        super().setUpClass()
        cls.user = User.objects.create_user(username='lev')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.objects = [Post(author=cls.user,
                            text='Тестовый пост',
                            group=cls.group,
                            id=f'{i}') for i in range(12)]
        cls.posts = Post.objects.bulk_create(cls.objects)
        cls.paginator_list = {
            'posts:index': reverse('posts:index'),
            'posts:group_list': reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}),
            'posts:profile': reverse(
                'posts:profile', kwargs={'username': cls.user.username}),
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_posts(self):
        for template, reverse_name in self.paginator_list.items():
            response = self.authorized_client.get(reverse_name)
            self.assertIn('page_obj', response.context)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        for template, reverse_name in self.paginator_list.items():
            response = self.authorized_client.get(reverse_name + '?page=2')
            self.assertIn('page_obj', response.context)
            self.assertEqual(len(response.context['page_obj']), 2)
