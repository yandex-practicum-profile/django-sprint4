from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post

POSTS_PER_PAGE = 10
User = get_user_model()


def post_list():
    return Post.objects.select_related(
        'author', 'category', 'location',
    ).order_by('-pub_date', '-pk')


def published_posts(posts):
    return posts.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now(),
    )


def with_comment_count(posts):
    return posts.annotate(comment_count=Count('comments'))


def paginate(request, posts):
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


def visible_post(request, post_id):
    post = get_object_or_404(post_list(), pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(published_posts(post_list()), pk=post_id)
    return post


def index(request):
    posts = published_posts(post_list())
    return render(request, 'blog/index.html', {
        'page_obj': paginate(request, with_comment_count(posts)),
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True,
    )
    posts = published_posts(post_list().filter(category=category))
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': paginate(request, with_comment_count(posts)),
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = post_list().filter(author=author)
    if request.user != author:
        posts = published_posts(posts)
    return render(request, 'blog/profile.html', {
        'profile': author,
        'page_obj': paginate(request, with_comment_count(posts)),
    })


@login_required
def edit_profile(request):
    form = ProfileForm(
        request.POST if request.method == 'POST' else None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        return redirect('blog:profile', username=user.username)
    return render(request, 'blog/user.html', {'form': form})


class RegistrationView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


def post_detail(request, post_id):
    post = visible_post(request, post_id)
    return render(request, 'blog/detail.html', {
        'post': post, 'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    })


@login_required
def create_post(request):
    form = PostForm(
        request.POST if request.method == 'POST' else None,
        request.FILES or None,
    )
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(
        request.POST if request.method == 'POST' else None,
        request.FILES or None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {
        'form': PostForm(instance=post),
    })


@login_required
@require_POST
def add_comment(request, post_id):
    post = visible_post(request, post_id)
    # Передаём форме данные, отправленные при добавлении комментария.
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/detail.html', {
        'post': post, 'form': form,
        'comments': post.comments.select_related('author'),
    })


@login_required
def edit_comment(request, post_id, comment_id):
    post = visible_post(request, post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = CommentForm(
        request.POST if request.method == 'POST' else None,
        instance=comment,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {
        'form': form, 'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    post = visible_post(request, post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {'comment': comment})
