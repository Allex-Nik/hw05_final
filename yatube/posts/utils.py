from django.core.paginator import Paginator


def paginate_page(request, post_list, post_per_page=10):
    paginator = Paginator(post_list, post_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
