from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django import forms

from .models import *


CATEGORIES = [(category, category) for category in Category.objects.all()]

class ListingForm(forms.Form):
    title = forms.CharField(label="title", max_length=64)
    description = forms.CharField(label="description", max_length=64)
    imageUrl = forms.CharField(label="imageUrl", max_length=256)
    category = forms.ChoiceField(choices=CATEGORIES)
    startPrice = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    active = forms.BooleanField(required=False)


class BidForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)


def index(request):
    return render(request, "auctions/index.html", {
        "listings": Listing.objects.filter(active=True).all(),
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")

@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = Listing(
                title = form.cleaned_data["title"],
                description = form.cleaned_data["description"],
                imageUrl = form.cleaned_data["imageUrl"],
                startPrice = form.cleaned_data["startPrice"],
                active = form.cleaned_data["active"],
                user = request.user,
                category = Category.objects.get(name=request.POST["category"])
            )
            listing.save()
        return HttpResponseRedirect(reverse("index"))

    return render(request, "auctions/create-listing.html", {
        "form": ListingForm()
    })


def listing(request, id):
    listing = Listing.objects.get(id=id)
    error = None
    if request.method == "POST":
        if request.POST.get("form", False) == "bid":
            bidForm = BidForm(request.POST)
            if bidForm.is_valid():
                maxBid = 0
                if len(listing.bids.all()) != 0:
                    maxBid = listing.bids.order_by('-amount')[0].amount
                if bidForm.cleaned_data["amount"] >= listing.startPrice and bidForm.cleaned_data["amount"] > maxBid:
                    bid = Bid(
                        amount = bidForm.cleaned_data["amount"],
                        listing = listing,
                        user = listing.user
                    )
                    bid.save()
                else:
                    error = "Bid must be at least as much as the starting price, and larger than all existing bids!"
            else: 
                error = "Bid form was invalid! Try again"
            
        if request.POST.get("form", False) == "active":
            listing.active = False
            listing.save()

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "bidForm": BidForm(),
        "bids": listing.bids.order_by('-amount').all(),
        "error": error,
    })


def categories(request):
    return render(request, "auctions/categories.html", {
        "categories": Category.objects.all()
    })


def category(request, category):
    return render(request, "auctions/category.html", {
        "listings": Category.objects.get(name=category).listings.all()
    })


@login_required
def watchlist(request):
    if request.method == "POST":
        listing = Listing.objects.get(id=int(request.POST["listing"]))

        if request.POST.get("remove") == "True" and Watchlist.objects.filter(user=request.user, listing=listing).count():
            tmp = Watchlist.objects.get(user=request.user, listing=listing)
            tmp.delete()
            return HttpResponseRedirect(reverse("watchlist"))

        elif request.POST.get("add") == "True" and len(Watchlist.objects.filter(user=request.user, listing=listing).all()) == 0:
            item = Watchlist(user=request.user, listing=listing)
            item.save()
            return HttpResponseRedirect(reverse("watchlist"))

    return render(request, "auctions/watchlist.html", {
        "watchlist": Watchlist.objects.filter(user=request.user)
    })