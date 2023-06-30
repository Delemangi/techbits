import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from . import models

# Helpers


def get_current_user_info(request: HttpRequest) -> models.UserInformation | None:
    if not request.user.is_authenticated:
        return None

    try:
        return models.UserInformation.objects.get(user=request.user)  # type: ignore
    except models.UserInformation.DoesNotExist:
        return None


def get_categories() -> list[models.Category]:
    return list(models.Category.objects.all())


def get_products(limit: int | None = None) -> list[models.Product]:
    products = list(models.Product.objects.all())

    if limit is not None:
        return products[:limit]

    return products


# Views


def index(request: HttpRequest) -> HttpResponse:
    result = request.GET.get("result", None)

    context = {
        "categories": get_categories(),
        "products": get_products(4),
        "info": get_current_user_info(request),
        "result": result,
    }

    return render(request, "index.html", context)


def products(request: HttpRequest) -> HttpResponse:
    context = {
        "categories": get_categories(),
        "products": get_products(),
        "info": get_current_user_info(request),
    }

    return render(request, "products.html", context)


def category(request: HttpRequest, slug: str) -> HttpResponse:
    context = {
        "categories": get_categories(),
        "products": models.Product.objects.filter(category__slug=slug),
        "category": models.Category.objects.get(slug=slug),
        "info": get_current_user_info(request),
    }

    return render(request, "products.html", context)


def cart(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    context = {
        "categories": get_categories(),
        "info": get_current_user_info(request),
        "cart": models.Cart.objects.get_or_create(user=request.user)[
            0
        ].productincart_set.all()
        if request.user.is_authenticated
        else None,
    }

    return render(request, "cart.html", context)


def profile(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    url = f"/admin/app/userinformation/{request.user.id}/change/"

    return redirect(url)


def add_to_cart(request: HttpRequest, slug: str) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method != "POST":
        return JsonResponse({"success": False})

    cart, _ = models.Cart.objects.get_or_create(user=request.user)
    product = models.Product.objects.get(slug=slug)
    product_in_cart, created = models.ProductInCart.objects.get_or_create(
        cart=cart, product=product
    )
    product_in_cart.quantity += 1

    if created:
        product_in_cart.quantity = 1

    product_in_cart.save()

    return JsonResponse({"success": True})


def remove_from_cart(request: HttpRequest, slug: str) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method != "POST":
        return JsonResponse({"success": False})

    cart = models.Cart.objects.get_or_create(user=request.user)[0]
    product = models.Product.objects.get(slug=slug)

    product_in_cart = models.ProductInCart.objects.get(cart=cart, product=product)

    if product_in_cart is not None:
        product_in_cart.delete()

    return JsonResponse({"success": True})


def checkout(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    context = {
        "categories": get_categories(),
        "info": get_current_user_info(request),
        "cart": models.Cart.objects.get_or_create(user=request.user)[
            0
        ].productincart_set.all()
        if request.user.is_authenticated
        else None,
    }

    return render(request, "checkout.html", context)


def empty_cart(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method != "POST":
        return JsonResponse({"success": False})

    try:
        cart = models.Cart.objects.get(user=request.user)

        order = models.Order.objects.create(user=request.user, state="pending")
        for product_in_cart in cart.productincart_set.all():
            product_in_order = models.ProductInOrder.objects.create(
                order=order,
                product=product_in_cart.product,
                quantity=product_in_cart.quantity,
            )
            product_in_order.save()
            product_in_cart.delete()

        cart.delete()
        models.Cart.objects.create(user=request.user).save()
    except models.Cart.DoesNotExist:
        pass

    return JsonResponse({"success": True})


def product(request: HttpRequest, slug: str) -> HttpResponse:
    context = {
        "categories": get_categories(),
        "info": get_current_user_info(request),
        "product": models.Product.objects.get(slug=slug),
        "reviews": models.Review.objects.filter(product__slug=slug),
    }

    return render(request, "product_view.html", context)


def post_review(request: HttpRequest, slug: str) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method != "POST":
        return JsonResponse({"success": False})

    product = models.Product.objects.get(slug=slug)
    user = request.user
    try:
        data = json.loads(request.body)
        text = data.get("review", None)
        rating = data.get("rating", None)
    except json.JSONDecodeError:
        return JsonResponse({"success": False})

    try:
        review = models.Review.objects.get(product=product, user=user)
        review.text = text if text is not None else "No comment given."
        review.rating = int(rating) if rating is not None else 1
        review.save()
    except models.Review.DoesNotExist:
        models.Review.objects.create(
            product=product,
            user=user,
            text=text if text is not None else "No comment given.",
            rating=int(rating) if rating is not None else 1,
        ).save()

    return JsonResponse({"success": True})
